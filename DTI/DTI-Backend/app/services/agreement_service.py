from typing import Any, Dict


def extract_agreement_signal(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    signal = raw_result.get("agreement_signal") or {}
    support_count = int(signal.get("support_count", 0) or 0)
    refute_count = int(signal.get("refute_count", 0) or 0)
    neutral_count = int(signal.get("neutral_count", 0) or 0)

    return {
        "support_count": support_count,
        "refute_count": refute_count,
        "neutral_count": neutral_count,
        "explicit_contradiction": bool(support_count > 0 and refute_count > 0),
    }


def build_evidence_summary(signal: Dict[str, Any]) -> str:
    support_count = int(signal.get("support_count", 0) or 0)
    refute_count = int(signal.get("refute_count", 0) or 0)
    neutral_count = int(signal.get("neutral_count", 0) or 0)

    parts = [
        f"{support_count} sources support the claim",
        f"{refute_count} refute it",
        f"{neutral_count} are neutral",
    ]
    return "; ".join(parts) + "."
