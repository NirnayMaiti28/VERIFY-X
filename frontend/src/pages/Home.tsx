// ─── VERIFY-X 2.0 — Home Page ───

import { useState, useRef } from 'react';
import type { VerificationResponse } from '../types/verification';
import { verifyText, verifyImage } from '../services/api';

export default function Home() {
  const [claim, setClaim] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VerificationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleVerifyText = async () => {
    if (!claim.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await verifyText({ claim: claim.trim() });
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyImage = async (file: File) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await verifyImage(file);
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Image verification failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      setSelectedFile(file);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) setSelectedFile(file);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleVerifyText();
    }
  };

  return (
    <div className="home-page">
      {/* Hero Section */}
      <section className="hero">
        <div className="hero-badge">AI-Powered Fact Verification</div>
        <h1 className="hero-title">VERIFY-X</h1>
        <p className="hero-subtitle">
          Verify information. See the evidence.
        </p>
        <p className="hero-description">
          Multilingual multimodal fact verification powered by fine-tuned language models,
          evidence retrieval, and calibrated confidence scoring.
        </p>

        {/* Input Area */}
        <div className="verify-input-container">
          <div className="input-group">
            <textarea
              id="claim-input"
              className="claim-input"
              placeholder="Paste a claim to verify..."
              value={claim}
              onChange={(e) => setClaim(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={3}
              maxLength={2000}
            />
            <div className="input-footer">
              <span className="char-count">{claim.length}/2000</span>
              <button
                id="verify-button"
                className="verify-button"
                onClick={handleVerifyText}
                disabled={!claim.trim() || loading}
              >
                {loading ? (
                  <span className="button-loading">
                    <span className="spinner" />
                    Verifying...
                  </span>
                ) : (
                  'VERIFY'
                )}
              </button>
            </div>
          </div>

          <div className="divider">
            <span>OR</span>
          </div>

          {/* Image Upload */}
          <div
            className={`upload-zone ${dragActive ? 'drag-active' : ''} ${selectedFile ? 'has-file' : ''}`}
            onDragEnter={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={(e) => { e.preventDefault(); setDragActive(false); }}
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              className="hidden"
            />
            {selectedFile ? (
              <div className="selected-file">
                <span className="file-icon">🖼️</span>
                <span className="file-name">{selectedFile.name}</span>
                <button
                  className="verify-image-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleVerifyImage(selectedFile);
                  }}
                  disabled={loading}
                >
                  Verify Image
                </button>
              </div>
            ) : (
              <div className="upload-prompt">
                <span className="upload-icon">📷</span>
                <span>Drop an image or click to upload</span>
                <span className="upload-hint">Screenshots, memes, infographics</span>
              </div>
            )}
          </div>
        </div>

        {/* Supported Languages */}
        <div className="supported-languages">
          <span className="lang-label">Supported:</span>
          <span className="lang-tag">English</span>
          <span className="lang-tag">हिन्दी</span>
          <span className="lang-tag">বাংলা</span>
          <span className="lang-tag">Code-mixed</span>
        </div>
      </section>

      {/* Error Display */}
      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {/* Quick Result Preview */}
      {result && (
        <section className="quick-result">
          <div className="result-card">
            <div className="result-header">
              <span className={`verdict-badge verdict-${result.verdict.toLowerCase().replace(/_/g, '-')}`}>
                {result.verdict.replace(/_/g, ' ')}
              </span>
              <span className="confidence-display">
                {Math.round(result.confidence * 100)}% confidence
              </span>
            </div>
            <p className="result-summary">{result.summary}</p>
            <a href={`/results/${result.request_id}`} className="view-details-link">
              View full analysis →
            </a>
          </div>
        </section>
      )}

      {/* Features */}
      <section className="features">
        <div className="feature-grid">
          <div className="feature-card">
            <span className="feature-icon">🔍</span>
            <h3>Evidence Retrieval</h3>
            <p>Multi-source search with hybrid BM25 + dense retrieval and cross-encoder reranking</p>
          </div>
          <div className="feature-card">
            <span className="feature-icon">🧠</span>
            <h3>Fine-Tuned Models</h3>
            <p>QLoRA-trained Qwen3-8B specifically optimized for fact verification</p>
          </div>
          <div className="feature-card">
            <span className="feature-icon">🖼️</span>
            <h3>Multimodal</h3>
            <p>Verify screenshots, memes, and infographics with OCR + Vision-Language Models</p>
          </div>
          <div className="feature-card">
            <span className="feature-icon">🌐</span>
            <h3>Multilingual</h3>
            <p>English, Hindi, Bengali, and code-mixed text with automatic language detection</p>
          </div>
          <div className="feature-card">
            <span className="feature-icon">📊</span>
            <h3>Calibrated Confidence</h3>
            <p>Temperature-scaled confidence scores reflecting actual empirical reliability</p>
          </div>
          <div className="feature-card">
            <span className="feature-icon">🔢</span>
            <h3>Deterministic Verification</h3>
            <p>Numerical and temporal reasoning without relying on LLM arithmetic</p>
          </div>
        </div>
      </section>
    </div>
  );
}
