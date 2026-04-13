from typing import Any, Dict, List


MAX_SOURCES = 3


def _snippet_from_item(item: Dict[str, Any], max_len: int = 220) -> str:
    text = (item.get("content") or item.get("description") or "").strip()
    text = " ".join(text.split())
    if len(text) > max_len:
        return text[: max_len - 3].rstrip() + "..."
    return text


def extract_sources(raw_result: Dict[str, Any]) -> List[Dict[str, str]]:
    sources = raw_result.get("sources") or raw_result.get("evidence") or []
    result = []

    for item in sources[:MAX_SOURCES]:
        result.append(
            {
                "title": (item.get("title") or "Untitled source").strip(),
                "url": (item.get("url") or "").strip(),
                "credibility": (item.get("credibility") or "Low").strip().title(),
                "snippet": _snippet_from_item(item),
            }
        )

    return result
