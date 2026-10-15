import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import app
from store import SQLiteStore


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        app._store = SQLiteStore(str(Path(self.temp.name) / 'test.sqlite3'))
        salt = b'a' * 16
        app._config = {'allowed_origins': ['https://resume.example'], 'code_salt': salt.hex(),
                       'code_hash': hashlib.pbkdf2_hmac('sha256', b'test-access-code', salt, 310000).hex(),
                       'rate_salt': 'test-salt', 'qwen_key': 'fake-key', 'qwen_model': 'test-model',
                       'qwen_base': 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1', 'qwen_usage_confirmed': True}
        app._config_time = time.time()
        self.headers = {'origin': 'https://resume.example', 'content-type': 'application/json'}
        app.PUBLIC = Path(__file__).resolve().parents[1]
        self.markdown = '# Usama Aslam\n\n## Education\nBSCS\n\n## Experience\nSoftware development\n'

    def tearDown(self):
        self.temp.cleanup()

    def call(self, path, data=None, query=None):
        return app.handle('POST' if data is not None else 'GET', path, self.headers,
                          json.dumps(data).encode() if data is not None else b'', query=query)

    def login(self):
        result = self.call('/api/login', {'code': 'test-access-code'})
        self.assertEqual(result['statusCode'], 200)
        cookie = result['cookies'][0]
        self.assertIn('HttpOnly', cookie)
        self.assertIn('Secure', cookie)
        self.assertIn('SameSite=Strict', cookie)
        self.headers['cookie'] = cookie.split(';')[0]

    def test_private_endpoints_require_login(self):
        self.assertEqual(self.call('/api/current', query={'type': 'software'})['statusCode'], 401)
        self.assertEqual(self.call('/api/save', {'type': 'software', 'markdown': self.markdown})['statusCode'], 401)
        self.assertEqual(self.call('/api/generate', {'type': 'software'})['statusCode'], 401)

    def test_cross_origin_and_bad_json_rejected(self):
        result = app.handle('POST', '/api/login', {'origin': 'https://evil.example'}, b'{}')
        self.assertEqual(result['statusCode'], 403)
        self.assertEqual(app.handle('POST', '/api/login', self.headers, b'[')['statusCode'], 400)
        self.assertEqual(self.call('/api/login', [])['statusCode'], 400)

    def test_login_rate_limit_and_logout_revocation(self):
        self.login()
        self.assertTrue(json.loads(self.call('/api/session')['body'])['authenticated'])
        self.assertEqual(self.call('/api/logout', {})['statusCode'], 200)
        self.assertFalse(json.loads(self.call('/api/session')['body'])['authenticated'])
        for _ in range(4):
            self.assertEqual(self.call('/api/login', {'code': 'incorrect-code'})['statusCode'], 401)
        self.assertEqual(self.call('/api/login', {'code': 'test-access-code'})['statusCode'], 429)

    def test_versions_are_immutable_and_concurrent_saves_conflict(self):
        self.login()
        def save(kind, base, content):
            return self.call('/api/save', {'type': kind, 'baseId': base, 'markdown': content, 'note': 'test'})
        first = save('software', None, self.markdown)
        self.assertEqual(first['statusCode'], 201)
        first_id = json.loads(first['body'])['id']
        self.assertEqual(save('software', None, self.markdown + 'Other tab')['statusCode'], 409)
        second = save('software', first_id, self.markdown + 'Changed')
        self.assertEqual(second['statusCode'], 201)
        earlier = json.loads(self.call('/api/version', query={'type': 'software', 'id': first_id})['body'])
        self.assertEqual(earlier['markdown'], self.markdown)
        academic = json.loads(self.call('/api/current', query={'type': 'academic'})['body'])
        self.assertIsNone(academic['id'])
        versions = json.loads(self.call('/api/versions', query={'type': 'software'})['body'])['versions']
        self.assertEqual(len(versions), 2)
        self.assertNotIn('markdown', versions[0])

    def test_history_pagination_preserves_all_versions(self):
        self.login()
        base = None
        for number in range(23):
            result = self.call('/api/save', {'type': 'general', 'baseId': base, 'markdown': self.markdown, 'note': str(number)})
            base = json.loads(result['body'])['id']
        first = json.loads(self.call('/api/versions', query={'type': 'general'})['body'])
        second = json.loads(self.call('/api/versions', query={'type': 'general', 'cursor': first['cursor']})['body'])
        all_ids = {item['id'] for item in first['versions'] + second['versions']}
        self.assertEqual(len(all_ids), 23)
        self.assertIsNone(second['cursor'])

    def test_expired_session_and_validation(self):
        self.login()
        app.store().put(app.session_key(self.headers), {'ttl': 1})
        self.assertFalse(json.loads(self.call('/api/session')['body'])['authenticated'])
        self.login()
        self.assertEqual(self.call('/api/save', {'type': 'academic', 'markdown': 'bad'})['statusCode'], 400)
        self.assertEqual(self.call('/api/current', query={'type': '../private'})['statusCode'], 400)

    def test_generation_is_bounded_and_never_auto_saves(self):
        self.login()
        payload = {'model': 'test-model', 'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({'markdown': self.markdown, 'notes': 'Review'})}}]}
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, *args): return json.dumps(payload).encode()
        with patch('app.urlopen', return_value=FakeResponse()) as provider:
            for _ in range(10):
                result = self.call('/api/generate', {'type': 'academic', 'markdown': self.markdown, 'instruction': 'Tailor for study'})
                self.assertEqual(result['statusCode'], 200)
            self.assertEqual(self.call('/api/generate', {'type': 'academic', 'markdown': self.markdown, 'instruction': 'Again'})['statusCode'], 429)
            request = provider.call_args.args[0]
            sent = json.loads(request.data)
            self.assertFalse(sent['enable_thinking'])
            self.assertEqual(sent['max_tokens'], 6000)
        self.assertIsNone(json.loads(self.call('/api/current', query={'type': 'academic'})['body'])['id'])

    def test_invalid_provider_draft_does_not_modify_cv(self):
        self.login()
        class InvalidResponse:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, *args): return b'{"choices": []}'
        with patch('app.urlopen', return_value=InvalidResponse()):
            result = self.call('/api/generate', {'type': 'software', 'markdown': self.markdown, 'instruction': 'Tailor'})
            self.assertEqual(result['statusCode'], 502)
        self.assertIsNone(app.store().get('cv#software', 'current'))

    def test_lambda_origin_guard_and_static_allowlist(self):
        event = {'rawPath': '/', 'headers': {}, 'requestContext': {'http': {'method': 'GET'}}}
        self.assertEqual(app.handler(event, None)['statusCode'], 403)
        app._config['origin_secret'] = 'private-test-origin'
        event['headers']['x-resume-origin'] = 'private-test-origin'
        self.assertEqual(app.handler(event, None)['statusCode'], 200)
        event['rawPath'] = '/.private/runtime.json'
        self.assertEqual(app.handler(event, None)['statusCode'], 404)
        event['rawPath'] = '/api/session'
        self.assertEqual(json.loads(app.handler(event, None)['body']), {'authenticated': False})


if __name__ == '__main__':
    unittest.main()
