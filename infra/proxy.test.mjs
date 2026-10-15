import assert from 'node:assert/strict';
import {afterEach, beforeEach, test} from 'node:test';
import proxy from './proxy.mjs';

const originalFetch = globalThis.fetch;
const originalCaches = globalThis.caches;
const env = {AWS_ORIGIN:'https://example.lambda-url.us-east-1.on.aws/', AWS_ORIGIN_SECRET:'test-origin', ASSET_VERSION:'test-release'};
let requests, cacheWrites, cached, tasks;
const ctx = {waitUntil: task => tasks.push(task)};
beforeEach(() => {
  requests = []; cacheWrites = []; tasks = []; cached = null;
  globalThis.caches = {default: {
    match: async () => cached,
    put: async (key, response) => {cacheWrites.push(key.url); cached = response;},
  }};
  globalThis.fetch = async (url, options) => {
    requests.push({url:String(url), options});
    return new Response('response', {headers:{'cache-control':'public, max-age=300'}});
  };
});
afterEach(() => {globalThis.fetch = originalFetch; globalThis.caches = originalCaches;});

test('private API forwards authentication and origin but is never cached', async () => {
  const result = await proxy.fetch(new Request('https://resume.usamaaslam.site/api/save', {
    method:'POST', body:'{}', headers:{cookie:'owner-session', origin:'https://resume.usamaaslam.site',
      authorization:'untrusted', 'x-resume-origin':'forged', 'cf-connecting-ip':'192.0.2.1'},
  }), env, ctx);
  assert.equal(result.headers.get('cache-control'), 'no-store');
  assert.equal(cacheWrites.length, 0);
  assert.equal(requests[0].options.headers.get('cookie'), 'owner-session');
  assert.equal(requests[0].options.headers.get('x-resume-origin'), 'test-origin');
  assert.equal(requests[0].options.headers.get('x-resume-client-ip'), '192.0.2.1');
  assert.equal(requests[0].options.headers.get('authorization'), null);
});

test('public assets use a release-specific cache', async () => {
  await proxy.fetch(new Request('https://resume.usamaaslam.site/studio.js'), env, ctx);
  await Promise.all(tasks);
  assert.equal(cacheWrites[0], 'https://resume.usamaaslam.site/studio.js?release=test-release');
  await proxy.fetch(new Request('https://resume.usamaaslam.site/studio.js'), env, ctx);
  assert.equal(requests.length, 1);
});

test('unknown files and hosts never reach AWS', async () => {
  assert.equal((await proxy.fetch(new Request('https://resume.usamaaslam.site/.private/runtime.json'), env, ctx)).status, 404);
  assert.equal((await proxy.fetch(new Request('https://unexpected.example/'), env, ctx)).status, 404);
  assert.equal(requests.length, 0);
});
