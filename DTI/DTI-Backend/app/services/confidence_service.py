from typing import Any, Dict


DEFAULT_BREAKDOWN = {
    "llm": 0.5,
    "agreement": 0.0,
    "consistency": 1.0,
    "credibility": 0.4,
    "diversity": 0.5,
}


def extract_confidence_payload(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    confidence = float(raw_result.get("confidence", 0.5) or 0.5)
    breakdown = raw_result.get("confidence_breakdown") or {}

    payload = {
        "llm": float(breakdown.get("llm", DEFAULT_BREAKDOWN["llm"])),
        "agreement": float(breakdown.get("agreement", DEFAULT_BREAKDOWN["agreement"])),
        "consistency": float(breakdown.get("consistency", DEFAULT_BREAKDOWN["consistency"])),
        "credibility": float(breakdown.get("credibility", DEFAULT_BREAKDOWN["credibility"])),
        "diversity": float(breakdown.get("diversity", DEFAULT_BREAKDOWN["diversity"])),
    }

    return {
        "confidence": max(0.0, min(1.0, confidence)),
        "confidence_breakdown": payload,
    }
