# VERIFY-X 2.0 — Architecture

## System Overview

VERIFY-X 2.0 is a multimodal AI fact verification platform that processes claims through a multi-stage pipeline combining information retrieval, hybrid ranking, fine-tuned language models, deterministic verification, and calibrated confidence scoring.

## Pipeline Architecture

```mermaid
graph TD
    A[User Input] --> B{Input Type}
    B -->|Text| C[Claim Normalization]
    B -->|Image| D[OCR + VLM]
    D --> C
    C --> E[Language Detection]
    E --> F[Query Generation]
    F --> G[Multi-Source Retrieval]
    G --> H[Document Processing]
    H --> I[BM25 Retrieval]
    H --> J[Dense Retrieval]
    I --> K[Merge & Deduplicate]
    J --> K
    K --> L[Cross-Encoder Reranking]
    L --> M[Evidence Selection]
    M --> N[Temporal Analysis]
    M --> O[Numerical Analysis]
    M --> P[Source Credibility]
    N --> Q[Cross-Source Agreement]
    O --> Q
    P --> Q
    Q --> R[Fine-Tuned Text Model]
    R --> S[Verdict Engine]
    S --> T[Confidence Calibration]
    T --> U[Final Result]
```

## Component Architecture

```mermaid
graph LR
    subgraph Frontend
        FE[React + TypeScript + Vite]
    end

    subgraph Backend
        API[FastAPI]
        SVC[Services Layer]
        ML[Model Layer]
        RET[Retrieval Layer]
        RNK[Ranking Layer]
        DB[(PostgreSQL)]
        CACHE[(Redis)]
    end

    subgraph ML_Training["ML Training (Colab)"]
        TR[train_text.py]
        HF[HuggingFace Hub]
    end

    FE --> API
    API --> SVC
    SVC --> ML
    SVC --> RET
    SVC --> RNK
    SVC --> DB
    SVC --> CACHE
    ML --> HF
    TR --> HF
```

## Key Design Decisions

1. **Independently replaceable components** — Every major component (text model, vision model, OCR, retriever, reranker, etc.) implements an interface that can be swapped without rewriting the application.

2. **Hybrid retrieval** — BM25 for lexical matching + dense embeddings for semantic matching, merged and reranked with a cross-encoder.

3. **Deterministic over probabilistic** — Numerical verification and temporal reasoning use deterministic computation rather than LLM arithmetic.

4. **Calibrated confidence** — Raw model probabilities are calibrated using temperature scaling to reflect empirical reliability.

5. **Mandatory evidence grounding** — Every verdict is backed by traceable evidence. No evidence = NOT_ENOUGH_INFORMATION.
