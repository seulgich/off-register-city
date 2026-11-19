#!/usr/bin/env python3
"""Serve Off-Register City on http://127.0.0.1:5502 and open it in the browser.
The page has to run from a small local server: browsers do not let a page read
its own letter sheets (for the threshold) when it is opened straight from the folder."""
import http.server, os, socketserver, sys, threading, webbrowser
PORT = 5502
os.chdir(os.path.dirname(os.path.abspath(__file__)))
class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')  # always the latest files after an edit
        super().end_headers()
    def log_message(self, *a): pass
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(('127.0.0.1', PORT), Handler) as httpd:
    url = f'http://127.0.0.1:{PORT}/'
    print(f'Signage, Inverted is running at {url}  (close this window to stop)')
    if '--no-browser' not in sys.argv: threading.Timer(.6, lambda: webbrowser.open(url)).start()
    httpd.serve_forever()
