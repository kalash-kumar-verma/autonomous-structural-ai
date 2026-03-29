"""Serve the frontend folder reliably from the project root.

Usage:
    python serve_frontend.py [port]

This avoids common issues where the simple Python HTTP server is started from
the wrong working directory and returns 404 for `/`.
"""

from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5500
ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"

if not FRONTEND_DIR.is_dir():
    raise SystemExit(f"Frontend directory not found: {FRONTEND_DIR}")

class FrontendHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

if __name__ == "__main__":
    server_address = ("", PORT)
    httpd = ThreadingHTTPServer(server_address, FrontendHandler)
    print(f"Serving frontend from {FRONTEND_DIR} on http://127.0.0.1:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.server_close()
