import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _parse_timestamp(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def load_events(log_file):
    path = Path(log_file)

    if not path.exists():
        return []

    events = []

    with path.open("r", encoding="utf-8") as f:
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


def filter_recent(events, days=7):
    if days <= 0:
        return events

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    filtered = []

    for event in events:
        timestamp = _parse_timestamp(event.get("timestamp"))
        if timestamp is None:
            continue

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        if timestamp >= cutoff:
            filtered.append(event)

    return filtered


def summarize_events(events):
    summary = {
        "total_events": len(events),
        "hard_cases": 0,
        "hard_case_rate": 0.0,
        "verdict_counts": Counter(),
        "taxonomy_tag_counts": Counter(),
        "low_diversity_cases": 0,
        "confidence_bands": {
            "lt_0_50": 0,
            "0_50_to_0_70": 0,
            "0_70_to_0_85": 0,
            "gte_0_85": 0,
        },
    }

    for event in events:
        verdict = (event.get("verdict") or "UNKNOWN").upper()
        confidence = _safe_float(event.get("confidence"), default=0.0)
        taxonomy = event.get("taxonomy") or {}
        tags = taxonomy.get("tags") or []
        hard_case = bool(taxonomy.get("hard_case"))
        source_diversity = int(taxonomy.get("source_diversity") or 0)

        summary["verdict_counts"][verdict] += 1

        if hard_case:
            summary["hard_cases"] += 1

        if source_diversity < 2:
            summary["low_diversity_cases"] += 1

        for tag in tags:
            summary["taxonomy_tag_counts"][tag] += 1

        if confidence < 0.5:
            summary["confidence_bands"]["lt_0_50"] += 1
        elif confidence < 0.7:
            summary["confidence_bands"]["0_50_to_0_70"] += 1
        elif confidence < 0.85:
            summary["confidence_bands"]["0_70_to_0_85"] += 1
        else:
            summary["confidence_bands"]["gte_0_85"] += 1

    total = summary["total_events"]
    if total > 0:
        summary["hard_case_rate"] = round(summary["hard_cases"] / total, 4)

    summary["verdict_counts"] = dict(summary["verdict_counts"])
    summary["taxonomy_tag_counts"] = dict(summary["taxonomy_tag_counts"].most_common())

    return summary


def format_markdown_report(summary, days, log_path):
    total = summary["total_events"]
    hard_cases = summary["hard_cases"]
    hard_rate_pct = round(summary["hard_case_rate"] * 100, 2)
    low_div = summary["low_diversity_cases"]

    lines = []
    lines.append("# Verification Failure Report")
    lines.append("")
    lines.append(f"- Window: last {days} days")
    lines.append(f"- Log file: {log_path}")
    lines.append(f"- Total cases: {total}")
    lines.append(f"- Hard cases: {hard_cases} ({hard_rate_pct}%)")
    lines.append(f"- Low source diversity (<2 sources): {low_div}")
    lines.append("")

    lines.append("## Verdict Distribution")
    if not summary["verdict_counts"]:
        lines.append("- No data")
    else:
        for verdict, count in sorted(summary["verdict_counts"].items(), key=lambda x: x[1], reverse=True):
            lines.append(f"- {verdict}: {count}")
    lines.append("")

    lines.append("## Top Failure Tags")
    if not summary["taxonomy_tag_counts"]:
        lines.append("- No taxonomy tags")
    else:
        top_tags = list(summary["taxonomy_tag_counts"].items())[:10]
        for tag, count in top_tags:
            lines.append(f"- {tag}: {count}")
    lines.append("")

    lines.append("## Confidence Bands")
    for band, count in summary["confidence_bands"].items():
        lines.append(f"- {band}: {count}")

    return "\n".join(lines) + "\n"


def write_report(report_text, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        f.write(report_text)


def main():
    parser = argparse.ArgumentParser(description="Generate weekly failure report from verification audit logs.")
    parser.add_argument("--log-file", default="logs/verification_audit.jsonl", help="Path to JSONL audit log file")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days")
    parser.add_argument("--output", default="logs/weekly_failure_report.md", help="Output markdown report path")
    parser.add_argument("--json-output", default="", help="Optional path to write summary JSON")
    args = parser.parse_args()

    events = load_events(args.log_file)
    recent_events = filter_recent(events, days=args.days)
    summary = summarize_events(recent_events)
    report_text = format_markdown_report(summary, args.days, args.log_file)

    write_report(report_text, args.output)

    if args.json_output:
        write_report(json.dumps(summary, indent=2), args.json_output)

    print(f"Report written: {args.output}")
    print(f"Cases analyzed: {summary['total_events']}")
    print(f"Hard-case rate: {round(summary['hard_case_rate'] * 100, 2)}%")


if __name__ == "__main__":
    main()
