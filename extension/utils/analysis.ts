export type Verdict = 'yes' | 'no' | 'not_mentioned' | 'unsure';

export interface Citation {
  url: string;
  id: string;
  probability: number;
  text: string;
  quote: string;
}

export interface Point {
  key: string;
  label: string;
  verdict: Verdict;
  probabilities: Record<string, number>;
  source: string;
  citations: Citation[];
}

export interface AnalyzedDocument {
  url: string;
  model: string;
  input_tokens: number;
  paragraphs: number;
  kind: 'contract' | 'relay';
  follow: string[];
}

export interface Analysis {
  documents: AnalyzedDocument[];
  follow: string[];
  points: Point[];
}

export interface AnalyzeRequest {
  type: 'analyze';
  urls: string[];
}

export interface InspectRequest {
  type: 'inspect';
  url: string;
  html: string;
}

export interface PageLink {
  text: string;
  href: string;
}

export interface InspectResult {
  html: string;
  links: PageLink[];
}

export type AnalyzeResponse = { ok: true; analysis: Analysis } | { ok: false; error: string };
