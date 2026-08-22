import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import {
  MAX_PORTFOLIO_BYTES,
  parsePortfolioMarkdown,
} from './portfolio-content.mjs';

const validMarkdown = await readFile('portfolio.md', 'utf8');
const resumeMarkdown = await readFile('resume.md', 'utf8');
const FUTURE_FEATURE_MARKER = 'F* Future feature (not implemented yet) —';

test('parses the published portfolio contract', () => {
  const portfolio = parsePortfolioMarkdown(validMarkdown);
  assert.equal(portfolio.schemaVersion, 1);
  assert.equal(portfolio.profile.name, 'Usama Aslam');
  assert.deepEqual(
    portfolio.projects
      .filter((project) => project.featuredOrder !== null)
      .sort((a, b) => a.featuredOrder - b.featuredOrder)
      .map((project) => project.id),
    ['deviceops-ai-copilot', 'alignav-monitoring', 'cool-potato'],
  );
});

test('keeps future features explicit and out of the resume', () => {
  const portfolio = parsePortfolioMarkdown(validMarkdown);
  const futureDetails = portfolio.projects.flatMap((project) =>
    project.details.filter((detail) => detail.startsWith('F*')),
  );
  const rawFutureLines = validMarkdown.split(/\r?\n/).filter((line) => line.includes('F*'));

  assert.ok(futureDetails.length >= 1);
  assert.equal(futureDetails.length, rawFutureLines.length);
  assert.ok(rawFutureLines.every((line) => line.includes(FUTURE_FEATURE_MARKER)));
  assert.ok(futureDetails.every((detail) => detail.startsWith(FUTURE_FEATURE_MARKER)));
  assert.ok(
    portfolio.projects.every((project) =>
      project.technologies.every((technology) => !technology.includes('F*')),
    ),
  );
  assert.ok(
    portfolio.experience.every((entry) =>
      [entry.summary, ...entry.details].every((detail) => !detail.includes('F*')),
    ),
  );
  assert.equal(resumeMarkdown.includes('F*'), false);
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
