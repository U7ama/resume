import { readFile } from 'node:fs/promises';
import { parsePortfolioMarkdown } from './portfolio-content.mjs';

const REQUIRED_CV_HEADINGS = [
  '# Usama Aslam',
  '## Contact',
  '## Experience',
  '## Technical Skills',
  '## Education',
  '## Selected Projects',
];
const FUTURE_FEATURE_MARKER = 'F* Future feature (not implemented yet) —';

const [cvMarkdown, portfolioMarkdown, resumePage] = await Promise.all([
  readFile('resume.md', 'utf8'),
  readFile('portfolio.md', 'utf8'),
  readFile('index.html', 'utf8'),
]);

for (const heading of REQUIRED_CV_HEADINGS) {
  if (!cvMarkdown.includes(heading)) {
    throw new Error(`resume.md is missing required heading: ${heading}`);
  }
}

if (/portfolio-schema\s*:/i.test(cvMarkdown)) {
  throw new Error('resume.md must remain independent of the portfolio content schema.');
}

if (cvMarkdown.includes('F*')) {
  throw new Error('resume.md must not contain future-feature markers.');
}

if (!resumePage.includes('resume.md') || resumePage.includes('portfolio.md')) {
  throw new Error('The resume page must load resume.md only.');
}

const cvUrls = new Set([
  ...Array.from(cvMarkdown.matchAll(/\[[^\]]+\]\(([^)]+)\)/g), (match) => match[1]),
  ...Array.from(
    cvMarkdown.matchAll(/^-\s+[^|\n]+\|\s*([^|\s]+)\s*\|/gm),
    (match) => match[1],
  ),
]);
const allowedProtocols = new Set(['http:', 'https:', 'mailto:', 'tel:']);

for (const url of cvUrls) {
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    throw new Error(`resume.md contains an invalid absolute URL: ${url}`);
  }

  if (!allowedProtocols.has(parsed.protocol)) {
    throw new Error(`resume.md contains an unsupported URL protocol: ${url}`);
  }
  if (!resumePage.includes(`href="${url}"`)) {
    throw new Error(`The static resume fallback is missing a resume.md link: ${url}`);
  }
}

const portfolio = parsePortfolioMarkdown(portfolioMarkdown);
const futureDetails = portfolio.projects.flatMap((project) =>
  project.details.filter((detail) => detail.startsWith('F*')),
);
const rawFutureLines = portfolioMarkdown
  .split(/\r?\n/)
  .filter((line) => line.includes('F*'));

if (futureDetails.length !== rawFutureLines.length) {
  throw new Error('Future-feature markers are allowed only in portfolio project details.');
}

if (rawFutureLines.some((line) => !line.includes(FUTURE_FEATURE_MARKER))) {
  throw new Error(`Every portfolio future-feature line must include: ${FUTURE_FEATURE_MARKER}`);
}

for (const detail of futureDetails) {
  if (!detail.startsWith(FUTURE_FEATURE_MARKER)) {
    throw new Error(`Future feature must start with: ${FUTURE_FEATURE_MARKER}`);
  }
}

for (const project of portfolio.projects) {
  if (project.technologies.some((technology) => technology.includes('F*'))) {
    throw new Error(`Project technologies must not contain future markers: ${project.id}`);
  }
}

for (const entry of portfolio.experience) {
  if ([entry.summary, ...entry.details].some((detail) => detail.includes('F*'))) {
    throw new Error(`Employment achievements must not contain future markers: ${entry.id}`);
  }
}

console.log(
  `Content validation passed: CV is independent with ${cvUrls.size} links; portfolio has ${portfolio.projects.length} projects and ${futureDetails.length} explicit future features.`,
);
