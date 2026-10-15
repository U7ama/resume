"""Local preview with an explicit public-file allowlist and SQLite persistence."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import mimetypes
import os
from pathlib import Path
import sys
from urllib.parse import parse_qsl, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
os.environ['PUBLIC_DIR'] = str(ROOT)
from app import handle

PUBLIC_FILES = {'index.html', 'studio.js', 'studio.css', 'resume.md', 'academic.md', 'general.md',
                'Usama DP.jpeg', 'Usama DP headshot.jpeg', 'robots.txt', 'sitemap.xml'}


class Preview(BaseHTTPRequestHandler):
    def do_GET(self):
        self.dispatch()

    def do_POST(self):
        self.dispatch()

    def dispatch(self):
        url = urlsplit(self.path)
        if url.path.startswith('/api/'):
            length = int(self.headers.get('content-length', '0'))
            if length > 40000:
                self.send_error(413)
                return
            result = handle(self.command, url.path, dict(self.headers), self.rfile.read(length), self.client_address[0], dict(parse_qsl(url.query)))
            self.send_response(result['statusCode'])
            for key, value in result['headers'].items():
                self.send_header(key, value)
            for cookie in result.get('cookies', []):
                self.send_header('Set-Cookie', cookie)
            self.end_headers()
            self.wfile.write(result['body'].encode())
            return
        name = unquote(url.path).lstrip('/') or 'index.html'
        if self.command != 'GET' or name not in PUBLIC_FILES:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', mimetypes.guess_type(name)[0] or 'text/plain')
        self.end_headers()
        self.wfile.write((ROOT / name).read_bytes())

    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=4081)
    args = parser.parse_args()
    print(f'Resume Studio preview: http://localhost:{args.port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Preview).serve_forever()


if __name__ == '__main__':
    main()
