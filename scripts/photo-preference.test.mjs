import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');

function sourceBetween(start, end) {
  const from = html.indexOf(start);
  const to = html.indexOf(end, from);
  assert.ok(from >= 0 && to > from, `Controller source exists: ${start}`);
  return html.slice(from, to);
}

function controller(markdown) {
  const stored = new Map();
  const rendered = [];
  const handlers = {};
  const context = vm.createContext({
    markdownEditor: {value: markdown},
    STORAGE_KEY: 'resume_md_draft_general',
    localStorage: {setItem: (key, value) => stored.set(key, value)},
    parseCV: text => ({markdown: text}),
    renderCV: cv => rendered.push(cv.markdown),
    updateEditorStats() {},
    console: {warn(error) { throw new Error(`Unexpected render failure: ${error}`); }},
    document: {getElementById: () => ({addEventListener: (event, handler) => { handlers[event] = handler; }})},
    profileImageVisible: true,
  });
  vm.runInContext(sourceBetween('    function applyMarkdownLive(', '    function setEditorOpen('), context);
  vm.runInContext(sourceBetween('    function setProfileImagePreference(', '    const togglePhotoButton'), context);
  vm.runInContext(sourceBetween('    const togglePhotoButton', '    /* ── CV Markdown Loader'), context);
  return {
    set: visible => context.setProfileImagePreference(visible),
    click: () => handlers.click(),
    text: () => context.markdownEditor.value,
    stored,
    rendered,
  };
}

const content = '# Usama Aslam\n\n> Client Communication\n\nSummary stays unchanged.\n\n';
const rest = '\n## Contact\n\n- github | https://github.com/U7ama | github.com/U7ama\n\n## Experience\n\n### Engineer | Example | 2022 - 2026\n\n- Discussed client feedback.\n';
const display = '## Display Options\n\n- show-profile-image | true\n- profile-image | Usama DP headshot.jpeg\n';

test('photo toggle updates an existing option without changing CV text, photo path, or links', () => {
  const original = content + display + rest;
  const app = controller(original);
  app.set(false);
  assert.equal(app.text(), original.replace('show-profile-image | true', 'show-profile-image | false'));
  app.set(true);
  assert.equal(app.text(), original);
});

test('photo setting is added to an existing Display Options section once', () => {
  const original = content + '## Display Options\n\n- profile-image | Usama DP headshot.jpeg\n' + rest;
  const app = controller(original);
  app.set(false);
  app.set(true);
  app.set(false);
  assert.equal((app.text().match(/^## Display Options$/gm) || []).length, 1);
  assert.equal((app.text().match(/^- show-profile-image\s*\|/gm) || []).length, 1);
  assert.match(app.text(), /## Display Options\n(?:(?!\n## ).)*- show-profile-image\s*\| false/s);
  assert.match(app.text(), /- profile-image \| Usama DP headshot\.jpeg/);
  assert.ok(app.text().startsWith(content));
  assert.ok(app.text().includes(rest));
});

test('CV without display options gains a section without overwriting its content', () => {
  const original = content + rest;
  const app = controller(original);
  app.set(false);
  assert.match(app.text(), /^## Display Options$/m);
  assert.match(app.text(), /^- show-profile-image\s*\| false$/m);
  assert.ok(app.text().includes(content));
  assert.ok(app.text().includes(rest));
  app.set(true);
  assert.equal((app.text().match(/^- show-profile-image\s*\|/gm) || []).length, 1);
  assert.match(app.text(), /^- show-profile-image\s*\| true$/m);
});

test('photo toolbar persists the rendered preference to the active browser draft', () => {
  const original = content + display + rest;
  const app = controller(original);
  app.click();
  assert.match(app.text(), /^- show-profile-image\s*\| false$/m);
  assert.equal(app.stored.get('resume_md_draft_general'), app.text());
  assert.equal(app.rendered.at(-1), app.text());
});
