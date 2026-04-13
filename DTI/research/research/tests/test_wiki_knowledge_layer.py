from text_verification.knowledge_layer.wiki_knowledge_layer import WikiKnowledgeLayer


def test_aggregate_false_when_high_confidence_false():
    layer = WikiKnowledgeLayer()

    scored_claims = [
        {
            "claim": {"claim_text": "Joe Biden is the president of USA"},
            "verdict": "FALSE",
            "confidence": 0.91,
            "reason": "Contradicted by evidence",
            "evidence_used": "Wikidata position held",
            "sources": [
                "https://www.wikidata.org/wiki/Q6279",
                "https://en.wikipedia.org/wiki/Joe_Biden",
            ],
        },
        {
            "claim": {"claim_text": "Washington is in the USA"},
            "verdict": "TRUE",
            "confidence": 0.84,
            "reason": "Supported by evidence",
            "evidence_used": "Wikidata country",
            "sources": ["https://www.wikidata.org/wiki/Q61"],
        },
    ]

    result = layer.aggregate_verdict(scored_claims)

    assert result["verdict"] == "FALSE"
    assert result["confidence"] > 0.0
    assert len(result["claim_breakdown"]) == 2
    assert result["all_sources"]


def test_verify_article_with_mocked_clients(monkeypatch):
    layer = WikiKnowledgeLayer()

    def fake_extract(_text):
        return [
            {
                "subject": "Joe Biden",
                "predicate": "is president of",
                "object": "USA",
                "claim_text": "Joe Biden is president of USA.",
                "entities": [{"text": "Joe Biden", "label": "PERSON"}],
            }
        ]

    def fake_lookup(entity, predicate_hint):
        assert entity == "Joe Biden"
        assert predicate_hint == "is president of"
        return {
            "qid": "Q6279",
            "label": "Joe Biden",
            "properties": {"P39": ["President of the United States"]},
            "wikidata_url": "https://www.wikidata.org/wiki/Q6279",
        }

    def fake_summary(entity):
        assert entity == "Joe Biden"
        return {
            "title": "Joe Biden",
            "extract": "Joe Biden is the 46th president of the United States.",
            "wikipedia_url": "https://en.wikipedia.org/wiki/Joe_Biden",
            "exists": True,
        }

    def fake_score(claim, wikidata, wiki_summary):
        assert claim["subject"] == "Joe Biden"
        assert wikidata["qid"] == "Q6279"
        assert wiki_summary["title"] == "Joe Biden"
        return {
            "claim": claim,
            "verdict": "TRUE",
            "confidence": 0.9,
            "reason": "Matches Wikidata and Wikipedia context",
            "evidence_used": "P39 + summary",
            "sources": [wikidata["wikidata_url"], wiki_summary["wikipedia_url"]],
            "llm_raw": "{}",
        }

    monkeypatch.setattr(layer, "extract_entities_and_claims", fake_extract)
    monkeypatch.setattr(layer, "lookup_wikidata", fake_lookup)
    monkeypatch.setattr(layer, "fetch_wikipedia_summary", fake_summary)
    monkeypatch.setattr(layer, "score_claim", fake_score)

    result = layer.verify_article("Joe Biden is president of USA.")

    assert result["verdict"] == "TRUE"
    assert result["confidence"] == 0.9
    assert len(result["claim_breakdown"]) == 1
    assert result["all_sources"] == [
        "https://www.wikidata.org/wiki/Q6279",
        "https://en.wikipedia.org/wiki/Joe_Biden",
    ]
