import type { AnalyzeRequest, AnalyzeResponse } from '@/utils/analysis';

const API_URL = import.meta.env.WXT_API_URL ?? 'http://127.0.0.1:8787';

async function analyze(url: string): Promise<AnalyzeResponse> {
  let html: string;
  try {
    const page = await fetch(url, { credentials: 'include' });
    if (!page.ok) return { ok: false, error: `La page des CGU a répondu ${page.status}` };
    html = await page.text();
  } catch {
    return { ok: false, error: 'Impossible de télécharger la page des CGU' };
  }

  try {
    const response = await fetch(`${API_URL}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, html }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      return { ok: false, error: body.detail ?? `Le serveur d'analyse a répondu ${response.status}` };
    }
    return { ok: true, analysis: await response.json() };
  } catch {
    return { ok: false, error: `Serveur d'analyse injoignable (${API_URL})` };
  }
}

export default defineBackground(() => {
  browser.runtime.onMessage.addListener((message: AnalyzeRequest) => {
    if (message.type === 'analyze') return analyze(message.url);
  });
});
