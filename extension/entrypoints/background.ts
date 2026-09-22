import type { Analysis, AnalyzeRequest, AnalyzeResponse, InspectRequest, InspectResult, PageLink } from '@/utils/analysis';
import { describeError } from '@/utils/errors';

const API_URL = import.meta.env.WXT_API_URL ?? 'http://127.0.0.1:8787';
const MAX_HOPS = 2;

interface FetchedPage {
  url: string;
  html: string;
  links: PageLink[];
}

type Failure = { error: string };

let offscreenReady: Promise<void> | null = null;

// Chrome n'autorise qu'un seul document offscreen : deux créations simultanées échoueraient.
function ensureOffscreen(): Promise<void> {
  offscreenReady ??= (async () => {
    if (await browser.offscreen.hasDocument()) return;
    await browser.offscreen.createDocument({
      url: browser.runtime.getURL('/offscreen.html'),
      reasons: ['DOM_PARSER'],
      justification: 'Lire le texte et les liens des pages de CGU téléchargées',
    });
  })().catch((error) => {
    offscreenReady = null;
    throw error;
  });
  return offscreenReady;
}

async function prepare(url: string): Promise<FetchedPage | Failure> {
  let html: string;
  try {
    const page = await fetch(url, { credentials: 'include' });
    if (!page.ok) return { error: `${url} a répondu ${page.status}` };
    html = await page.text();
  } catch {
    return { error: `Impossible de télécharger ${url}` };
  }
  await ensureOffscreen();
  const request: InspectRequest = { type: 'inspect', url, html };
  const inspected: InspectResult = await browser.runtime.sendMessage(request);
  return { url, ...inspected };
}

async function prepareAll(urls: string[]): Promise<{ documents: FetchedPage[]; failures: Failure[] }> {
  const results = await Promise.all(urls.map(prepare));
  return {
    documents: results.filter((result): result is FetchedPage => 'html' in result),
    failures: results.filter((result): result is Failure => 'error' in result),
  };
}

async function post(documents: FetchedPage[]): Promise<AnalyzeResponse> {
  try {
    const response = await fetch(`${API_URL}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ documents }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      return { ok: false, error: describeError(response.status, body.detail) };
    }
    return { ok: true, analysis: (await response.json()) as Analysis };
  } catch {
    return { ok: false, error: `Serveur d'analyse injoignable (${API_URL})` };
  }
}

// analyze suit au plus MAX_HOPS fois les liens que Jev désigne quand une page renvoie vers le vrai contrat.
async function analyze(urls: string[]): Promise<AnalyzeResponse> {
  const seen = new Set(urls);
  let { documents, failures } = await prepareAll(urls);
  for (let hop = 0; ; hop++) {
    if (documents.length === 0) return { ok: false, error: failures[0]?.error ?? 'Aucun document à analyser' };
    const response = await post(documents);
    if (!response.ok) return response;
    const next = response.analysis.follow.filter((url) => !seen.has(url));
    if (next.length === 0 || hop === MAX_HOPS) return response;

    next.forEach((url) => seen.add(url));
    const contracts = new Set(response.analysis.documents.filter((doc) => doc.kind === 'contract').map((doc) => doc.url));
    const followed = await prepareAll(next);
    documents = [...documents.filter((doc) => contracts.has(doc.url)), ...followed.documents];
    failures = followed.failures;
  }
}

export default defineBackground(() => {
  browser.runtime.onMessage.addListener((message: AnalyzeRequest) => {
    if (message.type === 'analyze') return analyze(message.urls);
  });
});
