# Research Verification Module

This folder contains the standalone research-grade text verification pipeline
used by the backend service. It provides:

- A FastAPI app for claim verification
- A terminal mode for manual verification
- Retrieval, ranking, and verdict-generation components

## Project Layout

- `text_verification/main.py`: FastAPI app and terminal entry mode
- `text_verification/api/verify_route.py`: verification API route
- `text_verification/pipeline/verify_pipeline.py`: orchestration pipeline
- `text_verification/retrieval/*`: source retrieval adapters
- `text_verification/verdict/*`: verdict logic
- `text_verification/config/settings.py`: environment-backed settings

## Prerequisites

- Python 3.11+
- Optional external API credentials depending on enabled retrievers

## Install

```bash
cd research/research
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Notes:

- `requirements.txt` includes `en-core-web-sm`, but many environments still
	require the explicit spaCy model download command shown above.
- Heavy ML dependencies (`torch`, `transformers`, `sentence-transformers`) can
	take time to install.

## Configuration

Environment values are loaded from `.env` at `research/research/.env`.
Important keys from `text_verification/config/settings.py`:

- `NEWS_API_KEY`
- `VERIFY_TIMEOUT_SECONDS` (used by the API route, default `45`)
- `VERDICT_TRUE_THRESHOLD`
- `VERDICT_FALSE_THRESHOLD`
- `VERDICT_UNVERIFIED_CAP`
- `VERDICT_ABSTAIN_MIN_CONFIDENCE`
- `RETRIEVAL_TIME_BUDGET_SECONDS`

## Run

Start API server:

```bash
uvicorn text_verification.main:app --host 0.0.0.0 --port 8001 --reload
```

Run terminal mode:

```bash
python -m text_verification.main
```

## API

- `GET /` returns service status message
- `POST /verify-text` verifies a single claim

Example request:

```json
{
	"claim": "The WHO declared a new global pandemic this week."
}
```

The `/verify-text` route is rate-limited (`10/minute`) and protected with an
execution timeout (`VERIFY_TIMEOUT_SECONDS`). If a timeout occurs, the API
returns an `UNVERIFIED` fallback response.

## Integration Note

The backend service imports this module via
`text_verification.pipeline.verify_pipeline.VerificationPipeline`.
If you move directories, update import paths and backend dependency setup.
