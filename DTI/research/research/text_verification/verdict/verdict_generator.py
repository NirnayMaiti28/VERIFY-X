import json
import logging
import os
import re
import time

import requests
from requests.exceptions import ReadTimeout


class VerdictGenerator:

    OLLAMA_URL = "http://localhost:11434/api/generate"

    def __init__(self):
        self.model_name = os.getenv("OLLAMA_MODEL", "mistral")
        configured_models = os.getenv("OLLAMA_MODELS", "").strip()
        if configured_models:
            self.model_candidates = [m.strip() for m in configured_models.split(",") if m.strip()]
        else:
            self.model_candidates = [self.model_name, "tinyllama"]
        self.logger = logging.getLogger(__name__)

    def _normalize_verdict(self, label):
        value = (label or "").strip().lower()

        if value in {"true", "support", "supports", "supported"}:
            return "True"
        if value in {"false", "refute", "refutes", "refuted"}:
            return "False"
        if value in {"misleading", "mixed", "conflicting", "partially true", "partly true"}:
            return "Misleading"

        return "Not Enough Information"

    def _map_confidence(self, confidence_text):
        token = (confidence_text or "").strip().lower()

        if "high" in token:
            return 0.9
        if "medium" in token:
            return 0.7
        if "low" in token:
            return 0.5

        # Parse numeric values if model outputs numeric confidence.
        match = re.search(r"(\d+(?:\.\d+)?)", token)
        if match:
            value = float(match.group(1))
            if value > 1:
                value = value / 100.0
            if value >= 0.85:
                return 0.9
            if value >= 0.6:
                return 0.7
            return 0.5

        return 0.5

    def _parse_conflicting_sources(self, text):
        token = (text or "").strip().lower()
        explicit_conflict_markers = {
            "explicit contradiction",
            "explicitly contradictory",
            "sources contradict",
            "direct contradiction",
            "conflicting reports",
        }
        if any(marker in token for marker in explicit_conflict_markers):
            return True
        if token.startswith("yes") and "contradict" in token:
            return True
        if token.startswith("no") or token in {"false", "0", "none", "no"}:
            return False
        return False

    def _shorten_text(self, text, max_sentences=2, max_chars=320):
        cleaned = re.sub(r"\s+", " ", (text or "")).strip()
        if not cleaned:
            return ""

        pieces = [p.strip() for p in re.split(r"(?<=[.!?])\s+", cleaned) if p.strip()]
        if pieces:
            short = " ".join(pieces[:max_sentences])
        else:
            short = cleaned

        if len(short) > max_chars:
            short = short[: max_chars - 3].rstrip() + "..."

        return short

    def _sanitize_summary(self, summary_text, fallback_text):
        # Keep summary concise: at most 2-3 lines, factual text only.
        base = (summary_text or "").strip()
        if not base:
            base = self._shorten_text(fallback_text, max_sentences=2, max_chars=320)

        lines = [re.sub(r"\s+", " ", line).strip() for line in base.splitlines() if line.strip()]
        if not lines and base:
            lines = [re.sub(r"\s+", " ", base).strip()]

        if len(lines) > 3:
            lines = lines[:3]

        summary = "\n".join(lines)

        # If model returns one long paragraph, split into short sentence lines.
        if "\n" not in summary and len(summary) > 360:
            parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", summary) if p.strip()]
            if parts:
                summary = "\n".join(parts[:3])

        if len(summary) > 600:
            summary = summary[:597].rstrip() + "..."

        return summary or (fallback_text or "").strip()

    def _source_to_prompt_line(self, item, idx):
        title = (item.get("title") or "").strip()
        source = (item.get("source") or "Unknown").strip()
        credibility = (item.get("credibility") or "Low").strip()
        published = (item.get("published_at") or "").strip()
        url = (item.get("url") or "").strip()
        text = (item.get("content") or item.get("description") or "").strip()
        text = re.sub(r"\s+", " ", text)
        if len(text) > 250:
            text = text[:250]

        return (
            f"[{idx}] Title: {title} | Source: {source} | Credibility: {credibility} "
            f"| Published: {published} | URL: {url} | Text: {text}"
        )

    def _direct_claim_prompt(self, claim):
        return (
            "You are a strict fact-checker.\n"
            "Classify the claim into exactly one verdict: TRUE, FALSE, or UNSURE.\n"
            "If uncertain, use UNSURE.\n"
            "Return JSON only with this schema:\n"
            "{\n"
            "  \"verdict\": \"TRUE|FALSE|UNSURE\",\n"
            "  \"confidence\": 0.0-1.0,\n"
            "  \"reason\": \"one short sentence\"\n"
            "}\n\n"
            f"Claim: {claim}\n"
        )

    def generate_direct_claim(self, claim):
        try:
            num_gpu = int(os.getenv("OLLAMA_NUM_GPU", "0"))
        except ValueError:
            num_gpu = 0

        raw = ""
        model_used = ""
        last_exc = None
        for candidate in self.model_candidates:
            payload = {
                "model": candidate,
                "prompt": self._direct_claim_prompt(claim),
                "stream": False,
                "options": {"num_gpu": num_gpu},
            }
            try:
                response = requests.post(self.OLLAMA_URL, json=payload, timeout=120)
                response.raise_for_status()
                raw = (response.json().get("response") or "").strip()
                model_used = candidate
                break
            except Exception as exc:
                last_exc = exc
                continue

        if not model_used:
            raise RuntimeError(f"No Ollama model succeeded: {type(last_exc).__name__ if last_exc else 'unknown'}")

        verdict = "UNSURE"
        confidence = 0.5
        reason = "Model was uncertain."

        json_match = re.search(r"\{[\s\S]*\}", raw)
        if json_match:
            try:
                obj = json.loads(json_match.group(0))
                verdict = str(obj.get("verdict", "UNSURE")).strip().upper()
                if verdict not in {"TRUE", "FALSE", "UNSURE"}:
                    verdict = "UNSURE"
                value = obj.get("confidence", 0.5)
                try:
                    confidence = float(value)
                except (TypeError, ValueError):
                    confidence = 0.5
                confidence = max(0.0, min(1.0, confidence))
                reason = str(obj.get("reason") or reason)
            except Exception:
                pass
        else:
            lower = raw.lower()
            if "false" in lower:
                verdict = "FALSE"
            elif "true" in lower:
                verdict = "TRUE"

        return {
            "claim": claim,
            "verdict": verdict,
            "confidence": confidence,
            "reason": reason,
            "model_used": model_used,
            "ollama_response_raw": raw,
        }

    def _build_sources_prompt(self, sources):
        return "\n".join(
            self._source_to_prompt_line(item, idx)
            for idx, item in enumerate((sources or [])[:3], start=1)
        )

    def call_ollama_verifier(self, claim, sources, agreement_summary, credibility_summary):
        try:
            num_gpu = int(os.getenv("OLLAMA_NUM_GPU", "0"))
        except ValueError:
            num_gpu = 0

        prompt = (
            "You are a fact-checking AI.\n\n"
            f"Claim:\n{claim}\n\n"
            f"Sources:\n{sources}\n\n"
            f"Summary:\n{agreement_summary}\n\n"
            "Instructions:\n"
            "- Use only the sources\n"
            "- If sources agree -> decide accordingly\n"
            "- If unclear -> Not Enough Information\n"
            "- If multiple sources describe the same event differently, treat them as agreement\n"
            "- Do not be overly conservative\n"
            "- Detect negation carefully (e.g., 'not', 'myth', 'false')\n"
            "- If sources explicitly deny the claim, treat them as refuting evidence\n"
            "- Do not treat mentions of a claim as support unless they affirm it\n"
            "- Only mark conflicting sources if there is explicit contradiction\n"
            "- Do not guess\n\n"
            "- Provide a concise 2-3 line summary of the claim based ONLY on the sources\n"
            "- The summary should be factual and neutral\n"
            "- Do NOT repeat the explanation\n"
            "- Do NOT guess if information is insufficient\n\n"
            "Output:\n"
            "Verdict:\n"
            "Explanation:\n"
            "Summary:\n"
            "Confidence:\n"
            "Conflicting Sources:\n"
        )

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"num_gpu": num_gpu},
        }

        self.logger.debug(
            "ollama_request_start model=%s prompt_length=%d num_sources=%d",
            self.model_name,
            len(prompt),
            len((sources or "").splitlines()),
        )

        last_exc = None
        for attempt in range(3):
            started = time.perf_counter()
            try:
                response = requests.post(self.OLLAMA_URL, json=payload, timeout=120)
                response.raise_for_status()
                elapsed = time.perf_counter() - started
                self.logger.debug(
                    "ollama_request_success attempt=%d response_time_seconds=%.3f",
                    attempt + 1,
                    elapsed,
                )
                data = response.json()
                return data.get("response", "")
            except ReadTimeout as exc:
                elapsed = time.perf_counter() - started
                self.logger.warning(
                    "ollama_timeout attempt=%d response_time_seconds=%.3f",
                    attempt + 1,
                    elapsed,
                )
                last_exc = exc
                if attempt < 2:
                    continue
                raise
            except Exception as exc:
                elapsed = time.perf_counter() - started
                self.logger.warning(
                    "ollama_request_failed attempt=%d response_time_seconds=%.3f error=%s",
                    attempt + 1,
                    elapsed,
                    type(exc).__name__,
                )
                raise

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Ollama request failed")

    def _parse_ollama_output(self, raw_text):
        text = (raw_text or "").strip()
        if not text:
            return {
                "verdict": "Not Enough Information",
                "confidence": 0.5,
                "explanation": "Ollama returned an empty response.",
                "summary": "Ollama returned an empty response.",
                "conflicting_sources": False,
            }

        verdict = ""
        explanation = ""
        summary = ""
        confidence_text = ""
        conflicting_text = ""

        verdict_match = re.search(r"verdict\s*:\s*(.+)", text, flags=re.IGNORECASE)
        explanation_match = re.search(
            r"explanation\s*:\s*(.+?)(?:\n\s*summary\s*:|\n\s*confidence\s*:|\n\s*conflicting\s*sources\s*:|$)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        summary_match = re.search(
            r"summary\s*:\s*(.+?)(?:\n\s*confidence\s*:|\n\s*conflicting\s*sources\s*:|$)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        confidence_match = re.search(r"confidence\s*:\s*(.+)", text, flags=re.IGNORECASE)
        conflicting_match = re.search(r"conflicting\s*sources\s*:\s*(.+)", text, flags=re.IGNORECASE)

        if verdict_match:
            verdict = verdict_match.group(1).strip()
        if explanation_match:
            explanation = re.sub(r"\s+", " ", explanation_match.group(1)).strip()
        if summary_match:
            summary = summary_match.group(1).strip()
        if confidence_match:
            confidence_text = confidence_match.group(1).strip()
        if conflicting_match:
            conflicting_text = conflicting_match.group(1).strip()

        # JSON fallback parser.
        if not verdict:
            json_match = re.search(r"\{[\s\S]*\}", text)
            if json_match:
                try:
                    obj = json.loads(json_match.group(0))
                    verdict = str(obj.get("verdict") or obj.get("Verdict") or "")
                    explanation = str(obj.get("explanation") or obj.get("Explanation") or explanation)
                    summary = str(obj.get("summary") or obj.get("Summary") or summary)
                    confidence_text = str(obj.get("confidence") or obj.get("Confidence") or confidence_text)
                    conflicting_text = str(
                        obj.get("conflicting_sources")
                        or obj.get("Conflicting Sources")
                        or obj.get("conflicting")
                        or conflicting_text
                    )
                except Exception:
                    pass

        normalized = self._normalize_verdict(verdict)
        confidence = self._map_confidence(confidence_text)

        if not explanation:
            explanation = "The provided sources were insufficient for a stronger determination."

        summary = self._sanitize_summary(summary, explanation)

        return {
            "verdict": normalized,
            "confidence": confidence,
            "explanation": explanation,
            "summary": summary,
            "conflicting_sources": self._parse_conflicting_sources(conflicting_text),
        }

    def generate(self, claim, sources, agreement_summary, credibility_summary):
        limited_sources = (sources or [])[:3]

        if not limited_sources:
            return {
                "claim": claim,
                "verdict": "Not Enough Information",
                "confidence": 0.5,
                "summary": "No sources were available for verification.",
                "explanation": "No sources were available for verification.",
                "conflicting_sources": False,
                "sources": [],
                "ollama_response_raw": "",
            }

        prompt_sources = self._build_sources_prompt(limited_sources)

        try:
            raw = self.call_ollama_verifier(
                claim=claim,
                sources=prompt_sources,
                agreement_summary=agreement_summary,
                credibility_summary=credibility_summary,
            )
            parsed = self._parse_ollama_output(raw)
            return {
                "claim": claim,
                "verdict": parsed["verdict"],
                "confidence": parsed["confidence"],
                "summary": parsed["summary"],
                "explanation": parsed["explanation"],
                "conflicting_sources": parsed["conflicting_sources"],
                "sources": limited_sources,
                "ollama_response_raw": raw,
            }
        except Exception as exc:
            return {
                "claim": claim,
                "verdict": "Not Enough Information",
                "confidence": 0.5,
                "summary": f"Ollama verification failed: {type(exc).__name__}.",
                "explanation": f"Ollama verification failed: {type(exc).__name__}.",
                "conflicting_sources": False,
                "sources": limited_sources,
                "ollama_response_raw": "",
            }


__all__ = ["VerdictGenerator"]
