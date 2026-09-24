"""Provider-neutral OIDC authorization-code login and opaque server-side sessions.

No password database, browser tokens, trusted identity headers, or client-selected owners.
The backend remains loopback-only; hosted mode requires an HTTPS proxy.
"""
from dataclasses import dataclass, field
import hashlib
from datetime import datetime, timezone
from http.cookies import SimpleCookie
import json
import os
import secrets
import time
from urllib.parse import urlsplit

import requests
from authlib.integrations.requests_client import OAuth2Session
from authlib.oidc.core import CodeIDToken
from joserfc import jwk, jwt


class AuthenticationRequired(PermissionError):
    pass


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def https_url(value):
    url = urlsplit(value)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.fragment:
        raise ValueError('OIDC endpoints must use HTTPS without credentials or fragments.')
    return value


@dataclass(frozen=True)
class OIDCConfig:
    issuer: str
    client_id: str
    client_secret: str = field(repr=False)
    redirect_uri: str

    def __post_init__(self):
        https_url(self.issuer)
        if urlsplit(self.issuer).query or not self.client_id or not self.client_secret:
            raise ValueError('Supply a valid issuer and OIDC client credentials.')
        url = urlsplit(self.redirect_uri)
        if (url.scheme not in ('http', 'https') or not url.hostname
                or (url.scheme == 'http' and url.hostname not in ('127.0.0.1', 'localhost'))
                or url.path != '/auth/callback' or url.query or url.fragment or url.username or url.password):
            raise ValueError('OIDC callback must use HTTPS, or HTTP strictly on localhost, with path /auth/callback.')

    @classmethod
    def from_environment(cls):
        mode = os.getenv('MICROGRID_AUTH_MODE', 'local')
        names = ('MICROGRID_OIDC_ISSUER', 'MICROGRID_OIDC_CLIENT_ID',
                 'MICROGRID_OIDC_CLIENT_SECRET', 'MICROGRID_OIDC_REDIRECT_URI')
        values = [os.getenv(name, '') for name in names]
        if mode == 'local':
            if any(values):
                raise ValueError('OIDC configuration is present; set MICROGRID_AUTH_MODE=oidc. Refusing an unauthenticated fallback.')
            return None
        if mode != 'oidc' or not all(values):
            raise ValueError('Set MICROGRID_AUTH_MODE to local or supply all four MICROGRID_OIDC_* settings in oidc mode.')
        return cls(*values)


class OIDCProvider:
    """Authlib handles OAuth/PKCE and OIDC claim checks; joserfc verifies signatures."""
    def __init__(self, config):
        self.config = config

    def metadata(self):
        response = requests.get(self.config.issuer.rstrip('/') + '/.well-known/openid-configuration',
                                timeout=15, allow_redirects=False)
        response.raise_for_status()
        result = response.json()
        if result['issuer'] != self.config.issuer:
            raise ValueError('OIDC issuer mismatch.')
        for key in ('authorization_endpoint', 'token_endpoint', 'jwks_uri'):
            https_url(result[key])
        if 'S256' not in result.get('code_challenge_methods_supported', []):
            raise ValueError('The identity provider must support PKCE S256.')
        return result

    def client(self):
        return OAuth2Session(self.config.client_id, self.config.client_secret,
                             scope='openid', redirect_uri=self.config.redirect_uri,
                             code_challenge_method='S256')

    def authorize(self, state, nonce, verifier):
        with self.client() as client:
            return client.create_authorization_url(self.metadata()['authorization_endpoint'],
                state=state, nonce=nonce, code_verifier=verifier)[0]

    def exchange(self, code, nonce, verifier):
        metadata = self.metadata()
        with self.client() as client:
            token = client.fetch_token(metadata['token_endpoint'], code=code,
                code_verifier=verifier, timeout=15, allow_redirects=False)
        response = requests.get(metadata['jwks_uri'], timeout=15, allow_redirects=False)
        response.raise_for_status()
        decoded = jwt.decode(token['id_token'], jwk.KeySet.import_key_set(response.json()),
                             algorithms=['RS256', 'ES256'])
        claims = CodeIDToken(decoded.claims, decoded.header,
            options={'iss': {'essential': True, 'value': self.config.issuer},
                     'aud': {'essential': True, 'value': self.config.client_id}},
            params={'nonce': nonce, 'client_id': self.config.client_id,
                    'access_token': token.get('access_token')})
        claims.validate(leeway=30)
        if not isinstance(claims.get('sub'), str) or not claims['sub']:
            raise ValueError('OIDC subject missing.')
        # Issuer + subject is the identity. Email changes cannot transfer ownership.
        return digest(json.dumps([self.config.issuer, claims['sub']]))


class Sessions:
    COOKIE = 'microgrid_session'
    LOGIN_COOKIE = 'microgrid_login'
    GUEST_COOKIE = 'microgrid_guest'
    IDLE_SECONDS = 1800
    ABSOLUTE_SECONDS = 28800
    GUEST_SECONDS = 48 * 3600

    def __init__(self, store, config, provider=None):
        self.store, self.config = store, config
        self.secure = urlsplit(config.redirect_uri).scheme == 'https'
        if self.secure:
            self.COOKIE = '__Host-microgrid_session'
            self.LOGIN_COOKIE = '__Host-microgrid_login'
            self.GUEST_COOKIE = '__Host-microgrid_guest'
        self.provider = provider or OIDCProvider(config)
        with store.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS auth_required (singleton INTEGER PRIMARY KEY CHECK(singleton=1))")
            db.execute("INSERT OR IGNORE INTO auth_required VALUES (1)")
            db.execute('''CREATE TABLE IF NOT EXISTS auth_sessions (
                token_hash TEXT PRIMARY KEY, owner_id TEXT NOT NULL, csrf TEXT NOT NULL,
                created REAL NOT NULL, last_seen REAL NOT NULL)''')
            db.execute('''CREATE TABLE IF NOT EXISTS auth_logins (
                state_hash TEXT PRIMARY KEY, browser_hash TEXT NOT NULL,
                nonce TEXT NOT NULL, verifier TEXT NOT NULL, expires REAL NOT NULL)''')
            db.execute('''CREATE TABLE IF NOT EXISTS auth_guests (
                token_hash TEXT PRIMARY KEY, owner_id TEXT NOT NULL UNIQUE,
                csrf TEXT NOT NULL, created REAL NOT NULL)''')

    @staticmethod
    def cookie_value(headers, name):
        try:
            cookies = SimpleCookie()
            cookies.load(headers.get('Cookie', ''))
            return cookies[name].value if name in cookies else ''
        except Exception:
            return ''

    def cookie(self, name, value, max_age):
        secure = '; Secure' if self.secure else ''
        return f'{name}={value}; Path=/; HttpOnly; SameSite=Lax; Max-Age={max_age}{secure}'

    def guest(self, headers, *, create=False):
        """Return a private temporary owner; never infer ownership from an ID."""
        token = self.cookie_value(headers, self.GUEST_COOKIE)
        instant = time.time()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM auth_guests WHERE token_hash=?', (digest(token),)).fetchone() if token else None
            if row is not None and row['created'] + self.GUEST_SECONDS > instant:
                return dict(row), None
            if not create:
                return None, None
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            issued = db.execute('SELECT COUNT(*) FROM auth_guests WHERE created>=?', (today,)).fetchone()[0]
            if issued >= self.store.guest_session_limit:
                from .runtime import CapacityError
                raise CapacityError('The temporary study service is full today. Try again tomorrow.', None)
            token = secrets.token_urlsafe(32)
            owner_id = 'guest:' + digest(token)
            csrf = secrets.token_urlsafe(32)
            db.execute('INSERT INTO auth_guests VALUES (?, ?, ?, ?)',
                       (digest(token), owner_id, csrf, instant))
        return {'owner_id': owner_id, 'csrf': csrf}, self.cookie(self.GUEST_COOKIE, token, self.GUEST_SECONDS)

    def start(self):
        state, browser, nonce, verifier = [secrets.token_urlsafe(32) for _ in range(4)]
        url = self.provider.authorize(state, nonce, verifier)
        with self.store.connect() as db:
            db.execute('DELETE FROM auth_logins WHERE expires < ?', (time.time(),))
            db.execute('INSERT INTO auth_logins VALUES (?, ?, ?, ?, ?)',
                       (digest(state), digest(browser), nonce, verifier, time.time() + 600))
        return url, self.cookie(self.LOGIN_COOKIE, browser, 600)

    def callback(self, params, headers):
        if set(params) - {'state', 'code', 'iss', 'session_state'} or any(len(v) != 1 for v in params.values()):
            raise AuthenticationRequired('Sign-in failed. Please try again.')
        state, code = params.get('state', [''])[0], params.get('code', [''])[0]
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM auth_logins WHERE state_hash=?', (digest(state),)).fetchone()
            if (row is None or row['expires'] < time.time() or not code
                    or not secrets.compare_digest(row['browser_hash'], digest(self.cookie_value(headers, self.LOGIN_COOKIE)))):
                raise AuthenticationRequired('Sign-in expired or invalid. Please try again.')
            db.execute('DELETE FROM auth_logins WHERE state_hash=?', (digest(state),))
        if params.get('iss', [self.config.issuer])[0] != self.config.issuer:
            raise AuthenticationRequired('Sign-in failed. Please try again.')
        try:
            owner = self.provider.exchange(code, row['nonce'], row['verifier'])
        except Exception:
            # Never expose token endpoint responses, auth codes or client credentials.
            raise AuthenticationRequired('Sign-in failed. Please try again.') from None
        self.revoke(headers)
        session = secrets.token_urlsafe(32)
        with self.store.connect() as db:
            db.execute('INSERT INTO auth_sessions VALUES (?, ?, ?, ?, ?)',
                       (digest(session), owner, secrets.token_urlsafe(32), time.time(), time.time()))
        return [self.cookie(self.COOKIE, session, self.ABSOLUTE_SECONDS), self.cookie(self.LOGIN_COOKIE, '', 0)]

    def authenticate(self, headers):
        value = self.cookie_value(headers, self.COOKIE)
        if not value:
            raise AuthenticationRequired('Sign in to access your studies.')
        timestamp = time.time()
        with self.store.connect() as db:
            db.execute('DELETE FROM auth_sessions WHERE created < ? OR last_seen < ?',
                       (timestamp-self.ABSOLUTE_SECONDS, timestamp-self.IDLE_SECONDS))
            row = db.execute('SELECT * FROM auth_sessions WHERE token_hash=?', (digest(value),)).fetchone()
            if row is None:
                raise AuthenticationRequired('Your session expired. Please sign in again.')
            db.execute('UPDATE auth_sessions SET last_seen=? WHERE token_hash=?', (timestamp, digest(value)))
        return dict(row)

    def revoke(self, headers):
        with self.store.connect() as db:
            db.execute('DELETE FROM auth_sessions WHERE token_hash=?',
                       (digest(self.cookie_value(headers, self.COOKIE)),))
