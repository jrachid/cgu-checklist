const TERMS_TEXT =
  /conditions?\s+(générales|generales|d['’]utilisation|de\s+vente|du\s+service)|\bCG[UV]\b|terms(\s+(of\s+(service|use)|and\s+conditions|&\s+conditions))?\b|\bToS\b/i;
const TERMS_HREF = /cgu|cgv|terms|conditions|legal|tos\b/i;
const PRIVACY = /confidentialit|privacy|données\s+personnelles|cookies/i;
const ACCEPTANCE =
  /accept|agree|consent|en\s+(vous\s+inscrivant|continuant|créant|cliquant|vous\s+connectant|poursuivant)|by\s+(signing|continuing|creating|clicking|registering)|j['’]ai\s+lu/i;
const MAX_SENTENCE_LENGTH = 400;

export interface ConsentSpot {
  termsUrl: string;
  privacyUrl: string | null;
  anchor: Element;
}

export function withoutHash(href: string): string {
  const url = new URL(href);
  url.hash = '';
  return url.href;
}

function isPrivacyLink(link: HTMLAnchorElement): boolean {
  return PRIVACY.test(link.textContent ?? '') || PRIVACY.test(link.pathname);
}

// Un lien qui nomme les CGU en est un, même s'il cite aussi la confidentialité (« Terms of Use and … Privacy Statement »).
function isTermsLink(link: HTMLAnchorElement): boolean {
  const text = link.textContent ?? '';
  if (TERMS_TEXT.test(text)) return true;
  return TERMS_HREF.test(link.pathname) && !isPrivacyLink(link);
}

function acceptanceSentenceOf(link: HTMLAnchorElement): Element | null {
  for (let node = link.parentElement; node && node !== document.body; node = node.parentElement) {
    const text = node.textContent ?? '';
    if (text.length > MAX_SENTENCE_LENGTH) return null;
    if (ACCEPTANCE.test(text)) return node;
  }
  return null;
}

// findConsentSpot rend null quand aucun lien de CGU n'apparaît dans une phrase d'acceptation.
export function findConsentSpot(root: ParentNode = document): ConsentSpot | null {
  for (const link of root.querySelectorAll<HTMLAnchorElement>('a[href]')) {
    if (!link.href.startsWith('http') || !isTermsLink(link)) continue;
    const sentence = acceptanceSentenceOf(link);
    if (sentence) {
      const privacy = [...sentence.querySelectorAll<HTMLAnchorElement>('a[href]')].find(
        (other) => other !== link && other.href.startsWith('http') && isPrivacyLink(other),
      );
      return {
        termsUrl: withoutHash(link.href),
        privacyUrl: privacy ? withoutHash(privacy.href) : null,
        anchor: sentence,
      };
    }
  }
  return null;
}
