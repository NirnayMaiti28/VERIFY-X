# Headline Verification API

FastAPI backend for the DTI headline verification system. This service exposes
health and verification endpoints used by the frontend and delegates claim
analysis to the research verification pipeline.

## Prerequisites

- Python 3.11+
- Access to the research pipeline at `../research/research/text_verification`
- Optional API keys needed by the research pipeline (if applicable)

## Setup

1. Go to the backend folder.
2. Create and activate a virtual environment.
3. Install dependencies.

```bash
cd DTI-Backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

For local testing and development tools:

```bash
pip install -r requirements-dev.txt
```

## Configuration

The backend reads settings from environment variables (see `app/config.py`).
Common values:

- `HOST` (default: `0.0.0.0`)
- `PORT` (default: `8000`)
- `RELOAD` (default: `false`)
- `RATE_LIMIT` (default: `5/minute`)
- `VERIFY_TIMEOUT_SECONDS` (default: `20`)

Create a `.env` file in `DTI-Backend` if you want to override defaults.

## Run the API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

When the app starts, it attempts to initialize the verification pipeline.
If initialization fails, `/api/v1/verify` returns `503` and `/api/v1/health`
reports the degraded state.

## Test

```bash
pytest
```

## Endpoints

- `GET /api/v1/health` - reports API and pipeline readiness
- `POST /api/v1/verify` - verifies a claim/headline

Example request:

```json
{
   "claim": "A major hurricane made landfall in New York City today."
}
```

## Notes

- `app/dependencies.py` injects the research path dynamically so the backend can
   import `text_verification.pipeline.verify_pipeline.VerificationPipeline`.
- If that import is unavailable, the backend still starts, but verification is
   disabled until the dependency path is fixed.