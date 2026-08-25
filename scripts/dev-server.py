import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class CORSHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Content-Length', '0')
        self.end_headers()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(directory)
    server = ThreadedHTTPServer(('0.0.0.0', port), CORSHandler)
    print(f'Serving {directory} on port {port} with CORS enabled...')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
