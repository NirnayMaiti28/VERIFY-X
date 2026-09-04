// ─── VERIFY-X 2.0 — About Page ───

export default function About() {
  return (
    <div className="about-page">
      <h1>About VERIFY-X</h1>
      <p className="about-subtitle">
        Multimodal AI Fact Verification & Evidence Intelligence Platform
      </p>

      <section className="about-section">
        <h2>What is VERIFY-X?</h2>
        <p>
          VERIFY-X is an evidence-grounded AI verification system that goes beyond simple
          LLM prompting. It combines fine-tuned language models, multimodal understanding,
          multi-source information retrieval, hybrid ranking, deterministic verification,
          source analysis, and calibrated confidence to deliver reliable fact verification.
        </p>
      </section>

      <section className="about-section">
        <h2>How It Works</h2>
        <div className="pipeline-steps">
          <div className="pipeline-step">
            <span className="step-number">1</span>
            <h3>Claim Analysis</h3>
            <p>Your input is normalized, entities are extracted, and the language is auto-detected.</p>
          </div>
          <div className="pipeline-step">
            <span className="step-number">2</span>
            <h3>Evidence Retrieval</h3>
            <p>Multiple search queries hit Google News, Wikipedia, GDELT, and other sources.</p>
          </div>
          <div className="pipeline-step">
            <span className="step-number">3</span>
            <h3>Hybrid Ranking</h3>
            <p>BM25 + dense embeddings retrieve candidates; a cross-encoder selects the strongest evidence.</p>
          </div>
          <div className="pipeline-step">
            <span className="step-number">4</span>
            <h3>Verification</h3>
            <p>Temporal, numerical, and source credibility analysis combine with the fine-tuned model prediction.</p>
          </div>
          <div className="pipeline-step">
            <span className="step-number">5</span>
            <h3>Calibrated Verdict</h3>
            <p>The verdict engine produces a confidence-calibrated result with full evidence traceability.</p>
          </div>
        </div>
      </section>

      <section className="about-section">
        <h2>Technology</h2>
        <div className="tech-grid">
          <div className="tech-item">
            <strong>Text Model</strong>
            <span>Qwen3-8B (QLoRA fine-tuned)</span>
          </div>
          <div className="tech-item">
            <strong>Vision Model</strong>
            <span>Qwen2.5-VL-7B-Instruct</span>
          </div>
          <div className="tech-item">
            <strong>OCR</strong>
            <span>PaddleOCR</span>
          </div>
          <div className="tech-item">
            <strong>Backend</strong>
            <span>FastAPI + PostgreSQL + Redis</span>
          </div>
          <div className="tech-item">
            <strong>Frontend</strong>
            <span>React + TypeScript + Vite</span>
          </div>
          <div className="tech-item">
            <strong>Retrieval</strong>
            <span>BM25 + FAISS + Cross-Encoder</span>
          </div>
        </div>
      </section>

      <section className="about-section">
        <h2>Supported Languages</h2>
        <div className="language-list">
          <span className="lang-item">English</span>
          <span className="lang-item">हिन्दी (Hindi)</span>
          <span className="lang-item">বাংলা (Bengali)</span>
          <span className="lang-item">Code-mixed (EN/HI)</span>
        </div>
      </section>

      <section className="about-section">
        <h2>Important Notes</h2>
        <ul className="notes-list">
          <li>VERIFY-X never fabricates evidence or URLs. Every source is traceable.</li>
          <li>When evidence is insufficient, the system returns "Not Enough Information" rather than guessing.</li>
          <li>Source credibility is one signal — it never equals truth by itself.</li>
          <li>Confidence scores are calibrated and represent empirical reliability.</li>
          <li>Numerical calculations use deterministic computation, not LLM arithmetic.</li>
        </ul>
      </section>
    </div>
  );
}
