"""Loopback-only HTTP API and static browser UI, using the Python standard library."""

import argparse
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
from urllib.parse import parse_qs, urlsplit

from .contract import DEFAULT_REQUEST, SCENARIOS
from .runtime import Application, ROOT

MAX_BODY = 20 * 1024 * 1024
STATIC = Path(__file__).with_name("static")


def make_server(application, port=8765):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(30)

        def log_message(self, *_args):
            pass

        def respond(self, status, value, content_type="application/json", filename=None):
            content = json.dumps(value, allow_nan=False).encode() if content_type == "application/json" else value
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(content)

        def guard(self, mutation=False):
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin")
            if host not in allowed or (origin is not None and origin != f"http://{host}"):
                raise PermissionError("This service accepts same-origin localhost requests only.")
            if mutation and not secrets.compare_digest(self.headers.get("X-Study-Token", ""), token):
                raise PermissionError("Reload the local application before submitting a study.")

        def do_GET(self):
            try:
                self.guard()
                self.get_route()
            except PermissionError as exc:
                self.respond(403, {"error": str(exc)})
            except FileNotFoundError as exc:
                self.respond(404, {"error": str(exc)})
            except (ValueError, TypeError) as exc:
                self.respond(400, {"error": str(exc)})

        def get_route(self):
            url = urlsplit(self.path)
            if url.path in ("/", "/app.js", "/style.css"):
                name = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}[url.path]
                mime = {"index.html": "text/html; charset=utf-8", "app.js": "text/javascript; charset=utf-8", "style.css": "text/css; charset=utf-8"}[name]
                return self.respond(200, (STATIC / name).read_bytes(), mime)
            if url.path == "/api/capabilities":
                defaults = deepcopy(DEFAULT_REQUEST)
                defaults["dataset_id"] = next(d["id"] for d in application.store.datasets() if d["name"] == "default_small_business_week.csv")
                return self.respond(200, {**application.capabilities, "defaults": defaults,
                    "nsrdb_configured": all(os.getenv(k) for k in ("NSRDB_API_KEY", "NSRDB_API_EMAIL")),
                    "strategies": SCENARIOS, "token": token,
                    "engine": {k: application.engine[k] for k in ("id", "kind", "created_at", "dependencies")}})
            if url.path == "/api/datasets":
                return self.respond(200, application.store.datasets())
            if url.path == "/api/studies":
                return self.respond(200, application.store.list())
            match = re.fullmatch(r"/api/studies/([0-9a-f]{32})(?:/(.*))?", url.path)
            if not match:
                raise FileNotFoundError("Resource not found.")
            study = application.store.get(match[1])
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
            table = json.loads((directory / f"{table_id}.json").read_text())
            table["total"] = len(table["data"])
            table["data"] = table["data"][offset:offset + limit]
            table["offset"] = offset
            self.respond(200, table)

        def do_POST(self):
            try:
                self.guard(mutation=True)
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise ValueError("Send application/json.")
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_BODY:
                    raise ValueError("Request must be nonempty and at most 20 MB.")
                body = json.loads(self.rfile.read(length))
                if urlsplit(self.path).path in ("/api/location", "/api/weather"):
                    kind = "location" if urlsplit(self.path).path == "/api/location" else "weather"
                    return self.respond(200, application.resource(kind, body))
                if urlsplit(self.path).path in ("/api/ess/resolve", "/api/solar/optimize"):
                    kind = "ess" if urlsplit(self.path).path == "/api/ess/resolve" else "orientation"
                    return self.respond(200, application.candidate(kind, body))
                if urlsplit(self.path).path == "/api/datasets":
                    if not isinstance(body, dict) or not isinstance(body.get("csv"), str) or not isinstance(body.get("name"), str):
                        raise ValueError("Provide CSV text and a filename.")
                    dataset = application.store.add_dataset(body["csv"].encode("utf-8"), body["name"])
                    return self.respond(201, dataset)
                if urlsplit(self.path).path == "/api/studies":
                    if isinstance(body, dict) and body.get("schema_version") == 3 and "candidate_defaults" not in application.capabilities:
                        raise ValueError("This pinned engine does not support candidate studies.")
                    if isinstance(body, dict) and body.get("schema_version") == 2 and "site_defaults" not in application.capabilities:
                        raise ValueError("Restart with --refresh-engine to enable location studies.")
                    if isinstance(body, dict) and body.get("tariff_id") not in {None, *(t["id"] for t in application.capabilities["tariffs"])}:
                        raise ValueError("Choose a supported tariff.")
                    return self.respond(202, application.store.submit(body, application.engine))
                raise FileNotFoundError("Resource not found.")
            except PermissionError as exc:
                self.respond(403, {"error": str(exc)})
            except FileNotFoundError as exc:
                self.respond(404, {"error": str(exc)})
            except (ValueError, TypeError, UnicodeError) as exc:
                self.respond(400, {"error": str(exc)})

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description="Run the local Microgrid Simulator web application.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".cache" / "local_web")
    parser.add_argument("--env-file", type=Path, default=ROOT / "src" / ".env", help="Read only NSRDB credentials from this local .env file.")
    parser.add_argument("--refresh-engine", action="store_true", help="Explicitly pin the current source and dependencies as a development snapshot.")
    args = parser.parse_args()
    if args.env_file.is_file():
        from dotenv import dotenv_values
        values = dotenv_values(args.env_file)
        for key in ("NSRDB_API_KEY", "NSRDB_API_EMAIL"):
            if values.get(key):
                os.environ.setdefault(key, values[key])
    application = Application(args.data_dir, refresh=args.refresh_engine)
    try:
        server = make_server(application, args.port)
        print(f"Microgrid Simulator: http://127.0.0.1:{server.server_port}", flush=True)
        print(f"Studies: {application.store.directory}\nEngine snapshot: {application.engine['id'][:12]}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    finally:
        application.close()


if __name__ == "__main__":
    main()
