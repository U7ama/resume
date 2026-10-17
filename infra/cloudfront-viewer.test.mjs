import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import test from 'node:test';
const context = {};
vm.createContext(context);
vm.runInContext(readFileSync(new URL('./cloudfront-viewer.js', import.meta.url), 'utf8'), context);
const event = (uri, method = 'GET', headers = {}) => ({request: {uri, method, headers}, viewer: {ip: '203.0.113.4'}});
test('edge overwrites client identity and strips legacy origin credentials', () => {
  const result = context.handler(event('/api/login', 'POST', {'x-resume-client-ip': {value: 'spoofed'}, 'x-resume-origin': {value: 'spoofed'}}));
  assert.equal(result.headers['x-resume-client-ip'].value, '203.0.113.4');
  assert.equal(result.headers['x-resume-origin'], undefined);
});
test('edge preserves the public allowlist and request limits', () => {
  assert.equal(context.handler(event('/.private/runtime.json')).statusCode, 404);
  assert.equal(context.handler(event('/api/login', 'DELETE')).statusCode, 405);
  assert.equal(context.handler(event('/api/save', 'POST', {'content-length': {value: '40001'}})).statusCode, 413);
  assert.equal(context.handler(event('/studio.css')).uri, '/studio.css');
});
