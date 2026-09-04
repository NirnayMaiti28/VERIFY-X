"""
VERIFY-X 2.0 — Language Detection Service

Automatically detects the language of input text.
Supports: English, Hindi, Bengali, code-mixed, unknown.
"""

from __future__ import annotations

import re

from app.schemas.verification import Language
from app.utils.text import is_bengali_script, is_devanagari


class LanguageService:
    """Detects the language of input text."""

    # Devanagari Unicode range: U+0900 – U+097F
    # Bengali Unicode range: U+0980 – U+09FF

    def detect(self, text: str) -> Language:
        """Detect the language of the given text.
        
        Strategy:
        1. Check for Bengali script characters
        2. Check for Devanagari script characters
        3. Check for code-mixing (both Latin + Devanagari/Bengali)
        4. Try langdetect library as fallback
        5. Default to English if primarily Latin characters
        """
        if not text or len(text.strip()) < 3:
            return Language.UNKNOWN

        has_devanagari = is_devanagari(text)
        has_bengali = is_bengali_script(text)
        has_latin = bool(re.search(r'[a-zA-Z]', text))

        # Calculate script proportions
        total_alpha = 0
        devanagari_count = 0
        bengali_count = 0
        latin_count = 0

        for char in text:
            if '\u0900' <= char <= '\u097F':
                devanagari_count += 1
                total_alpha += 1
            elif '\u0980' <= char <= '\u09FF':
                bengali_count += 1
                total_alpha += 1
            elif char.isalpha() and char.isascii():
                latin_count += 1
                total_alpha += 1

        if total_alpha == 0:
            return Language.UNKNOWN

        devanagari_ratio = devanagari_count / total_alpha
        bengali_ratio = bengali_count / total_alpha
        latin_ratio = latin_count / total_alpha

        # Code-mixed: significant presence of both Latin and Indic scripts
        if has_latin and (has_devanagari or has_bengali):
            indic_ratio = devanagari_ratio + bengali_ratio
            if 0.15 < indic_ratio < 0.85 and 0.15 < latin_ratio < 0.85:
                return Language.CODE_MIXED

        # Predominantly Bengali
        if bengali_ratio > 0.5:
            return Language.BENGALI

        # Predominantly Hindi (Devanagari)
        if devanagari_ratio > 0.5:
            return Language.HINDI

        # Try langdetect for Latin-script text
        if latin_ratio > 0.7:
            try:
                from langdetect import detect as ld_detect
                detected = ld_detect(text)
                if detected == 'hi':
                    return Language.HINDI
                elif detected == 'bn':
                    return Language.BENGALI
                elif detected in ('en', 'en-US', 'en-GB'):
                    return Language.ENGLISH
            except Exception:
                pass
            # Default Latin script to English
            return Language.ENGLISH

        # Fallback
        if has_devanagari:
            return Language.HINDI
        if has_bengali:
            return Language.BENGALI
        if has_latin:
            return Language.ENGLISH

        return Language.UNKNOWN

    def detect_batch(self, texts: list[str]) -> list[Language]:
        """Detect languages for a batch of texts."""
        return [self.detect(text) for text in texts]
