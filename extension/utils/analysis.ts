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
  citation: Citation | null;
}

export interface AnalyzedDocument {
  url: string;
  model: string;
  input_tokens: number;
  paragraphs: number;
}

export interface Analysis {
  documents: AnalyzedDocument[];
  points: Point[];
}

export interface AnalyzeRequest {
  type: 'analyze';
  urls: string[];
}

export type AnalyzeResponse = { ok: true; analysis: Analysis } | { ok: false; error: string };
