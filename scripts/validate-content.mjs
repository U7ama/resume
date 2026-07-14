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

const [cvMarkdown, portfolioMarkdown, resumePage] = await Promise.all([
  readFile('cv.md', 'utf8'),
  readFile('portfolio.md', 'utf8'),
  readFile('index.html', 'utf8'),
]);

for (const heading of REQUIRED_CV_HEADINGS) {
  if (!cvMarkdown.includes(heading)) {
    throw new Error(`cv.md is missing required heading: ${heading}`);
  }
}

if (/portfolio-schema\s*:/i.test(cvMarkdown)) {
  throw new Error('cv.md must remain independent of the portfolio content schema.');
}

if (!resumePage.includes('cv.md') || resumePage.includes('portfolio.md')) {
  throw new Error('The resume page must load cv.md only.');
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
    throw new Error(`cv.md contains an invalid absolute URL: ${url}`);
  }

  if (!allowedProtocols.has(parsed.protocol)) {
    throw new Error(`cv.md contains an unsupported URL protocol: ${url}`);
  }
  if (!resumePage.includes(`href="${url}"`)) {
    throw new Error(`The static resume fallback is missing a cv.md link: ${url}`);
  }
}

const portfolio = parsePortfolioMarkdown(portfolioMarkdown);
console.log(
  `Content validation passed: CV is independent with ${cvUrls.size} links; portfolio has ${portfolio.projects.length} projects.`,
);
