#!/usr/bin/env python3
"""Serve the translator-ladder dashboard live while ladder.py runs.

    python3 ladder_server.py [--port 8778] [--dir ladder]

Three routes, all local:
    /              the dashboard, built from the current results and polling
    /results.json  the runner's results file, as it stands right now
    /log           the last lines of the runner's log (ladder/run.log)

The runner writes results.json atomically after every chapter, so a read
never sees a torn file; the page polls every three seconds and redraws when
the `updated` stamp moves. Nothing here talks to the simulation or the
models; it only reads what the runner wrote.
"""
from __future__ import annotations

import argparse
import json
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import ladder_dashboard as dash

LAST_GOOD: dict = {}


def _read_results(path: str) -> dict:
    global LAST_GOOD
    if os.path.exists(path):
        try:
            with open(path) as f:
                LAST_GOOD = json.load(f)
        except ValueError:
            pass
    return LAST_GOOD or dash.plan_only("qwen3.6:35b,qwen3.5:9b,qwen3.5:4b,qwen2.5:1.5b",
                                        "english,compact")


def make_handler(directory: str):
    results_path = os.path.join(directory, "results.json")
    log_path = os.path.join(directory, "run.log")

    class H(BaseHTTPRequestHandler):
        def _send(self, body: bytes, ctype: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            path = urlparse(self.path).path
            if path in ("/", "/index.html", "/dashboard.html"):
                self._send(dash.build_html(_read_results(results_path), live=True).encode(),
                           "text/html; charset=utf-8")
            elif path == "/results.json":
                self._send(json.dumps(_read_results(results_path)).encode(), "application/json")
            elif path == "/log":
                tail = ""
                if os.path.exists(log_path):
                    with open(log_path, "rb") as f:
                        f.seek(0, 2)
                        f.seek(max(0, f.tell() - 12000))
                        tail = f.read().decode("utf-8", "replace")
                    lines = tail.splitlines()[-40:]
                    tail = "\n".join(lines)
                self._send(tail.encode(), "text/plain; charset=utf-8")
            else:
                self.send_error(404)

        def log_message(self, *args):  # quiet
            pass

    return H


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8778)
    ap.add_argument("--host", default="127.0.0.1",
                    help="bind address; 0.0.0.0 to reach it from other devices on the LAN")
    ap.add_argument("--dir", default="ladder")
    ap.add_argument("--open", action="store_true", help="open the browser")
    args = ap.parse_args()
    os.makedirs(args.dir, exist_ok=True)
    srv = ThreadingHTTPServer((args.host, args.port), make_handler(args.dir))
    url = f"http://{'127.0.0.1' if args.host in ('0.0.0.0', '') else args.host}:{args.port}/"
    print(f"ladder dashboard live at {url} (bound to {args.host}; reads {args.dir}/results.json "
          f"and {args.dir}/run.log)")
    if args.open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
