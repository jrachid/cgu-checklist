export type Verdict = 'yes' | 'no' | 'not_mentioned' | 'unsure';

export interface Citation {
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
  citation: Citation | null;
}

export interface Analysis {
  url: string;
  model: string;
  input_tokens: number;
  paragraphs: number;
  points: Point[];
}

export interface AnalyzeRequest {
  type: 'analyze';
  url: string;
}

export type AnalyzeResponse = { ok: true; analysis: Analysis } | { ok: false; error: string };
