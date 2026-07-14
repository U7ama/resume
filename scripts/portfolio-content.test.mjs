import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import {
  MAX_PORTFOLIO_BYTES,
  parsePortfolioMarkdown,
} from './portfolio-content.mjs';

const validMarkdown = await readFile('portfolio.md', 'utf8');

test('parses the published portfolio contract', () => {
  const portfolio = parsePortfolioMarkdown(validMarkdown);
  assert.equal(portfolio.schemaVersion, 1);
  assert.equal(portfolio.profile.name, 'Usama Aslam');
  assert.deepEqual(
    portfolio.projects
      .filter((project) => project.featuredOrder !== null)
      .map((project) => project.featuredOrder),
    [1, 2, 3],
  );
});

test('rejects unsupported schema versions', () => {
  assert.throws(
    () => parsePortfolioMarkdown(validMarkdown.replace('portfolio-schema: 1', 'portfolio-schema: 2')),
    /Unsupported portfolio schema version/,
  );
});

test('rejects duplicate stable ids', () => {
  assert.throws(
    () => parsePortfolioMarkdown(validMarkdown.replace('### cool-potato |', '### alignav-monitoring |')),
    /Duplicate project id/,
  );
});

test('rejects invalid project slugs', () => {
  assert.throws(
    () => parsePortfolioMarkdown(validMarkdown.replace('### cool-potato |', '### Cool Potato |')),
    /lowercase stable slug/,
  );
});

test('rejects unsafe links', () => {
  assert.throws(
    () => parsePortfolioMarkdown(validMarkdown.replace('mailto:u7amaaslam@gmail.com', 'javascript:alert(1)')),
    /unsupported protocol/,
  );
});

test('rejects malformed records', () => {
  assert.throws(
    () => parsePortfolioMarkdown(validMarkdown.replace('- featured | 1', '- featured | first')),
    /featured order/,
  );
});

test('rejects missing contract sections and fields', () => {
  assert.throws(
    () => parsePortfolioMarkdown(validMarkdown.replace('## Uses', '## Unknown Uses')),
    /Unknown section|Missing required section/,
  );
  assert.throws(
    () => parsePortfolioMarkdown(validMarkdown.replace(/^- discipline \| .+\n/gm, '')),
    /profile discipline/,
  );
});

test('rejects oversized content', () => {
  assert.throws(
    () => parsePortfolioMarkdown(`${validMarkdown}\n${'x'.repeat(MAX_PORTFOLIO_BYTES)}`),
    /exceeds/,
  );
});
