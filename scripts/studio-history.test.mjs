import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

test('cloud history never prompts or replaces a browser draft on automatic refresh', async () => {
  const elements = new Map();
  const requests = [];
  let replacements = 0;
  let prompts = 0;
  const element = id => {
    if (!elements.has(id)) elements.set(id, {
      value: '', hidden: false, handlers: {},
      addEventListener(event, handler) { this.handlers[event] = handler; },
      querySelectorAll() { return []; },
      prepend() {}, append() {}, replaceChildren() {},
    });
    return elements.get(id);
  };
  const context = {
    document: {
      body: { dataset: {} },
      getElementById: element,
      createElement: () => element(Symbol()),
    },
    window: { resumeStudio: {
      getMarkdown: () => 'Unsaved browser draft',
      setMarkdown: () => { replacements++; },
      openEditor() {}, async load() {},
    } },
    confirm: () => { prompts++; return true; },
    async fetch(url, options) {
      requests.push({ url, body: options.body && JSON.parse(options.body) });
      const data = url === '/api/session' ? { authenticated: true }
        : url.startsWith('/api/current?') ? { id: 'latest-cloud-revision', markdown: 'Different cloud draft' }
          : url.startsWith('/api/versions?') ? { versions: [], cursor: null }
            : url === '/api/save' ? { id: 'new-revision' } : {};
      return { ok: true, status: 200, async json() { return data; } };
    },
  };
  const settle = async () => { for (let i = 0; i < 10; i++) await new Promise(setImmediate); };
  vm.runInNewContext(readFileSync(new URL('../studio.js', import.meta.url), 'utf8'), context);
  await settle();
  assert.ok(requests.some(r => r.url === '/api/current?type=software'));
  element('resumeType').value = 'academic';
  await element('resumeType').handlers.change();
  await element('refreshVersions').handlers.click();
  element('accessCode').value = 'test-code';
  element('studioLogin').handlers.submit({ preventDefault() {} });
  await settle();
  assert.ok(requests.some(r => r.url === '/api/current?type=academic'));
  assert.equal(prompts, 0);
  assert.equal(replacements, 0);
  await element('saveVersion').handlers.click();
  const saved = requests.find(r => r.url === '/api/save').body;
  assert.equal(saved.baseId, 'latest-cloud-revision');
  assert.equal(saved.markdown, 'Unsaved browser draft');
  assert.equal(saved.type, 'academic');
});
