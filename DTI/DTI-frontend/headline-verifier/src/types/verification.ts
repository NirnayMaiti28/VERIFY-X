export type Verdict =
  | 'True'
  | 'False'
  | 'Misleading'
  | 'Not Enough Information';

export interface ConfidenceBreakdown {
  llm: number;
  agreement: number;
  consistency: number;
  credibility: number;
  diversity: number;
}

export interface AgreementSignal {
  support_count: number;
  refute_count: number;
  neutral_count: number;
  explicit_contradiction: boolean;
}

export interface SourceItem {
  title: string;
  url: string;
  credibility: 'High' | 'Medium' | 'Low';
  snippet: string;
}

export interface VerificationResult {
  claim: string;
  verdict: Verdict;
  confidence: number;
  confidence_breakdown: ConfidenceBreakdown;
  summary: string;
  explanation: string;
  conflicting_sources: boolean;
  agreement_signal: AgreementSignal;
  evidence_summary: string;
  sources: SourceItem[];
}
