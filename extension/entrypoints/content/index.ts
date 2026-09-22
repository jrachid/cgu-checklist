import './style.css';
import type { AnalyzeResponse, Point } from '@/utils/analysis';
import { findConsentSpot } from '@/utils/detect';

const ICONS = { yes: '✅', no: '❌', not_mentioned: '➖', unsure: '⚠️' } as const;
const FRAGMENT_WORDS = 8;
const RESCAN_DELAY_MS = 500;

function el<K extends keyof HTMLElementTagNameMap>(tag: K, className?: string, text?: string) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

// Un text fragment (#:~:text=) fait défiler la page jusqu'au passage et le surligne ; « - » y est un séparateur.
function clauseUrl(termsUrl: string, quote: string): string {
  const words = quote.split(/\s+/);
  const encode = (part: string[]) => encodeURIComponent(part.join(' ')).replace(/-/g, '%2D');
  const range =
    words.length > 2 * FRAGMENT_WORDS
      ? `${encode(words.slice(0, FRAGMENT_WORDS))},${encode(words.slice(-FRAGMENT_WORDS))}`
      : encode(words);
  return `${termsUrl}#:~:text=${range}`;
}

function renderPoint(point: Point, termsUrl: string): HTMLElement {
  const summary = el('span', 'label', point.label);
  const icon = el('span', 'icon', ICONS[point.verdict]);
  if (!point.citation) {
    const row = el('div', `point ${point.verdict}`);
    row.append(icon, summary);
    return row;
  }
  const details = el('details', `point ${point.verdict}`);
  const head = el('summary');
  head.append(icon, summary);
  const quote = el('blockquote', undefined, point.citation.text);
  const link = el('a', 'source', 'Voir la clause dans les CGU ↗');
  link.href = clauseUrl(termsUrl, point.citation.quote);
  link.target = '_blank';
  link.rel = 'noopener';
  details.append(head, quote, link);
  return details;
}

function renderPanel(container: HTMLElement, termsUrl: string, onClose: () => void) {
  const panel = el('section', 'panel');
  const header = el('header');
  const title = el('strong', undefined, 'Ce que vous acceptez');
  const close = el('button', 'close', '×');
  close.title = 'Fermer';
  close.addEventListener('click', onClose);
  header.append(title, close);
  const body = el('div', 'body', 'Lecture des CGU…');
  panel.append(header, body);
  container.append(panel);

  return (response: AnalyzeResponse) => {
    body.replaceChildren();
    if (!response.ok) {
      body.append(el('p', 'error', response.error));
      return;
    }
    for (const point of response.analysis.points) body.append(renderPoint(point, termsUrl));
    body.append(el('p', 'legend', '✅ autorisé · ❌ exclu · ➖ non mentionné · ⚠️ à vérifier soi-même'));
  };
}

export default defineContentScript({
  matches: ['<all_urls>'],
  cssInjectionMode: 'ui',
  async main(ctx) {
    let shown = false;

    const tryShow = async () => {
      if (shown) return;
      const spot = findConsentSpot();
      if (!spot) return;
      shown = true;
      observer.disconnect();

      let fill: (response: AnalyzeResponse) => void = () => {};
      const ui = await createShadowRootUi(ctx, {
        name: 'cgu-checklist-panel',
        position: 'inline',
        anchor: spot.anchor,
        append: 'after',
        onMount: (container) => {
          fill = renderPanel(container, spot.termsUrl, () => ui.remove());
        },
      });
      ui.mount();
      const response: AnalyzeResponse = await browser.runtime.sendMessage({ type: 'analyze', url: spot.termsUrl });
      if (ctx.isValid) fill(response);
    };

    // Les formulaires d'inscription apparaissent souvent après le chargement (pages dynamiques, fenêtres modales).
    let timer: number | undefined;
    const observer = new MutationObserver(() => {
      clearTimeout(timer);
      timer = ctx.setTimeout(tryShow, RESCAN_DELAY_MS);
    });
    observer.observe(document.body, { childList: true, subtree: true });
    ctx.onInvalidated(() => observer.disconnect());
    await tryShow();
  },
});
