// ─── VERIFY-X 2.0 — TypeScript Types ───

// ── Verdict Labels ──
export type VerdictType =
  | 'TRUE'
  | 'FALSE'
  | 'MISLEADING'
  | 'PARTIALLY_TRUE'
  | 'NOT_ENOUGH_INFORMATION';

export type LanguageType = 'en' | 'hi' | 'bn' | 'code-mixed' | 'unknown';

export type ClaimType =
  | 'factual'
  | 'opinion'
  | 'prediction'
  | 'statistical'
  | 'historical'
  | 'scientific'
  | 'political'
  | 'economic'
  | 'other';

// ── Signals ──
export interface VerificationSignals {
  model_confidence: number;
  evidence_relevance: number;
  source_credibility: number;
  agreement_score: number;
  temporal_consistency: number;
  numerical_consistency: number;
}

export interface SourceAgreement {
  support_count: number;
  refute_count: number;
  neutral_count: number;
  contradiction_strength: number;
  source_diversity: number;
}

export interface NumericalAnalysis {
  detected_numbers: Record<string, unknown>[];
  calculations: Record<string, unknown>[];
  consistency: number | null;
}

export interface TimelineEvent {
  date: string;
  event: string;
  source?: string;
  relevance?: string;
}

export interface ProcessingMetrics {
  retrieval_ms: number;
  ranking_ms: number;
  inference_ms: number;
  total_ms: number;
  sources_retrieved: number;
  evidence_selected: number;
  cache_hit: boolean;
}

export interface ClaimAnalysis {
  original_claim: string;
  normalized_claim: string;
  entities: string[];
  dates: string[];
  locations: string[];
  numbers: string[];
  claim_type: ClaimType;
  language: LanguageType;
}

// ── Evidence ──
export interface EvidenceItem {
  evidence_id: string;
  source: string;
  title: string;
  url: string;
  published_at?: string;
  passage: string;
  relevance_score: number;
  stance: 'SUPPORTS' | 'REFUTES' | 'NEUTRAL';
  source_tier?: 'A' | 'B' | 'C';
  language: string;
  retriever?: string;
}

// ── Verification Response ──
export interface VerificationResponse {
  request_id: string;
  claim: string;
  language: LanguageType;
  verdict: VerdictType;
  confidence: number;
  summary: string;
  reasoning: string;
  evidence: EvidenceItem[];
  signals: VerificationSignals;
  agreement: SourceAgreement;
  timeline: TimelineEvent[];
  numerical_analysis?: NumericalAnalysis;
  image_analysis?: Record<string, unknown>;
  claim_analysis?: ClaimAnalysis;
  processing: ProcessingMetrics;
  created_at: string;
}

export interface VerificationSummary {
  request_id: string;
  claim: string;
  verdict: VerdictType;
  confidence: number;
  language: LanguageType;
  evidence_count: number;
  created_at: string;
}

// ── Request Types ──
export interface TextVerificationRequest {
  claim: string;
  language?: LanguageType;
  context?: string;
}

// ── API Responses ──
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface HealthResponse {
  status: string;
  version: string;
  database: string;
  redis: string;
  text_model: string;
  vision_model: string;
  timestamp: string;
}

export interface FeedbackRequest {
  request_id: string;
  is_correct: boolean;
  user_verdict?: string;
  comment?: string;
}

export interface ModelInfoResponse {
  text_model: string;
  text_adapter?: string;
  vision_model: string;
  vision_adapter?: string;
  embedding_model: string;
  model_mode: string;
}
