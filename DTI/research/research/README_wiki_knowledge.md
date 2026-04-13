# Wiki Knowledge Layer

This module adds fact grounding with Wikimedia-only sources:

- Wikidata via SPARQL endpoint: https://query.wikidata.org/sparql
- Wikipedia summary endpoint: https://en.wikipedia.org/api/rest_v1/page/summary/{title}

No API keys are required.

## Files

- `text_verification/knowledge_layer/wiki_knowledge_layer.py`: orchestration and claim scoring
- `text_verification/knowledge_layer/wikidata_client.py`: QID resolution + SPARQL property fetch
- `text_verification/knowledge_layer/wikipedia_client.py`: page summary retrieval + fallback
- `text_verification/knowledge_layer/claim_extractor.py`: entity and claim extraction
- `text_verification/knowledge_layer/cache.py`: TTL cache utility (24 hours)

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

2. Make sure the local LLM endpoint is available if you use LLM scoring:

- Default URL: `http://localhost:11434/api/generate`
- Default model: `mistral`
- Override via env vars `OLLAMA_URL` and `OLLAMA_MODEL`

## Predicate Mapping

`wikidata_client.py` maps natural predicate hints to Wikidata properties.

Current mapping:

- `population` -> `P1082`
- `date of birth` -> `P569`
- `country` -> `P17`
- `head of state` -> `P35`
- `employer` -> `P108`
- `member of` -> `P463`
- `position held` -> `P39`
- `located in` -> `P131`
- `inception` -> `P571`

To add new mappings, edit `PREDICATE_TO_PROPERTY` in `wikidata_client.py`.

## Caching

Both clients use a 24-hour TTL cache:

- Wikidata cache key: `entity + predicate`
- Wikipedia cache key: `entity`

This reduces repeated calls across similar article checks.

## Error Handling

- Wikidata timeout: retried once, then fails that lookup
- HTTP 429: exponential backoff with max 3 retries
- Wikipedia 404: graceful fallback to `wikipedia-api` package
- All Wikimedia requests send user-agent:
  `NewsVerifier/1.0 (your@email.com)`

## Pipeline Integration

`VerificationPipeline.verify_claim()` now routes claim verification through the
knowledge layer and uses only Wikimedia-grounded outputs for verdicting.

It returns enriched fields:

- `knowledge_verdict`
- `knowledge_claim_breakdown`
- `knowledge_gaps`
- `knowledge_sources`
