from typing import Any, Dict


_ALLOWED_VERDICTS = {
    "True",
    "False",
    "Misleading",
    "Not Enough Information",
}


def extract_llm_payload(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    verdict = str(raw_result.get("verdict", "Not Enough Information") or "Not Enough Information")
    if verdict not in _ALLOWED_VERDICTS:
        verdict = "Not Enough Information"

    summary = str(raw_result.get("summary") or raw_result.get("explanation") or "")
    explanation = str(raw_result.get("explanation") or "")

    return {
        "claim": str(raw_result.get("claim") or ""),
        "verdict": verdict,
        "summary": summary,
        "explanation": explanation,
    }
