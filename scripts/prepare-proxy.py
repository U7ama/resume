"""Prepare ignored Cloudflare bindings for an already deployed AWS origin."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--origin', required=True)
    args = parser.parse_args()
    url = urlsplit(args.origin)
    if url.scheme != 'https' or not url.hostname.endswith('.lambda-url.us-east-1.on.aws') or url.path not in {'', '/'}:
        raise ValueError('Use the HTTPS origin URL returned by the AWS stack.')
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / '.private/runtime.json').read_text())
    settings = {'AWS_ORIGIN': args.origin, 'AWS_ORIGIN_SECRET': config['origin_secret'],
                'ASSET_VERSION': hashlib.sha256((root / 'output/aws/api.zip').read_bytes()).hexdigest()[:20]}
    output = root / '.private/proxy-secrets.json'
    output.write_text(json.dumps(settings))
    os.chmod(output, 0o600)
    print('Prepared private proxy bindings and asset cache version.')


if __name__ == '__main__':
    main()
