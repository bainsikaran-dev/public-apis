#!/usr/bin/env python3
"""Serve README.md rendered as HTML so the sandbox preview has something to show.

This repository is a curated Markdown list plus a Python validation toolkit, so
there is no application server of its own. This tiny dev server renders the
repository's README.md (and serves the repository's static assets, e.g. the
images it references) on port 3000. It re-renders whenever README.md changes on
disk, so edits are visible on refresh without a restart.
"""

import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

import markdown

APP_DIR = os.path.realpath(os.environ.get("APP_DIR", "/app"))
README = os.path.join(APP_DIR, "README.md")
PORT = int(os.environ.get("PORT", "3000"))

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json",
    ".md": "text/markdown; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
}

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>public-apis</title>
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: #ffffff;
    color: #1f2328;
    font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  }
  .topbar {
    position: sticky;
    top: 0;
    z-index: 10;
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 8px 12px;
    padding: 12px 24px;
    background: #f6f8fa;
    border-bottom: 1px solid #d1d9e0;
  }
  .topbar strong { font-size: 15px; letter-spacing: .01em; }
  .topbar span { color: #59636e; font-size: 13px; }
  main {
    max-width: 1020px;
    margin: 0 auto;
    padding: 24px 24px 96px;
    overflow-wrap: break-word;
  }
  h1, h2, h3, h4 { line-height: 1.25; margin: 28px 0 12px; font-weight: 600; }
  h1 { font-size: 2em; padding-bottom: .3em; border-bottom: 1px solid #d1d9e0; }
  h2 { font-size: 1.5em; padding-bottom: .3em; border-bottom: 1px solid #d1d9e0; }
  h3 { font-size: 1.2em; }
  p, ul, ol, table, blockquote { margin: 0 0 16px; }
  a { color: #0969da; text-decoration: none; }
  a:hover { text-decoration: underline; }
  img { max-width: 100%; height: auto; }
  code {
    font: 85%/1.5 ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
    background: #eff1f3;
    padding: .2em .4em;
    border-radius: 6px;
  }
  pre { background: #f6f8fa; padding: 16px; border-radius: 6px; overflow: auto; }
  pre code { background: none; padding: 0; }
  table { border-collapse: collapse; width: 100%; display: block; overflow-x: auto; }
  th, td { border: 1px solid #d1d9e0; padding: 6px 13px; text-align: left; vertical-align: top; }
  tr:nth-child(2n) { background: #f6f8fa; }
  th { background: #f6f8fa; font-weight: 600; }
  blockquote {
    margin-left: 0;
    padding: 0 1em;
    color: #59636e;
    border-left: .25em solid #d1d9e0;
  }
  hr { height: 1px; background: #d1d9e0; border: 0; margin: 24px 0; }
</style>
</head>
<body>
<div class="topbar">
  <strong>public-apis</strong>
  <span>Rendered from README.md &mdash; edit it and refresh</span>
</div>
<main>
{{content}}
</main>
</body>
</html>
"""

_cache = {"mtime": None, "html": None}


def render_readme() -> str:
    """Render README.md, reusing the previous output while the file is unchanged."""
    mtime = os.path.getmtime(README)
    if _cache["mtime"] != mtime:
        with open(README, encoding="utf-8") as handle:
            raw = handle.read()
        body = markdown.markdown(
            raw,
            extensions=["tables", "toc", "fenced_code", "sane_lists", "attr_list"],
            output_format="html5",
        )
        _cache["mtime"] = mtime
        _cache["html"] = PAGE.replace("{{content}}", body)
    return _cache["html"]


class Handler(BaseHTTPRequestHandler):
    server_version = "public-apis-preview/1.0"

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        path = unquote(urlparse(self.path).path)

        if path == "/healthz":
            self._send(200, b"ok\n", "text/plain; charset=utf-8")
            return

        if path in ("", "/", "/index.html"):
            self._send(200, render_readme().encode("utf-8"), "text/html; charset=utf-8")
            return

        # Everything else is a static asset referenced by README.md, confined to APP_DIR.
        target = os.path.realpath(os.path.join(APP_DIR, path.lstrip("/")))
        if target.startswith(APP_DIR + os.sep) and os.path.isfile(target):
            extension = os.path.splitext(target)[1].lower()
            with open(target, "rb") as handle:
                self._send(200, handle.read(), CONTENT_TYPES.get(extension, "application/octet-stream"))
            return

        self._send(404, b"Not found\n", "text/plain; charset=utf-8")

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main() -> None:
    if not os.path.isfile(README):
        sys.exit(f"README.md not found at {README}")

    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Serving README.md on http://0.0.0.0:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
