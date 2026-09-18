#!/bin/sh
# MEMS modeling web viewer — port 8971 (old modeling project uses 8941/8942)
# Serves with no-store headers so re-exported GLB/manifest/app.js always load fresh.
cd "$(dirname "$0")" && exec python3 - <<'PY'
import http.server

class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

http.server.ThreadingHTTPServer(('127.0.0.1', 8971), Handler).serve_forever()
PY
