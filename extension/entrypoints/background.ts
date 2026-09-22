import type { AnalyzeRequest, AnalyzeResponse } from '@/utils/analysis';
import { describeError } from '@/utils/errors';

const API_URL = import.meta.env.WXT_API_URL ?? 'http://127.0.0.1:8787';

async function download(url: string): Promise<{ url: string; html: string } | { error: string }> {
  try {
    const page = await fetch(url, { credentials: 'include' });
    if (!page.ok) return { error: `${url} a répondu ${page.status}` };
    return { url, html: await page.text() };
  } catch {
    return { error: `Impossible de télécharger ${url}` };
  }
}

// analyze échoue seulement si aucun des documents n'a pu être téléchargé.
async function analyze(urls: string[]): Promise<AnalyzeResponse> {
  const pages = await Promise.all(urls.map(download));
  const documents = pages.filter((page) => 'html' in page);
  if (documents.length === 0) {
    const failure = pages.find((page) => 'error' in page);
    return { ok: false, error: failure && 'error' in failure ? failure.error : 'Aucun document à analyser' };
  }

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
    return { ok: true, analysis: await response.json() };
  } catch {
    return { ok: false, error: `Serveur d'analyse injoignable (${API_URL})` };
  }
}

export default defineBackground(() => {
  browser.runtime.onMessage.addListener((message: AnalyzeRequest) => {
    if (message.type === 'analyze') return analyze(message.urls);
  });
});
