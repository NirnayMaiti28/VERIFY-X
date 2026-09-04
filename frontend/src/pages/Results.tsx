// ─── VERIFY-X 2.0 — Results Page ───

import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getVerification } from '../services/api';
import type { VerificationResponse } from '../types/verification';
import { getVerdictConfig, formatConfidence, formatDate, formatLatency } from '../utils/verdict';

export default function Results() {
  const { id } = useParams<{ id: string }>();
  const [result, setResult] = useState<VerificationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getVerification(id)
      .then(setResult)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="results-page loading">
        <div className="spinner-large" />
        <p>Loading verification result...</p>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="results-page error-state">
        <h2>Result Not Found</h2>
        <p>{error || 'The verification result could not be found.'}</p>
        <a href="/" className="back-link">← Back to Home</a>
      </div>
    );
  }

  const verdictConfig = getVerdictConfig(result.verdict);

  return (
    <div className="results-page">
      {/* Verdict Header */}
      <section className="verdict-section">
        <div className="verdict-header">
          <span className="verdict-label">VERDICT</span>
          <div
            className="verdict-display"
            style={{ color: verdictConfig.color, borderColor: verdictConfig.borderColor }}
          >
            <span className="verdict-icon">{verdictConfig.icon}</span>
            <span className="verdict-text">{verdictConfig.label}</span>
          </div>
        </div>

        <div className="confidence-section">
          <span className="confidence-label">Confidence</span>
          <div className="confidence-bar-container">
            <div
              className="confidence-bar"
              style={{
                width: formatConfidence(result.confidence),
                backgroundColor: verdictConfig.color,
              }}
            />
          </div>
          <span className="confidence-value" style={{ color: verdictConfig.color }}>
            {formatConfidence(result.confidence)}
          </span>
        </div>
      </section>

      {/* Claim */}
      <section className="claim-section">
        <h3>CLAIM</h3>
        <blockquote className="claim-text">{result.claim}</blockquote>
        {result.claim_analysis && (
          <div className="claim-metadata">
            <span className="meta-tag">Language: {result.claim_analysis.language}</span>
            <span className="meta-tag">Type: {result.claim_analysis.claim_type}</span>
            {result.claim_analysis.entities.map((e, i) => (
              <span key={i} className="entity-tag">{e}</span>
            ))}
          </div>
        )}
      </section>

      {/* Reasoning */}
      <section className="reasoning-section">
        <h3>WHY?</h3>
        <p className="summary-text">{result.summary}</p>
        {result.reasoning && (
          <details className="reasoning-details">
            <summary>Detailed Reasoning</summary>
            <p>{result.reasoning}</p>
          </details>
        )}
      </section>

      {/* Evidence */}
      {result.evidence.length > 0 && (
        <section className="evidence-section">
          <h3>EVIDENCE</h3>
          <div className="evidence-list">
            {result.evidence.map((e, i) => (
              <div key={i} className={`evidence-card stance-${e.stance?.toLowerCase()}`}>
                <div className="evidence-header">
                  <span className="evidence-id">[{e.evidence_id}]</span>
                  <span className="evidence-source">{e.title || e.source}</span>
                  <span className={`stance-badge ${e.stance?.toLowerCase()}`}>
                    {e.stance}
                  </span>
                </div>
                <p className="evidence-passage">{e.passage}</p>
                <div className="evidence-footer">
                  <a
                    href={e.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="source-link"
                  >
                    View Source ↗
                  </a>
                  <span className="relevance-score">
                    Relevance: {Math.round(e.relevance_score * 100)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Source Agreement */}
      {(result.agreement.support_count > 0 ||
        result.agreement.refute_count > 0 ||
        result.agreement.neutral_count > 0) && (
        <section className="agreement-section">
          <h3>SOURCE AGREEMENT</h3>
          <div className="agreement-bars">
            <div className="agreement-row">
              <span className="agreement-label">Support</span>
              <div className="agreement-bar-container">
                <div
                  className="agreement-bar support"
                  style={{
                    width: `${(result.agreement.support_count / Math.max(result.agreement.support_count + result.agreement.refute_count + result.agreement.neutral_count, 1)) * 100}%`,
                  }}
                />
              </div>
              <span className="agreement-count">{result.agreement.support_count}</span>
            </div>
            <div className="agreement-row">
              <span className="agreement-label">Neutral</span>
              <div className="agreement-bar-container">
                <div
                  className="agreement-bar neutral"
                  style={{
                    width: `${(result.agreement.neutral_count / Math.max(result.agreement.support_count + result.agreement.refute_count + result.agreement.neutral_count, 1)) * 100}%`,
                  }}
                />
              </div>
              <span className="agreement-count">{result.agreement.neutral_count}</span>
            </div>
            <div className="agreement-row">
              <span className="agreement-label">Refute</span>
              <div className="agreement-bar-container">
                <div
                  className="agreement-bar refute"
                  style={{
                    width: `${(result.agreement.refute_count / Math.max(result.agreement.support_count + result.agreement.refute_count + result.agreement.neutral_count, 1)) * 100}%`,
                  }}
                />
              </div>
              <span className="agreement-count">{result.agreement.refute_count}</span>
            </div>
          </div>
        </section>
      )}

      {/* Model Signals */}
      <section className="signals-section">
        <h3>MODEL SIGNALS</h3>
        <div className="signals-grid">
          {Object.entries(result.signals).map(([key, value]) => (
            <div key={key} className="signal-item">
              <span className="signal-label">{key.replace(/_/g, ' ')}</span>
              <div className="signal-bar-container">
                <div
                  className="signal-bar"
                  style={{ width: `${(value as number) * 100}%` }}
                />
              </div>
              <span className="signal-value">{Math.round((value as number) * 100)}%</span>
            </div>
          ))}
        </div>
      </section>

      {/* Processing Metrics */}
      <section className="metrics-section">
        <h3>PROCESSING</h3>
        <div className="metrics-grid">
          <div className="metric">
            <span className="metric-label">Total</span>
            <span className="metric-value">{formatLatency(result.processing.total_ms)}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Retrieval</span>
            <span className="metric-value">{formatLatency(result.processing.retrieval_ms)}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Inference</span>
            <span className="metric-value">{formatLatency(result.processing.inference_ms)}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Sources</span>
            <span className="metric-value">{result.processing.sources_retrieved}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Evidence</span>
            <span className="metric-value">{result.processing.evidence_selected}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Cached</span>
            <span className="metric-value">{result.processing.cache_hit ? 'Yes' : 'No'}</span>
          </div>
        </div>
      </section>

      {/* Timestamp */}
      <div className="result-timestamp">
        Verified at {formatDate(result.created_at)}
      </div>

      <a href="/" className="back-link">← Verify another claim</a>
    </div>
  );
}
