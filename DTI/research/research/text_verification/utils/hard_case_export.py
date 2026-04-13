import argparse
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _parse_ts(value):
    if not value:
        return None

    try:
        dt = datetime.fromisoformat(value)
    except Exception:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def _to_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def load_events(path):
    file_path = Path(path)
    if not file_path.exists():
        return []

    events = []
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            events.append(event)

    return events


def filter_events(events, days, min_confidence, include_tags):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    include_tags = set(include_tags or [])

    selected = []

    for event in events:
        ts = _parse_ts(event.get("timestamp"))
        if ts is None or ts < cutoff:
            continue

        verdict = (event.get("verdict") or "UNVERIFIED").upper()
        confidence = _to_float(event.get("confidence"), 0.0)
        taxonomy = event.get("taxonomy") or {}
        tags = set(taxonomy.get("tags") or [])
        hard_case = bool(taxonomy.get("hard_case"))

        if confidence >= min_confidence and not hard_case and verdict != "UNVERIFIED":
            continue

        if include_tags and not (tags & include_tags):
            continue

        selected.append(event)

    selected.sort(key=lambda e: _to_float(e.get("confidence"), 0.0))
    return selected


def export_csv(events, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "timestamp",
                "claim",
                "normalized_claim",
                "verdict",
                "confidence",
                "tags",
                "hard_case",
                "source_diversity",
                "retrieved_count",
                "relevant_count",
                "verification_count",
            ],
        )
        writer.writeheader()

        for event in events:
            taxonomy = event.get("taxonomy") or {}
            writer.writerow(
                {
                    "timestamp": event.get("timestamp"),
                    "claim": event.get("claim"),
                    "normalized_claim": event.get("normalized_claim"),
                    "verdict": event.get("verdict"),
                    "confidence": event.get("confidence"),
                    "tags": "|".join(taxonomy.get("tags") or []),
                    "hard_case": taxonomy.get("hard_case"),
                    "source_diversity": taxonomy.get("source_diversity"),
                    "retrieved_count": event.get("retrieved_count"),
                    "relevant_count": event.get("relevant_count"),
                    "verification_count": event.get("verification_count"),
                }
            )


def main():
    parser = argparse.ArgumentParser(description="Export hard cases from verification audit logs.")
    parser.add_argument("--log-file", default="logs/verification_audit.jsonl", help="Path to audit log JSONL")
    parser.add_argument("--days", type=int, default=14, help="Lookback window in days")
    parser.add_argument("--min-confidence", type=float, default=0.7, help="Keep rows below this confidence unless hard_case")
    parser.add_argument("--tag", action="append", default=[], help="Optional taxonomy tag filter (can be repeated)")
    parser.add_argument("--limit", type=int, default=300, help="Maximum rows to export")
    parser.add_argument("--output", default="logs/hard_cases.csv", help="CSV output path")
    args = parser.parse_args()

    events = load_events(args.log_file)
    selected = filter_events(
        events=events,
        days=args.days,
        min_confidence=args.min_confidence,
        include_tags=args.tag,
    )

    selected = selected[: max(1, args.limit)]
    export_csv(selected, args.output)

    print(f"Exported hard cases: {len(selected)}")
    print(f"Output file: {args.output}")


if __name__ == "__main__":
    main()
