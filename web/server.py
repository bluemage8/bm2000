"""Tiny stdlib server for the Bridge Master 2000 web edition.

Run:
    py web/server.py            # http://127.0.0.1:8321
    py web/server.py 9000       # custom port

Serves the static files in this folder (index.html / app.js / style.css) and
the parsed deal table at /api/deals (web/deals.json, produced by gen_deals.py
if missing).
"""
import json
import os
import socketserver
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent

# ThreadingHTTPServer exists in Python 3.7+; backport for 3.6 so the server
# handles concurrent connections on the target (CentOS 7 = Python 3.6).
class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def ensure_deals() -> None:
    p = HERE / "deals.json"
    if not p.exists():
        print("deals.json missing -- generating from winexe/hands ...")
        gen = HERE / "gen_deals.py"
        import runpy
        runpy.run_path(str(gen), run_name="__main__")


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path) -> None:
        if not path.is_file():
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return
        data = path.read_bytes()
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".png": "image/png",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }.get(path.suffix.lower(), "application/octet-stream")
        self._send(200, data, ctype)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/api/deals", "/api/deals/"):
            p = HERE / "deals.json"
            if p.exists():
                self._send(200, p.read_bytes(), "application/json; charset=utf-8")
            else:
                self._send(500, b"deals.json not generated", "text/plain")
            return
        # static
        rel = path.lstrip("/") or "index.html"
        target = (HERE / rel).resolve()
        # confine to HERE
        if HERE.resolve() not in target.parents and target != HERE.resolve():
            self._send(403, b"Forbidden", "text/plain")
            return
        if target.is_dir():
            target = target / "index.html"
        self._serve_file(target)

    def log_message(self, fmt: str, *args) -> None:  # quieter log
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main() -> None:
    ensure_deals()
    # host: 0.0.0.0 for a network deployment (so clients on the LAN can reach
    # it); override with BM2000_HOST if you want to bind to a specific address.
    host = os.environ.get("BM2000_HOST", "0.0.0.0")
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("BM2000_PORT", "8321"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print("Bridge Master 2000 (web) running at http://%s:%d" % (host, port))
    print("Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
