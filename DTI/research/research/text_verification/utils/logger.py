import json
from datetime import datetime, timezone
from pathlib import Path


class VerificationAuditLogger:

	def __init__(self, log_dir=None, file_name="verification_audit.jsonl"):
		base_dir = Path(log_dir) if log_dir else Path("logs")
		self.log_dir = base_dir
		self.log_file = self.log_dir / file_name
		self.log_dir.mkdir(parents=True, exist_ok=True)

	def _source_diversity(self, evidence_list):
		sources = {
			(evidence.get("source") or "").strip().lower()
			for evidence in (evidence_list or [])
			if (evidence.get("source") or "").strip()
		}
		return len(sources)

	def classify_case(
		self,
		final_result,
		knowledge_result=None,
		query_candidates=None,
		retrieved_count=0,
		ranked_evidence=None,
		relevant_evidence=None,
		verification_results=None,
	):
		ranked_evidence = ranked_evidence or []
		relevant_evidence = relevant_evidence or []
		verification_results = verification_results or []

		verdict = (final_result or {}).get("verdict", "UNVERIFIED")
		confidence = float((final_result or {}).get("confidence", 0) or 0)
		retrieval_attempted = bool(query_candidates)

		tags = []

		if knowledge_result:
			tags.append("resolved_by_structured_knowledge")

		if retrieval_attempted and not knowledge_result and retrieved_count == 0:
			tags.append("retrieval_miss")

		if retrieval_attempted and retrieved_count > 0 and not ranked_evidence:
			tags.append("ranking_miss")

		if retrieval_attempted and ranked_evidence and not relevant_evidence:
			tags.append("relevance_filter_miss")

		if retrieval_attempted and relevant_evidence and not verification_results:
			tags.append("evidence_text_missing")

		supports = sum(1 for result in verification_results if float(result.get("SUPPORTS", 0) or 0) >= 0.6)
		refutes = sum(1 for result in verification_results if float(result.get("REFUTES", 0) or 0) >= 0.6)

		if supports > 0 and refutes > 0:
			tags.append("conflicting_evidence")

		source_diversity = self._source_diversity(relevant_evidence)
		if relevant_evidence and source_diversity < 2:
			tags.append("single_source_risk")

		if confidence < 0.55:
			tags.append("low_confidence")

		if verdict == "UNVERIFIED":
			tags.append("abstained")

		hard_case = (
			verdict == "UNVERIFIED"
			or confidence < 0.7
			or "conflicting_evidence" in tags
			or "retrieval_miss" in tags
		)

		return {
			"tags": sorted(set(tags)),
			"hard_case": hard_case,
			"source_diversity": source_diversity,
			"support_votes": supports,
			"refute_votes": refutes,
		}

	def log_event(
		self,
		claim,
		normalized_claim,
		result,
		query_candidates=None,
		entities=None,
		knowledge_result=None,
		retrieved_count=0,
		ranked_evidence=None,
		relevant_evidence=None,
		verification_results=None,
		sources_used=None,
		ollama_response=None,
	):
		ranked_evidence = ranked_evidence or []
		relevant_evidence = relevant_evidence or []
		verification_results = verification_results or []

		taxonomy = self.classify_case(
			final_result=result,
			knowledge_result=knowledge_result,
			query_candidates=query_candidates,
			retrieved_count=retrieved_count,
			ranked_evidence=ranked_evidence,
			relevant_evidence=relevant_evidence,
			verification_results=verification_results,
		)

		top_evidence = []
		for evidence in relevant_evidence[:5]:
			top_evidence.append(
				{
					"title": evidence.get("title"),
					"source": evidence.get("source"),
					"url": evidence.get("url"),
					"similarity_score": evidence.get("similarity_score"),
					"final_score": evidence.get("final_score"),
				}
			)

		event = {
			"timestamp": datetime.now(timezone.utc).isoformat(),
			"claim": claim,
			"normalized_claim": normalized_claim,
			"verdict": (result or {}).get("verdict"),
			"confidence": (result or {}).get("confidence"),
			"taxonomy": taxonomy,
			"query_candidates": query_candidates or [],
			"entity_count": len(entities or []),
			"retrieved_count": int(retrieved_count or 0),
			"ranked_count": len(ranked_evidence),
			"relevant_count": len(relevant_evidence),
			"verification_count": len(verification_results),
			"top_evidence": top_evidence,
			"sources_used": sources_used or top_evidence,
			"ollama_response": (ollama_response or "")[:3000],
		}

		with self.log_file.open("a", encoding="utf-8") as f:
			f.write(json.dumps(event, ensure_ascii=True) + "\n")


__all__ = ["VerificationAuditLogger"]
