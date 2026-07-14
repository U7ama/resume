import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

export const PORTFOLIO_SCHEMA_VERSION = 1;
export const MAX_PORTFOLIO_BYTES = 256 * 1024;

const SAFE_PROTOCOLS = new Set(['http:', 'https:', 'mailto:', 'tel:']);
const SECTION_NAMES = new Set([
  'profile',
  'contact',
  'experience',
  'skills',
  'education',
  'projects',
  'uses',
  'articles',
  'portfolio sites',
]);

function requireValue(value, context) {
  if (!value || !value.trim()) {
    throw new Error(`${context} is required`);
  }
  return value.trim();
}

function requireSlug(value, context) {
  const slug = requireValue(value, context);
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) {
    throw new Error(`${context} must be a lowercase stable slug`);
  }
  return slug;
}

function assertSafeUrl(value, context) {
  const rawUrl = requireValue(value, context);
  let url;

  try {
    url = new URL(rawUrl);
  } catch {
    throw new Error(`${context} is not a valid absolute URL: ${rawUrl}`);
  }

  if (!SAFE_PROTOCOLS.has(url.protocol.toLowerCase())) {
    throw new Error(`${context} uses an unsupported protocol: ${url.protocol}`);
  }

  return rawUrl;
}

function assertUnique(items, context) {
  const ids = new Set();
  for (const item of items) {
    if (ids.has(item.id)) {
      throw new Error(`Duplicate ${context} id: ${item.id}`);
    }
    ids.add(item.id);
  }
}

function parseRecord(line) {
  return line
    .slice(2)
    .split('|')
    .map((part) => part.trim());
}

export function parsePortfolioMarkdown(markdown) {
  if (typeof markdown !== 'string') {
    throw new TypeError('Portfolio content must be a string');
  }

  if (Buffer.byteLength(markdown, 'utf8') > MAX_PORTFOLIO_BYTES) {
    throw new Error(`Portfolio content exceeds ${MAX_PORTFOLIO_BYTES} bytes`);
  }

  const schemaMatch = markdown.match(/<!--\s*portfolio-schema:\s*(\d+)\s*-->/i);
  if (!schemaMatch) {
    throw new Error('Missing portfolio schema marker');
  }

  const schemaVersion = Number(schemaMatch[1]);
  if (schemaVersion !== PORTFOLIO_SCHEMA_VERSION) {
    throw new Error(`Unsupported portfolio schema version: ${schemaVersion}`);
  }

  const data = {
    schemaVersion,
    profile: {
      name: '',
      headline: '',
      summary: [],
      disciplines: [],
    },
    contacts: [],
    experience: [],
    skills: [],
    education: [],
    projects: [],
    uses: [],
    articles: [],
    sites: [],
  };

  let section = '';
  let currentEntry = null;
  const seenSections = new Set();
  const lines = markdown.replace(/\r\n?/g, '\n').split('\n');

  for (let index = 0; index < lines.length; index += 1) {
    const trimmed = lines[index].trim();
    const lineNumber = index + 1;

    if (!trimmed || /^<!--\s*portfolio-schema:/i.test(trimmed)) {
      continue;
    }

    if (/<\/?(?:script|iframe|object|embed|style|link|meta)\b/i.test(trimmed)) {
      throw new Error(`Raw active HTML is not allowed at line ${lineNumber}`);
    }

    if (trimmed.startsWith('# ') && !trimmed.startsWith('## ')) {
      data.profile.name = requireValue(trimmed.slice(2), `Name at line ${lineNumber}`);
      continue;
    }

    if (trimmed.startsWith('> ')) {
      data.profile.headline = requireValue(
        trimmed.slice(2),
        `Headline at line ${lineNumber}`,
      );
      continue;
    }

    if (trimmed.startsWith('## ')) {
      section = trimmed.slice(3).trim().toLowerCase();
      if (!SECTION_NAMES.has(section)) {
        throw new Error(`Unknown section at line ${lineNumber}: ${section}`);
      }
      seenSections.add(section);
      currentEntry = null;
      continue;
    }

    if (trimmed.startsWith('### ')) {
      const parts = trimmed
        .slice(4)
        .split('|')
        .map((part) => part.trim());

      if (section === 'experience') {
        if (parts.length !== 5) {
          throw new Error(`Experience heading needs 5 fields at line ${lineNumber}`);
        }
        currentEntry = {
          id: requireValue(parts[0], 'Experience id'),
          role: requireValue(parts[1], 'Experience role'),
          organization: requireValue(parts[2], 'Experience organization'),
          location: requireValue(parts[3], 'Experience location'),
          period: requireValue(parts[4], 'Experience period'),
          website: '',
          summary: '',
          details: [],
        };
        data.experience.push(currentEntry);
      } else if (section === 'skills' || section === 'uses') {
        if (parts.length !== 2) {
          throw new Error(`${section} heading needs 2 fields at line ${lineNumber}`);
        }
        currentEntry = {
          id: requireValue(parts[0], `${section} id`),
          label: requireValue(parts[1], `${section} label`),
          items: [],
        };
        data[section].push(currentEntry);
      } else if (section === 'education') {
        if (parts.length !== 5) {
          throw new Error(`Education heading needs 5 fields at line ${lineNumber}`);
        }
        currentEntry = {
          id: requireValue(parts[0], 'Education id'),
          qualification: requireValue(parts[1], 'Education qualification'),
          institution: requireValue(parts[2], 'Education institution'),
          location: requireValue(parts[3], 'Education location'),
          period: requireValue(parts[4], 'Education period'),
          details: [],
          links: [],
        };
        data.education.push(currentEntry);
      } else if (section === 'projects') {
        if (parts.length !== 3) {
          throw new Error(`Project heading needs 3 fields at line ${lineNumber}`);
        }
        currentEntry = {
          id: requireSlug(parts[0], 'Project id'),
          title: requireValue(parts[1], 'Project title'),
          category: requireValue(parts[2], 'Project category'),
          featuredOrder: null,
          summary: '',
          details: [],
          technologies: [],
          links: [],
          videos: [],
        };
        data.projects.push(currentEntry);
      } else if (section === 'articles') {
        if (parts.length !== 2) {
          throw new Error(`Article heading needs 2 fields at line ${lineNumber}`);
        }
        currentEntry = {
          id: requireValue(parts[0], 'Article id'),
          title: requireValue(parts[1], 'Article title'),
          date: '',
          summary: '',
          links: [],
        };
        data.articles.push(currentEntry);
      } else {
        throw new Error(`Entries are not supported in ${section || 'the document root'} at line ${lineNumber}`);
      }
      continue;
    }

    if (!trimmed.startsWith('- ')) {
      throw new Error(`Unsupported content at line ${lineNumber}: ${trimmed}`);
    }

    if (!section) {
      throw new Error(`Record appears before a section at line ${lineNumber}`);
    }

    const parts = parseRecord(trimmed);
    const field = requireValue(parts[0], `Field at line ${lineNumber}`).toLowerCase();

    if (section === 'profile') {
      if (parts.length !== 2 || (field !== 'summary' && field !== 'discipline')) {
        throw new Error(`Invalid profile record at line ${lineNumber}`);
      }
      const value = requireValue(parts[1], `Profile ${field}`);
      data.profile[field === 'summary' ? 'summary' : 'disciplines'].push(value);
    } else if (section === 'contact') {
      if (parts.length !== 3) {
        throw new Error(`Contact record needs 3 fields at line ${lineNumber}`);
      }
      data.contacts.push({
        id: field,
        label: requireValue(parts[1], 'Contact label'),
        url: assertSafeUrl(parts[2], 'Contact URL'),
      });
    } else if (section === 'experience') {
      if (!currentEntry) throw new Error(`Experience record has no heading at line ${lineNumber}`);
      if (field === 'website' && parts.length === 2) {
        currentEntry.website = assertSafeUrl(parts[1], 'Experience website');
      } else if (field === 'summary' && parts.length === 2) {
        currentEntry.summary = requireValue(parts[1], 'Experience summary');
      } else if (field === 'detail' && parts.length === 2) {
        currentEntry.details.push(requireValue(parts[1], 'Experience detail'));
      } else {
        throw new Error(`Invalid experience record at line ${lineNumber}`);
      }
    } else if (section === 'skills' || section === 'uses') {
      if (!currentEntry || field !== 'item' || parts.length !== 2) {
        throw new Error(`Invalid ${section} record at line ${lineNumber}`);
      }
      currentEntry.items.push(requireValue(parts[1], `${section} item`));
    } else if (section === 'education') {
      if (!currentEntry) throw new Error(`Education record has no heading at line ${lineNumber}`);
      if (field === 'detail' && parts.length === 2) {
        currentEntry.details.push(requireValue(parts[1], 'Education detail'));
      } else if (field === 'link' && parts.length === 3) {
        currentEntry.links.push({
          label: requireValue(parts[1], 'Education link label'),
          url: assertSafeUrl(parts[2], 'Education link URL'),
        });
      } else {
        throw new Error(`Invalid education record at line ${lineNumber}`);
      }
    } else if (section === 'projects') {
      if (!currentEntry) throw new Error(`Project record has no heading at line ${lineNumber}`);
      if (field === 'featured' && parts.length === 2) {
        const order = Number(parts[1]);
        if (!Number.isInteger(order) || order < 1 || order > 3) {
          throw new Error(`Project featured order must be 1, 2, or 3 at line ${lineNumber}`);
        }
        currentEntry.featuredOrder = order;
      } else if (field === 'summary' && parts.length === 2) {
        currentEntry.summary = requireValue(parts[1], 'Project summary');
      } else if (field === 'detail' && parts.length === 2) {
        currentEntry.details.push(requireValue(parts[1], 'Project detail'));
      } else if (field === 'technologies' && parts.length === 2) {
        currentEntry.technologies = parts[1]
          .split(',')
          .map((technology) => technology.trim())
          .filter(Boolean);
      } else if (field === 'link' && parts.length === 3) {
        currentEntry.links.push({
          label: requireValue(parts[1], 'Project link label'),
          url: assertSafeUrl(parts[2], 'Project link URL'),
        });
      } else if (field === 'video' && parts.length === 4) {
        const provider = requireValue(parts[1], 'Video provider').toLowerCase();
        const id = requireValue(parts[2], 'Video id');
        if (provider !== 'youtube' || !/^[\w-]{6,32}$/.test(id)) {
          throw new Error(`Unsupported project video at line ${lineNumber}`);
        }
        currentEntry.videos.push({
          provider,
          id,
          caption: requireValue(parts[3], 'Video caption'),
        });
      } else {
        throw new Error(`Invalid project record at line ${lineNumber}`);
      }
    } else if (section === 'articles') {
      if (!currentEntry) throw new Error(`Article record has no heading at line ${lineNumber}`);
      if (field === 'date' && parts.length === 2 && /^\d{4}-\d{2}-\d{2}$/.test(parts[1])) {
        currentEntry.date = parts[1];
      } else if (field === 'summary' && parts.length === 2) {
        currentEntry.summary = requireValue(parts[1], 'Article summary');
      } else if (field === 'link' && parts.length === 3) {
        currentEntry.links.push({
          label: requireValue(parts[1], 'Article link label'),
          url: assertSafeUrl(parts[2], 'Article link URL'),
        });
      } else {
        throw new Error(`Invalid article record at line ${lineNumber}`);
      }
    } else if (section === 'portfolio sites') {
      if (parts.length !== 3) {
        throw new Error(`Portfolio site record needs 3 fields at line ${lineNumber}`);
      }
      data.sites.push({
        id: field,
        label: requireValue(parts[1], 'Portfolio site label'),
        url: assertSafeUrl(parts[2], 'Portfolio site URL'),
      });
    }
  }

  requireValue(data.profile.name, 'Profile name');
  requireValue(data.profile.headline, 'Profile headline');
  for (const requiredSection of SECTION_NAMES) {
    if (!seenSections.has(requiredSection)) {
      throw new Error(`Missing required section: ${requiredSection}`);
    }
  }
  if (data.profile.summary.length === 0) throw new Error('At least one profile summary is required');
  if (data.profile.disciplines.length === 0) throw new Error('At least one profile discipline is required');
  if (data.contacts.length === 0) throw new Error('At least one contact is required');
  if (data.experience.length === 0) throw new Error('At least one experience entry is required');
  if (data.skills.length === 0) throw new Error('At least one skill group is required');
  if (data.education.length === 0) throw new Error('At least one education entry is required');
  if (data.projects.length === 0) throw new Error('At least one project is required');
  if (data.uses.length === 0) throw new Error('At least one uses group is required');
  if (data.articles.length === 0) throw new Error('At least one article is required');
  if (data.sites.length === 0) throw new Error('At least one portfolio site is required');

  assertUnique(data.contacts, 'contact');
  assertUnique(data.experience, 'experience');
  assertUnique(data.skills, 'skill group');
  assertUnique(data.education, 'education');
  assertUnique(data.projects, 'project');
  assertUnique(data.uses, 'uses group');
  assertUnique(data.articles, 'article');
  assertUnique(data.sites, 'portfolio site');

  const featuredOrders = data.projects
    .map((project) => project.featuredOrder)
    .filter((order) => order !== null);
  if (featuredOrders.length !== 3 || new Set(featuredOrders).size !== 3) {
    throw new Error('Exactly three projects with unique featured orders are required');
  }

  for (const entry of data.experience) {
    requireValue(entry.summary, `Experience summary for ${entry.id}`);
  }
  for (const group of [...data.skills, ...data.uses]) {
    if (group.items.length === 0) {
      throw new Error(`At least one item is required for ${group.id}`);
    }
  }
  for (const project of data.projects) {
    requireValue(project.summary, `Project summary for ${project.id}`);
  }
  for (const article of data.articles) {
    requireValue(article.date, `Article date for ${article.id}`);
    requireValue(article.summary, `Article summary for ${article.id}`);
    if (article.links.length === 0) throw new Error(`Article link required for ${article.id}`);
  }

  return data;
}

async function runCli() {
  const filename = process.argv[2] || 'portfolio.md';
  const markdown = await readFile(filename, 'utf8');
  const data = parsePortfolioMarkdown(markdown);
  process.stdout.write(
    `Validated portfolio schema ${data.schemaVersion}: ${data.experience.length} roles, ${data.projects.length} projects, ${data.articles.length} articles\n`,
  );
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runCli().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
