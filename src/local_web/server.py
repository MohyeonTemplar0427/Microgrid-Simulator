"""Waitress-hosted browser/API with explicit local or HTTPS-proxy mode."""

import argparse
from copy import deepcopy
from email.message import Message
from http import HTTPStatus
import signal
import threading
from waitress import create_server
from waitress import wasyncore
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
from urllib.parse import parse_qs, urlsplit
import zipfile

from .contract import DEFAULT_REQUEST, SCENARIOS
from .runtime import Application, CapacityError, ROOT, StudyConflict
from .auth import AuthenticationRequired, OIDCConfig, Sessions
from .privacy import redact

MAX_BODY = 20 * 1024 * 1024
STATIC = Path(__file__).with_name("static")


class TemporaryFileResponse:
    """Stream a generated download and remove it even if the client disconnects."""

    def __init__(self, path, release=None):
        self.path = Path(path)
        self.source = self.path.open("rb")
        self.release = release
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        block = self.source.read(1024 * 1024)
        if block:
            return block
        self.close()
        raise StopIteration

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self.source.close()
            self.path.unlink(missing_ok=True)
        finally:
            if self.release:
                self.release()


def make_wsgi_app(application, port=8765, *, auth=None, public_origin=None, allow_guests=False):
    if allow_guests and auth is None:
        raise ValueError("Guest studies require OIDC for saving to a profile.")
    if auth is None:
        with application.store.connect() as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='auth_required'").fetchone():
                raise ValueError("This storage directory requires OIDC. Use a separate directory for local mode.")
    if public_origin is not None:
        from .hosting import validate_public_origin
        validate_public_origin(public_origin)
        if auth is None or auth.config.redirect_uri != public_origin + "/auth/callback":
            raise ValueError("Hosted mode requires OIDC with a callback matching the configured HTTPS origin.")
    elif auth is not None and urlsplit(auth.config.redirect_uri).scheme != "http":
        raise ValueError("HTTPS sign-in requires explicit hosted mode and public origin.")
    token = secrets.token_urlsafe(32)

    class Handler:
        def __init__(self, environ):
            self.path = environ.get("PATH_INFO", "/") + ("?" + environ["QUERY_STRING"] if environ.get("QUERY_STRING") else "")
            self.headers = Message()
            for key, value in environ.items():
                if key.startswith("HTTP_"):
                    self.headers[key[5:].replace("_", "-")] = value
            for key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                if environ.get(key):
                    self.headers[key.replace("_", "-")] = environ[key]
            self.rfile = environ["wsgi.input"]
            self.scheme = environ.get("wsgi.url_scheme", "http")
            self.response = None

        def respond(self, status, value, content_type="application/json", filename=None, headers=()):
            content = json.dumps(value, allow_nan=False).encode() if content_type == "application/json" else value
            content = redact(content.decode("utf-8")).encode("utf-8")
            response_headers = [
                ("Content-Type", content_type), ("Content-Length", str(len(content))),
                ("Cache-Control", "no-store"), ("Referrer-Policy", "no-referrer"),
                ("X-Content-Type-Options", "nosniff"),
                ("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")]
            if public_origin is not None:
                response_headers.append(("Strict-Transport-Security", "max-age=31536000"))
            if getattr(self, "guest_cookie", None):
                response_headers.append(("Set-Cookie", self.guest_cookie))
            if auth is not None and getattr(self, "owner_id", None) is not None:
                response_headers.append(("X-Study-Session", self.csrf))
            response_headers.extend(headers)
            if filename:
                response_headers.append(("Content-Disposition", f'attachment; filename="{filename}"'))
            self.response = (status, response_headers, content)

        def result_bundle(self, study, directory):
            if not application.bundle_slot.acquire(blocking=False):
                raise CapacityError("Another result download is being prepared or transferred. Try again shortly.")
            try:
                self._prepare_result_bundle(study, directory)
            except BaseException:
                if getattr(self, "stream", None):
                    self.stream.unlink(missing_ok=True)
                application.bundle_slot.release()
                raise

        def _prepare_result_bundle(self, study, directory):
            files = []
            for item in study["result"]["tables"]:
                table_id = item["id"]
                if not re.fullmatch(r"[a-z0-9_-]+", table_id):
                    raise ValueError("Saved result table ID is invalid.")
                path = directory / f"{table_id}.csv"
                if not path.is_file():
                    raise ValueError("A saved result table is missing.")
                files.append(path)
            with application.store.connect() as db:
                application.store._require_free_space(sum(path.stat().st_size for path in files)
                                                      + application.store._active_run_headroom(db))
            with tempfile.NamedTemporaryFile(dir=application.store.directory, suffix=".zip", delete=False) as target:
                bundle = Path(target.name)
            self.stream = bundle
            try:
                with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
                    for path in files:
                        archive.write(path, path.name)
                    archive.write(directory / "result.json", "result-manifest.json")
            except BaseException:
                bundle.unlink(missing_ok=True)
                raise
            self.respond(200, b"", "application/zip", f"study-{study['id']}-tables.zip")
            self.response[1][:] = [(key, str(bundle.stat().st_size) if key == "Content-Length" else value)
                                   for key, value in self.response[1]]
            self.stream_release = application.bundle_slot.release

        def redirect(self, location, cookies=()):
            self.respond(302, b"", "text/plain", headers=[("Location", location), *[("Set-Cookie", c) for c in cookies]])

        def guard(self, mutation=False):
            allowed = {f"127.0.0.1:{wsgi.port}", f"localhost:{wsgi.port}"}
            if auth is not None:
                allowed = {urlsplit(auth.config.redirect_uri).netloc}
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin")
            expected_scheme = "https" if public_origin else "http"
            if (host not in allowed or self.scheme != expected_scheme
                    or (origin is not None and origin != f"{expected_scheme}://{host}")):
                raise PermissionError("Request must use the configured website origin and transport.")
            self.owner_id = None
            self.csrf = token
            self.is_guest = False
            public = urlsplit(self.path).path in {"/", "/app.js", "/municipal.js", "/socal.js", "/style.css", "/auth/login", "/auth/callback"}
            if auth is not None and not public:
                session = None
                if allow_guests and auth.cookie_value(self.headers, auth.COOKIE):
                    try:
                        session = auth.authenticate(self.headers)
                    except AuthenticationRequired:
                        pass
                elif not allow_guests:
                    session = auth.authenticate(self.headers)
                if session is None and allow_guests:
                    session, self.guest_cookie = auth.guest(self.headers, create=True)
                    self.is_guest = True
                self.owner_id, self.csrf = session["owner_id"], session["csrf"]
            if mutation and not secrets.compare_digest(self.headers.get("X-Study-Token", ""), self.csrf):
                raise PermissionError("Reload the local application before submitting a study.")

        def do_GET(self):
            try:
                self.guard()
                self.get_route()
            except AuthenticationRequired as exc:
                self.respond(401, {"error": str(exc)})
            except PermissionError as exc:
                self.respond(403, {"error": str(exc)})
            except FileNotFoundError as exc:
                self.respond(404, {"error": str(exc)})
            except CapacityError as exc:
                self.respond(429, {"error": str(exc)})
            except (ValueError, TypeError) as exc:
                self.respond(400, {"error": str(exc)})

        def get_route(self):
            url = urlsplit(self.path)
            if url.path in ("/", "/app.js", "/municipal.js", "/socal.js", "/style.css"):
                name = {"/": "index.html", "/app.js": "app.js", "/municipal.js": "municipal.js", "/socal.js": "socal.js", "/style.css": "style.css"}[url.path]
                mime = {"index.html": "text/html; charset=utf-8", "app.js": "text/javascript; charset=utf-8", "municipal.js": "text/javascript; charset=utf-8", "socal.js": "text/javascript; charset=utf-8", "style.css": "text/css; charset=utf-8"}[name]
                return self.respond(200, (STATIC / name).read_bytes(), mime)
            if url.path == "/auth/login" and auth is not None:
                try:
                    location, cookie = auth.start()
                except Exception:
                    return self.respond(503, {"error": "Sign-in is unavailable. Please try again later."})
                return self.redirect(location, [cookie])
            if url.path == "/auth/callback" and auth is not None:
                return self.redirect("/", auth.callback(parse_qs(url.query, keep_blank_values=True), self.headers))
            if url.path == "/api/session":
                return self.respond(200, {"mode": "oidc" if auth else "local", "token": self.csrf})
            if url.path == "/api/health":
                return self.respond(200, application.health(self.owner_id))
            if url.path == "/api/usage":
                return self.respond(200, application.store.daily_usage(self.owner_id))
            if url.path == "/api/capabilities":
                application.provision_samples(self.owner_id)
                defaults = deepcopy(DEFAULT_REQUEST)
                defaults["dataset_id"] = next(d["id"] for d in application.store.datasets(self.owner_id) if d["name"] == "default_small_business_week.csv")
                return self.respond(200, {**application.capabilities, "defaults": defaults,
                    "nsrdb_configured": all(os.getenv(k) for k in ("NSRDB_API_KEY", "NSRDB_API_EMAIL")),
                    "strategies": SCENARIOS, "token": self.csrf, "auth_mode": "oidc" if auth else "local",
                    "account_type": "guest" if self.is_guest else "member" if auth else "local",
                    "temp_result_hours": application.store.temp_result_hours if allow_guests else None,
                    "hosting_mode": "hosted" if public_origin else "local",
                    "engine": {k: application.engine[k] for k in ("id", "kind", "created_at", "dependencies")}})
            if url.path == "/api/datasets":
                return self.respond(200, application.store.datasets(self.owner_id))
            if url.path == "/api/studies":
                return self.respond(200, application.store.list(self.owner_id))
            match = re.fullmatch(r"/api/studies/([0-9a-f]{32})(?:/(.*))?", url.path)
            if not match:
                raise FileNotFoundError("Resource not found.")
            study = application.store.get(match[1], self.owner_id)
            suffix = match[2]
            directory = application.store.directory / "runs" / match[1]
            if suffix is None:
                return self.respond(200, study)
            if suffix == "request.json":
                return self.respond(200, study["request"], filename="study-request.json")
            if study["status"] != "completed":
                raise ValueError("Results are available after the run completes.")
            if suffix == "result.json":
                return self.respond(200, study["result"], filename="study-result-manifest.json")
            if suffix == "tables.zip":
                return self.result_bundle(study, directory)
            table_match = re.fullmatch(r"tables/([a-z0-9_-]+)(\.csv)?", suffix)
            available = {t["id"] for t in study["result"]["tables"]}
            if not table_match or table_match[1] not in available:
                raise FileNotFoundError("Result table not found.")
            table_id = table_match[1]
            if table_match[2]:
                return self.respond(200, (directory / f"{table_id}.csv").read_bytes(), "text/csv; charset=utf-8", f"{table_id}.csv")
            query = parse_qs(url.query)
            offset = int(query.get("offset", ["0"])[0])
            limit = int(query.get("limit", ["100"])[0])
            if offset < 0 or not 1 <= limit <= 500:
                raise ValueError("Use offset ≥ 0 and a page size of 1–500.")
            if (directory / f"{table_id}.meta.json").is_file():
                from .table_store import read_page
                table = read_page(directory, table_id, offset, limit)
            else:
                table = json.loads((directory / f"{table_id}.json").read_text())
                table["total"] = len(table["data"])
                table["data"] = table["data"][offset:offset + limit]
                table["offset"] = offset
            self.respond(200, table)

        def do_POST(self):
            try:
                self.guard(mutation=True)
                if urlsplit(self.path).path == "/auth/logout" and auth is not None:
                    auth.revoke(self.headers)
                    return self.respond(200, {"signed_out": True}, headers=[("Set-Cookie", auth.cookie(auth.COOKIE, "", 0))])
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise ValueError("Send application/json.")
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_BODY:
                    raise ValueError("Request must be nonempty and at most 20 MB.")
                body = json.loads(self.rfile.read(length))
                if allow_guests and self.is_guest and urlsplit(self.path).path in {
                    "/api/location", "/api/weather", "/api/utilities", "/api/ess/resolve",
                    "/api/solar/optimize", "/api/v1/utility-resolution",
                    "/api/v1/municipal/eligibility", "/api/v1/municipal/bill",
                }:
                    application.store.admit_guest_interaction(self.owner_id)
                save = re.fullmatch(r"/api/studies/([0-9a-f]{32})/save", urlsplit(self.path).path)
                if save and allow_guests:
                    if body != {}:
                        raise ValueError("Send an empty save request.")
                    if self.is_guest:
                        raise AuthenticationRequired("Sign in to save this study to your profile.")
                    guest, _ = auth.guest(self.headers)
                    if guest is not None:
                        try:
                            saved = application.store.save_guest_study(save[1], guest["owner_id"], self.owner_id)
                            return self.respond(200, saved)
                        except FileNotFoundError:
                            pass
                    return self.respond(200, application.store.save_member_study(save[1], self.owner_id))
                cancel = re.fullmatch(r"/api/studies/([0-9a-f]{32})/cancel", urlsplit(self.path).path)
                if cancel:
                    if body != {}:
                        raise ValueError("Send an empty cancellation request.")
                    study = application.store.cancel(cancel[1], self.owner_id)
                    return self.respond(202 if study["status"] == "cancelling" else 200, study)
                if urlsplit(self.path).path == "/api/v1/pge/annual-studies":
                    return self.respond(202, application.submit_pge_annual(body, self.owner_id,
                                                                           temporary=allow_guests))
                if urlsplit(self.path).path == "/api/v1/socal/studies":
                    return self.respond(202, application.submit_socal(body, self.owner_id, temporary=allow_guests))
                if urlsplit(self.path).path == "/api/v1/municipal/studies":
                    return self.respond(202, application.submit_municipal(body, self.owner_id, temporary=allow_guests))
                municipal_routes = {"/api/v1/utility-resolution": "utility-resolution",
                                    "/api/v1/municipal/eligibility": "municipal-eligibility",
                                    "/api/v1/municipal/bill": "municipal-bill"}
                if urlsplit(self.path).path in municipal_routes:
                    return self.respond(200, application.interactive(application.candidate, municipal_routes[urlsplit(self.path).path], body, self.owner_id))
                if urlsplit(self.path).path == "/api/utilities":
                    return self.respond(200, application.interactive(application.utilities, body, self.owner_id))
                if urlsplit(self.path).path in ("/api/location", "/api/weather"):
                    kind = "location" if urlsplit(self.path).path == "/api/location" else "weather"
                    return self.respond(200, application.interactive(application.resource, kind, body, self.owner_id))
                if urlsplit(self.path).path in ("/api/ess/resolve", "/api/solar/optimize"):
                    kind = "ess" if urlsplit(self.path).path == "/api/ess/resolve" else "orientation"
                    return self.respond(200, application.interactive(application.candidate, kind, body, self.owner_id))
                if urlsplit(self.path).path == "/api/datasets":
                    if not isinstance(body, dict) or not isinstance(body.get("csv"), str) or not isinstance(body.get("name"), str):
                        raise ValueError("Provide CSV text and a filename.")
                    dataset = application.store.add_dataset(body["csv"].encode("utf-8"), body["name"], self.owner_id)
                    return self.respond(201, dataset)
                if urlsplit(self.path).path == "/api/studies":
                    if isinstance(body, dict) and body.get("schema_version") == 7:
                        raise ValueError("Submit PG&E annual statement replays through /api/v1/pge/annual-studies.")
                    if isinstance(body, dict) and body.get("schema_version") in (4, 6):
                        raise ValueError("Submit municipal studies through /api/v1/municipal/studies.")
                    if isinstance(body, dict) and body.get("schema_version") == 3 and "candidate_defaults" not in application.capabilities:
                        raise ValueError("This pinned engine does not support candidate studies.")
                    if isinstance(body, dict) and body.get("schema_version") == 2 and "site_defaults" not in application.capabilities:
                        raise ValueError("Restart with --refresh-engine to enable location studies.")
                    if isinstance(body, dict) and body.get("tariff_id") not in {None, *(t["id"] for t in application.capabilities["tariffs"])}:
                        raise ValueError("Choose a supported tariff.")
                    return self.respond(202, application.store.submit(body, application.engine, self.owner_id,
                                                                       temporary=allow_guests))
                raise FileNotFoundError("Resource not found.")
            except AuthenticationRequired as exc:
                self.respond(401, {"error": str(exc)})
            except PermissionError as exc:
                self.respond(403, {"error": str(exc)})
            except FileNotFoundError as exc:
                self.respond(404, {"error": str(exc)})
            except CapacityError as exc:
                headers = [("Retry-After", str(exc.retry_after))] if exc.retry_after is not None else []
                self.respond(429, {"error": str(exc)}, headers=headers)
            except StudyConflict as exc:
                self.respond(409, {"error": str(exc)})
            except (ValueError, TypeError, UnicodeError) as exc:
                self.respond(400, {"error": str(exc)})

    def wsgi(environ, start_response):
        handler = Handler(environ)
        try:
            method = environ.get("REQUEST_METHOD", "GET")
            if method == "GET":
                handler.do_GET()
            elif method == "POST":
                handler.do_POST()
            else:
                handler.respond(405, {"error": "Method not allowed."}, headers=[("Allow", "GET, POST")])
        except Exception:
            # Do not let Waitress log request/provider details or a credential-bearing traceback.
            handler.respond(500, {"error": "The server could not complete this request."})
        status, headers, content = handler.response
        start_response(f"{status} {HTTPStatus(status).phrase}", headers)
        if getattr(handler, "stream", None):
            try:
                return TemporaryFileResponse(handler.stream, handler.stream_release)
            except OSError:
                handler.stream.unlink(missing_ok=True)
                handler.stream_release()
                raise
        return [content]

    wsgi.port = port
    return wsgi


class WebServer:
    """One Waitress process; runner remains separately managed in hosted mode."""
    def __init__(self, app, port, *, proxied=False):
        self.stopped = threading.Event()
        self.closed = False
        options = dict(host="127.0.0.1", port=port, threads=4,
                       max_request_body_size=MAX_BODY, max_request_header_size=32768,
                       clear_untrusted_proxy_headers=True, expose_tracebacks=False,
                       ident="Microgrid", channel_timeout=30)
        if proxied:
            # Caddy must run on the same host and overwrite this header.
            # Neither Host nor the user's identity is taken from forwarding headers.
            options.update(trusted_proxy="127.0.0.1", trusted_proxy_count=1,
                           trusted_proxy_headers={"x-forwarded-proto"})
        self.server = create_server(app, **options)
        self.server_port = int(self.server.effective_port)
        app.port = self.server_port

    def serve_forever(self):
        try:
            while not self.stopped.is_set():
                wasyncore.loop(timeout=.1, count=1, map=self.server._map)
        finally:
            self.server_close()

    def shutdown(self):
        self.stopped.set()

    def server_close(self):
        self.stopped.set()
        if not self.closed:
            self.closed = True
            self.server.task_dispatcher.shutdown()
            wasyncore.close_all(map=self.server._map, ignore_all=True)


def make_server(application, port=8765, *, auth=None, public_origin=None, allow_guests=False):
    app = make_wsgi_app(application, port, auth=auth, public_origin=public_origin, allow_guests=allow_guests)
    server = WebServer(app, port, proxied=public_origin is not None)
    if public_origin is None and auth is not None and urlsplit(auth.config.redirect_uri).netloc not in {
            f"127.0.0.1:{server.server_port}", f"localhost:{server.server_port}"}:
        server.server_close()
        raise ValueError("OIDC callback port must match this loopback server.")
    return server


def main():
    parser = argparse.ArgumentParser(description="Run the local Microgrid Simulator web application.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "local_web")
    parser.add_argument("--env-file", type=Path, default=ROOT / "src" / ".env", help="Read only weather and Electricity Maps credentials from this local .env file.")
    parser.add_argument("--refresh-engine", action="store_true", help="Explicitly pin the current source and dependencies as a development snapshot.")
    parser.add_argument("--external-worker", action="store_true", help="Queue studies for a separately started src.local_web.runner process.")
    parser.add_argument("--hosted", action="store_true", help="Require OIDC and MICROGRID_PUBLIC_ORIGIN behind an HTTPS proxy on this host; API remains loopback-only.")
    parser.add_argument("--allow-guests", action="store_true", help="Allow temporary cookie-bound studies before sign-in; requires OIDC.")
    args = parser.parse_args()
    if args.env_file.is_file():
        from dotenv import dotenv_values
        values = dotenv_values(args.env_file)
        for key in ("NSRDB_API_KEY", "NSRDB_API_EMAIL", "ELECTRICITY_MAPS_API_KEY"):
            if values.get(key):
                os.environ.setdefault(key, values[key])
    config = OIDCConfig.from_environment()
    if args.allow_guests and config is None:
        parser.error("--allow-guests requires MICROGRID_AUTH_MODE=oidc and OIDC configuration.")
    from .hosting import public_origin_from_environment
    public_origin = public_origin_from_environment(args.hosted, config)
    application = Application(args.data_dir, refresh=args.refresh_engine,
                              embedded_worker=not (args.external_worker or args.hosted))
    try:
        server = make_server(application, args.port, auth=Sessions(application.store, config) if config else None,
                             public_origin=public_origin, allow_guests=args.allow_guests)
        origin = f"http://{urlsplit(config.redirect_uri).netloc}" if config else f"http://127.0.0.1:{server.server_port}"
        origin = public_origin or origin
        print(f"Microgrid Simulator (Waitress): {origin}", flush=True)
        if args.hosted:
            print("Hosted mode: start the separate worker and HTTPS proxy; backend listens only on localhost.", flush=True)
        previous_signals = {sig: signal.signal(sig, lambda *_: server.shutdown())
                            for sig in (signal.SIGINT, signal.SIGTERM)}
        print(f"Studies: {application.store.directory}\nEngine snapshot: {application.engine['id'][:12]}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
            for sig, previous in previous_signals.items():
                signal.signal(sig, previous)
    finally:
        application.close()


if __name__ == "__main__":
    main()
