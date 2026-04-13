import logging


class VerificationPipeline:

    CACHE_VERSION = "direct-ollama-v1"

    def __init__(self):
        from text_verification.claim_processing.claim_normalizer import normalize_headline_to_claim
        from text_verification.claim_processing.cleaner import ClaimCleaner
        from text_verification.utils.cache import get_cached_result, set_cached_result
        from text_verification.verdict.verdict_generator import VerdictGenerator

        self.normalize_headline = normalize_headline_to_claim
        self.cleaner = ClaimCleaner()
        self.get_cached_result = get_cached_result
        self.set_cached_result = set_cached_result
        self.verdict_generator = VerdictGenerator()
        self.logger = logging.getLogger(__name__)

    def verify_claim(self, headline):
        claim = self.normalize_headline(headline)
        if claim == "NOT_A_CLAIM":
            return {
                "claim": headline,
                "normalized_claim": headline,
                "verdict": "UNVERIFIABLE",
                "confidence": 0.5,
                "summary": "Input is not a verifiable factual claim.",
                "reason": "Input is not a verifiable factual claim.",
                "explanation": "Input is not a verifiable factual claim.",
            }

        normalized_claim = self.cleaner.clean(claim) or claim
        cached = self.get_cached_result(normalized_claim)
        if cached:
            return cached

        try:
            direct = self.verdict_generator.generate_direct_claim(normalized_claim)
            model_verdict = (direct.get("verdict") or "UNSURE").strip().upper()
            if model_verdict == "TRUE":
                final_verdict = "TRUE"
            elif model_verdict == "FALSE":
                final_verdict = "FALSE"
            else:
                final_verdict = "UNVERIFIABLE"

            result = {
                "claim": headline,
                "normalized_claim": normalized_claim,
                "verdict": final_verdict,
                "confidence": float(round(float(direct.get("confidence", 0.5) or 0.5), 4)),
                "summary": "Direct Ollama claim verification result.",
                "reason": str(direct.get("reason") or "Direct model verdict."),
                "explanation": str(direct.get("reason") or "Direct model verdict."),
            }
            self.set_cached_result(normalized_claim, result)
            return result
        except Exception as exc:
            self.logger.exception("direct_ollama_verification_failed")
            return {
                "claim": headline,
                "normalized_claim": normalized_claim,
                "verdict": "UNVERIFIABLE",
                "confidence": 0.5,
                "summary": "Direct Ollama claim verification failed.",
                "reason": f"Direct claim verification failed: {type(exc).__name__}.",
                "explanation": f"Direct claim verification failed: {type(exc).__name__}.",
            }
