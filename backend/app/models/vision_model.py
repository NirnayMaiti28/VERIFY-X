"""
VERIFY-X 2.0 — Vision Model Inference Service

Handles inference for multimodal verification using Qwen2.5-VL-7B-Instruct.
Processes images via OCR and Visual Language Modeling.
"""

from __future__ import annotations

import asyncio
import io
import json

import torch
from PIL import Image

from app.config import ModelMode, get_settings
from app.schemas.verification import VerdictEnum
from app.utils.logging import get_logger

logger = get_logger("models.vision")


class VisionModelInterface:
    """Interface for the multimodal vision verification model."""

    def __init__(self):
        self.settings = get_settings()
        self.mode = self.settings.model_mode
        self._model = None
        self._processor = None
        self._ocr_engine = None
        self._is_loaded = False

    def load_model(self):
        """Lazy load the vision model, processor, and OCR engine."""
        if self._is_loaded:
            return

        if self.mode.value == "mock":
            logger.info("vision_model_mock_mode", message="Using mock vision model")
            self._is_loaded = True
            return

        if not torch.cuda.is_available():
            logger.warning("cuda_not_available_fallback", message="CUDA is not available. Falling back to MOCK engine for vision model.")
            self.mode = ModelMode.MOCK
            self._is_loaded = True
            return

        try:
            logger.info("vision_model_loading", mode=self.mode.value, base=self.settings.vision_base_model)
            from transformers import (
                AutoProcessor,
                BitsAndBytesConfig,
                Qwen2VLForConditionalGeneration,
            )
            
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
            )
            
            self._model = Qwen2VLForConditionalGeneration.from_pretrained(
                self.settings.vision_base_model,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True
            )
            self._processor = AutoProcessor.from_pretrained(
                self.settings.vision_base_model,
                trust_remote_code=True
            )
            self._model.eval()
            self._is_loaded = True
            logger.info("vision_model_loaded_successfully")
        except Exception as e:
            logger.error("vision_model_load_failed", error=str(e))
            self.mode = ModelMode.MOCK
            self._is_loaded = True

    async def extract_text(self, image_bytes: bytes) -> str:
        """Extract text from image using the VLM."""
        self.load_model()
        
        if self.mode.value == "mock":
            return "Extracted mock text from image: Breaking News - Major Event Occurs."
            
        prompt = "Extract all readable text from this image precisely as it appears."
        return await asyncio.to_thread(self._run_inference, image_bytes, prompt, max_tokens=256)

    async def predict(
        self, 
        image_bytes: bytes, 
        context: str | None = None,
        extracted_text: str | None = None
    ) -> dict:
        """Analyze image and verify claims within it."""
        self.load_model()
        
        if self.mode.value == "mock":
            return self._mock_predict()
            
        logger.info("vision_model_predict_start", has_context=bool(context))
        
        prompt = "Analyze this image and verify if it supports the provided context or contains misinformation.\n"
        if context:
            prompt += f"CONTEXT: {context}\n"
        prompt += "Determine the veracity. Return a JSON with 'verdict', 'confidence', 'reasoning', and 'detected_manipulation' (boolean)."
        
        response_text = await asyncio.to_thread(self._run_inference, image_bytes, prompt, max_tokens=512)
        
        json_str = response_text
        start_idx = json_str.find("{")
        end_idx = json_str.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = json_str[start_idx:end_idx+1]
            
        try:
            result = json.loads(json_str)
            return {
                "verdict": VerdictEnum(result.get("verdict", "NOT_ENOUGH_INFORMATION")),
                "confidence": float(result.get("confidence", 0.0)),
                "reasoning": result.get("reasoning", "No reasoning parsed"),
                "extracted_text": extracted_text,
                "detected_manipulation": bool(result.get("detected_manipulation", False)),
            }
        except Exception as e:
            logger.error("vision_model_json_parse_failed", error=str(e), raw_text=response_text)
            return {
                "verdict": VerdictEnum.NOT_ENOUGH_INFORMATION,
                "confidence": 0.0,
                "reasoning": "Visual analysis failed to produce structured output.",
                "extracted_text": extracted_text,
                "detected_manipulation": False,
            }

    def _run_inference(self, image_bytes: bytes, prompt: str, max_tokens: int) -> str:
        """Synchronous inference function for the vision model."""
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            
            # Use transformers' standard text + image processing
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
            
            text = self._processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = self._processor(text=[text], images=[image], return_tensors="pt").to(self._model.device)
            
            with torch.no_grad():
                generated_ids = self._model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=0.1
                )
                
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            response = self._processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True)[0]
            return response
        except Exception as e:
            logger.error("vision_inference_failed", error=str(e))
            return "{}"
        
    def _mock_predict(self) -> dict:
        """Mock prediction for testing."""
        import random
        
        verdicts = [VerdictEnum.MISLEADING, VerdictEnum.FALSE, VerdictEnum.PARTIALLY_TRUE]
        verdict = random.choice(verdicts)
        confidence = random.uniform(0.7, 0.92)
        
        return {
            "verdict": verdict,
            "confidence": confidence,
            "reasoning": f"Visual analysis indicates the image context is {verdict.value.replace('_', ' ')}.",
            "extracted_text": "Mock extracted text",
            "detected_manipulation": random.choice([True, False, False]),
        }
