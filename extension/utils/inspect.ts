import type { InspectRequest, InspectResult, PageLink } from './analysis';
import { withoutHash } from './detect';

const MAX_LINKS = 254;

function* htmlStrings(value: unknown): Generator<string> {
  if (typeof value === 'string') {
    if (/<a\s|<p[\s>]/i.test(value)) yield value;
  } else if (value && typeof value === 'object') {
    for (const child of Object.values(value)) yield* htmlStrings(child);
  }
}

// Les sites Vue ou React rangent souvent le texte en JSON dans un attribut, que leur JavaScript affiche au chargement.
function embeddedHtml(doc: Document): string[] {
  const found: string[] = [];
  for (const element of doc.querySelectorAll('*')) {
    for (const { value } of element.attributes) {
      if (!/^[[{]/.test(value)) continue;
      try {
        found.push(...htmlStrings(JSON.parse(value)));
      } catch {
        continue;
      }
    }
  }
  return found;
}

function pageLinks(doc: Document, url: string): PageLink[] {
  const byHref = new Map<string, PageLink>();
  for (const anchor of doc.querySelectorAll<HTMLAnchorElement>('a[href]')) {
    const text = (anchor.textContent ?? '').replace(/\s+/g, ' ').trim();
    if (!text || !anchor.href.startsWith('http')) continue;
    const href = withoutHash(anchor.href);
    if (href !== withoutHash(url) && !byHref.has(href)) byHref.set(href, { text, href });
  }
  return [...byHref.values()].slice(0, MAX_LINKS);
}

export function inspect({ url, html }: InspectRequest): InspectResult {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  // Sans <base>, les liens relatifs d'un document parsé se résoudraient contre l'adresse de cette page d'extension.
  const base = doc.createElement('base');
  base.href = url;
  doc.head.prepend(base);
  doc.querySelectorAll('script, style, noscript, template').forEach((node) => node.remove());
  for (const fragment of embeddedHtml(doc)) {
    const container = doc.createElement('div');
    container.innerHTML = fragment;
    doc.body.append(container);
  }
  return { html: doc.documentElement.outerHTML, links: pageLinks(doc, url) };
}
