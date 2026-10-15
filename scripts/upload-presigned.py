"""Upload an explicit manifest using short-lived signed URLs supplied on stdin."""
import json
import mimetypes
from pathlib import Path
import sys
import termios
from urllib.request import Request, urlopen


def main():
    if sys.stdin.isatty():
        settings = termios.tcgetattr(sys.stdin)
        settings[3] &= ~(termios.ECHO | termios.ICANON)
        settings[6][termios.VMIN] = 1
        settings[6][termios.VTIME] = 0
        termios.tcsetattr(sys.stdin, termios.TCSANOW, settings)
    print('Ready for upload manifest on stdin (input hidden).', flush=True)
    manifest = json.loads(sys.stdin.readline())
    for item in manifest:
        path = Path(item['path'])
        content_type = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
        if path.suffix == '.md':
            content_type = 'text/plain; charset=utf-8'
        request = Request(item['url'], data=path.read_bytes(), method='PUT', headers={
            'Content-Type': content_type, 'Cache-Control': 'no-store' if item['key'].startswith('private/') else 'public, max-age=300'})
        try:
            with urlopen(request, timeout=60) as result:
                if result.status != 200:
                    raise RuntimeError('Upload failed')
        except Exception as error:
            # Do not print presigned URLs or private file contents.
            print(f'Upload failed for {item["key"]}: {type(error).__name__}', file=sys.stderr)
            return 1
        print('Uploaded ' + item['key'], flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
