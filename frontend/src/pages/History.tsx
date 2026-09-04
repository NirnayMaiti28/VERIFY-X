// ─── VERIFY-X 2.0 — History Page ───

import { useEffect, useState } from 'react';
import { getHistory } from '../services/api';
import type { VerificationSummary } from '../types/verification';
import { getVerdictConfig, formatConfidence, formatDate } from '../utils/verdict';

export default function History() {
  const [items, setItems] = useState<VerificationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [hasNext, setHasNext] = useState(false);

  useEffect(() => {
    setLoading(true);
    getHistory(page)
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
        setHasNext(res.has_next);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [page]);

  return (
    <div className="history-page">
      <h1>Verification History</h1>
      <p className="history-subtitle">{total} total verifications</p>

      {loading ? (
        <div className="loading-state">
          <div className="spinner-large" />
        </div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <span className="empty-icon">📋</span>
          <h3>No verifications yet</h3>
          <p>Your verification history will appear here.</p>
          <a href="/" className="cta-link">Verify your first claim →</a>
        </div>
      ) : (
        <>
          <div className="history-list">
            {items.map((item) => {
              const config = getVerdictConfig(item.verdict);
              return (
                <a
                  key={item.request_id}
                  href={`/results/${item.request_id}`}
                  className="history-card"
                >
                  <div className="history-card-header">
                    <span
                      className="verdict-mini-badge"
                      style={{
                        color: config.color,
                        backgroundColor: config.bgColor,
                        borderColor: config.borderColor,
                      }}
                    >
                      {config.icon} {config.label}
                    </span>
                    <span className="history-date">{formatDate(item.created_at)}</span>
                  </div>
                  <p className="history-claim">{item.claim}</p>
                  <div className="history-card-footer">
                    <span className="confidence-mini">
                      {formatConfidence(item.confidence)} confidence
                    </span>
                    <span className="evidence-count-mini">
                      {item.evidence_count} evidence
                    </span>
                    <span className="language-mini">{item.language}</span>
                  </div>
                </a>
              );
            })}
          </div>

          {/* Pagination */}
          <div className="pagination">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="pagination-btn"
            >
              ← Previous
            </button>
            <span className="page-indicator">Page {page}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasNext}
              className="pagination-btn"
            >
              Next →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
