"""Verify the deployed origin or public site without printing credentials or CV text."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import quote


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--direct-origin', action='store_true')
    parser.add_argument('--generate', action='store_true')
    parser.add_argument('--seed', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / '.private/runtime.json').read_text())
    cookie = ''

    def request(path, data=None, *, origin='https://resume.usamaaslam.site', authenticated=True, proxy=True):
        nonlocal cookie
        headers = {'Origin': origin, 'User-Agent': 'Mozilla/5.0 ResumeStudioDeploymentCheck'}
        if args.direct_origin and proxy:
            headers['x-resume-origin'] = config['origin_secret']
            headers['x-resume-client-ip'] = 'deployment-check'
        if authenticated and cookie:
            headers['Cookie'] = cookie
        body = None
        if data is not None:
            body = json.dumps(data).encode()
            headers['Content-Type'] = 'application/json'
            headers['x-amz-content-sha256'] = hashlib.sha256(body).hexdigest()
        try:
            result = urlopen(Request(args.url.rstrip('/') + path, data=body, headers=headers), timeout=75)
        except HTTPError as error:
            result = error
        with result:
            raw = result.read()
            if result.headers.get('Set-Cookie'):
                cookie = result.headers['Set-Cookie'].split(';')[0]
            value = json.loads(raw) if 'application/json' in result.headers.get('Content-Type', '') else raw
            return result.status, value

    if args.direct_origin:
        assert request('/', authenticated=False, proxy=False)[0] == 403, 'Direct origin must reject missing proxy credentials'
        print('Origin rejects requests without the private proxy header.')
    for path in ['/', '/resume.md', '/academic.md', '/general.md', '/studio.js', '/studio.css']:
        code, body = request(path, authenticated=False)
        assert code == 200, f'Public asset failed: {path} ({code})'
    assert request('/.private/runtime.json', authenticated=False)[0] == 404
    assert request('/api/versions?type=software', authenticated=False)[0] == 401
    assert request('/api/login', {'code': 'not-a-real-code'}, origin='https://untrusted.example')[0] == 403
    code, _ = request('/api/login', {'code': (root / '.private/access-code.txt').read_text().strip()})
    assert code == 200, f'Owner login failed ({code})'
    print('Public assets, origin checks, private history and owner login passed.')
    for kind, filename in [('software', 'resume.md'), ('academic', 'academic.md'), ('general', 'general.md')]:
        code, current = request('/api/current?type=' + kind)
        assert code == 200
        if args.seed and not current.get('id'):
            markdown = (root / filename).read_text()
            code, version = request('/api/save', {'type': kind, 'markdown': markdown, 'baseId': None, 'note': 'Initial ' + kind + ' CV'})
            assert code == 201, f'Initial {kind} save failed ({code})'
            code, earlier = request('/api/version?type=' + kind + '&id=' + quote(version['id'], safe=''))
            assert code == 200 and earlier['markdown'] == markdown
            assert request('/api/save', {'type': kind, 'markdown': markdown, 'baseId': None, 'note': 'Conflict check'})[0] == 409
        code, history = request('/api/versions?type=' + kind)
        assert code == 200
        print(kind + ': private current/history read passed; saved versions=' + str(len(history['versions'])))
    if args.generate:
        code, draft = request('/api/generate', {'type': 'academic', 'markdown': (root / 'academic.md').read_text(),
            'instruction': 'Prepare a concise academic CV for postgraduate digital project management study in France. Use only the supplied facts, retain employment dates, and do not invent a thesis title, publication, IELTS score or French proficiency.'})
        if code != 200:
            print('Live Qwen generation failed:', code, draft.get('error', 'Provider unavailable'))
            return 1
        output = root / 'output/qa'
        output.mkdir(parents=True, exist_ok=True)
        (output / 'qwen-academic-draft.md').write_text(draft['markdown'])
        print('Live Qwen generation passed; review draft saved under output/qa. No AI text was saved to cloud history.')
    assert request('/api/logout', {})[0] == 200
    assert request('/api/current?type=software')[0] == 401
    print('Logout revocation passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
