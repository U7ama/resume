import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

test('print waits for both bundled font weights before opening the dialog', async () => {
  const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  const source = html.slice(html.indexOf('    function autofitPrint()'), html.indexOf('    let profileImageVisible'));
  const loads = [], releases = [], events = {};
  const style = {};
  let click, printed = 0;
  const button = {disabled:false, addEventListener(name, handler) { click = handler; }};
  vm.runInNewContext(source, {
    document: {
      documentElement: {style},
      getElementById: () => button,
      fonts: {
        load(font) { loads.push(font); return new Promise(resolve => releases.push(resolve)); },
        ready: Promise.resolve(),
      },
    },
    window: {addEventListener(name, handler) { events[name] = handler; }, print() { printed++; }},
    requestAnimationFrame: callback => callback(),
  });
  assert.equal(loads.length, 2);
  const printing = click.call(button);
  assert.equal(button.disabled, true);
  assert.equal(printed, 0);
  releases[0]([]);
  await new Promise(setImmediate);
  assert.equal(printed, 0);
  releases[1]([]);
  await printing;
  assert.equal(printed, 1);
  assert.equal(button.disabled, false);
  assert.equal(style.fontSize, '10.75pt');
  events.afterprint();
  assert.equal(style.fontSize, '');
});

test('compact spacing measures print height and restores temporary media and width', () => {
  const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  const source = html.slice(html.indexOf('    function autofitPrint()'), html.indexOf('    // Preload the embedded font'));
  const classes = new Set();
  let height = 900;
  const media = {mediaText: 'print'};
  const style = {width: '', setProperty(name, value) { this[name] = value; },
    getPropertyValue(name) { return this[name]; }, getPropertyPriority() { return ''; },
    removeProperty(name) { delete this[name]; }};
  const context = {
    document: {documentElement: {style}, styleSheets: [{cssRules: [{media}]}], getElementById: () => ({
      classList: {add: value => classes.add(value), remove: value => classes.delete(value)},
      getBoundingClientRect: () => {
        assert.equal(media.mediaText, 'all');
        assert.equal(style.width, '184.6mm');
        return {height};
      },
    })},
    window: {addEventListener() {}},
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  context.autofitPrint();
  assert.equal(classes.has('print-compact'), false);
  height = 1100;
  context.autofitPrint();
  assert.equal(classes.has('print-compact'), true);
  assert.equal(style.fontSize, '10.75pt');
  assert.equal(media.mediaText, 'print');
  assert.equal(style.width, undefined);
  height = 900;
  context.autofitPrint();
  assert.equal(classes.has('print-compact'), false);
  height = 1100;
  context.autofitPrint();
  context.resetPrintStyle();
  assert.equal(classes.size, 0);
  assert.equal(style.fontSize, '');
});
