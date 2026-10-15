"""Prepare ignored local secrets without printing them or changing DeviceOps."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--qwen-env', required=True)
    parser.add_argument('--origin', action='append', default=[])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    private = root / '.private'
    private.mkdir(mode=0o700, exist_ok=True)
    os.chmod(private, 0o700)
    runtime = private / 'runtime.json'
    settings = json.loads(runtime.read_text()) if runtime.exists() else {}
    values = {}
    for line in Path(args.qwen_env).read_text().splitlines():
        key, separator, value = line.partition('=')
        if separator and not key.startswith('#'):
            values[key.strip()] = value.strip().strip('\"\'')
    key = values.get('ABQWEN_API_KEY') or values.get('QWEN_API_KEY')
    if not key:
        raise ValueError('Qwen API key is missing from the selected private configuration.')
    if 'code_hash' not in settings:
        code = secrets.token_urlsafe(18)
        salt = secrets.token_bytes(16)
        settings.update(code_salt=salt.hex(), code_hash=hashlib.pbkdf2_hmac('sha256', code.encode(), salt, 310000).hex(), rate_salt=secrets.token_hex(32))
        code_file = private / 'access-code.txt'
        code_file.write_text(code + '\n')
        os.chmod(code_file, 0o600)
    settings.update(qwen_key=key, qwen_model=values.get('QWEN_MODEL_ID', 'qwen3.7-flash'),
                    qwen_base=values.get('QWEN_BASE_URL', 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1'),
                    qwen_usage_confirmed=values.get('QWEN_USAGE_CONFIRMED') == 'true',
                    allowed_origins=sorted(set(settings.get('allowed_origins', []) + ['https://resume.usamaaslam.site'] + args.origin)))
    settings.setdefault('origin_secret', secrets.token_hex(32))
    runtime.write_text(json.dumps(settings))
    os.chmod(runtime, 0o600)
    print('Private runtime prepared. Access code: .private/access-code.txt (contents not printed).')


if __name__ == '__main__':
    main()
