"""
VERIFY-X 2.0 — Text Model Inference Service

Handles inference using the fine-tuned Qwen3-8B model via HuggingFace Transformers.
Supports loading quantized models with LoRA adapters.
"""

from __future__ import annotations

import asyncio
import json

import torch

from app.config import ModelMode, get_settings
from app.schemas.evidence import EvidenceItem
from app.schemas.verification import VerdictEnum
from app.utils.logging import get_logger

logger = get_logger("models.text")


class TextModelInterface:
    """Interface for the fine-tuned text verification model."""

    def __init__(self):
        self.settings = get_settings()
        self.mode = self.settings.model_mode
        self._model = None
        self._tokenizer = None
        self._is_loaded = False

    def load_model(self):
        """Lazy load the model and tokenizer based on configuration."""
        if self._is_loaded:
            return

        if self.mode.value == "mock":
            logger.info("text_model_mock_mode", message="Using mock text model")
            self._is_loaded = True
            return

        if not torch.cuda.is_available():
            logger.warning("cuda_not_available_fallback", message="CUDA is not available. Falling back to MOCK engine for text model.")
            self.mode = ModelMode.MOCK
            self._is_loaded = True
            return

        try:
            logger.info("text_model_loading", mode=self.mode.value, base=self.settings.text_base_model)
            from peft import PeftModel
            from transformers import (
                AutoModelForCausalLM,
                AutoTokenizer,
                BitsAndBytesConfig,
            )
            
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.settings.text_base_model, 
                trust_remote_code=True,
                padding_side="left"
            )
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
                
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
            )
            
            base_model = AutoModelForCausalLM.from_pretrained(
                self.settings.text_base_model,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
            )
            
            if self.settings.text_adapter:
                logger.info("text_model_loading_adapter", adapter=self.settings.text_adapter)
                self._model = PeftModel.from_pretrained(base_model, self.settings.text_adapter)
            else:
                self._model = base_model
                
            self._model.eval()
            self._is_loaded = True
            logger.info("text_model_loaded_successfully")
        except Exception as e:
            logger.error("text_model_load_failed", error=str(e))
            # Fallback to mock on catastrophic failure
            self.mode = ModelMode.MOCK
            self._is_loaded = True

    def _build_prompt(self, claim: str, evidence: list[EvidenceItem]) -> str:
        """Build the structured prompt perfectly matching training template."""
        system_prompt = "You are a fact verification model."
        
        evidence_text = ""
        if not evidence:
            evidence_text = "[E1]\nNo reliable evidence provided.\n"
        else:
            for i, ev in enumerate(evidence):
                text = ev.passage.strip()
                evidence_text += f"[E{i+1}]\n{text}\n\n"
                
        task_prompt = "Determine the veracity of the claim.\nReturn structured JSON."
        
        prompt = (
            f"SYSTEM:\n{system_prompt}\n\n"
            f"CLAIM:\n{claim}\n\n"
            f"EVIDENCE:\n{evidence_text.strip()}\n\n"
            f"TASK:\n{task_prompt}\n"
            f"### RESPONSE:\n"
        )
        return prompt

    async def predict(self, claim: str, evidence: list[EvidenceItem]) -> dict:
        """Run inference to verify the claim against evidence."""
        self.load_model()
        
        # Build prompt
        prompt = self._build_prompt(claim, evidence)
        
        if self.mode.value == "mock":
            return self._mock_predict(claim, evidence)
            
        logger.info("text_model_predict_start", claim_length=len(claim), evidence_count=len(evidence))
        
        # Run inference in a background thread to prevent blocking FastAPI event loop
        return await asyncio.to_thread(self._run_inference, prompt)

    def _run_inference(self, prompt: str) -> dict:
        """Synchronous inference function intended for threaded execution."""
        try:
            inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
            
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=0.1,
                    top_p=0.9,
                    do_sample=False,
                    pad_token_id=self._tokenizer.pad_token_id,
                    eos_token_id=self._tokenizer.eos_token_id
                )
                
            # Decode only the generated response portion
            input_length = inputs.input_ids.shape[1]
            generated_tokens = outputs[0][input_length:]
            response_text = self._tokenizer.decode(generated_tokens, skip_special_tokens=True)
            
            # Find JSON payload
            json_str = response_text
            start_idx = json_str.find("{")
            end_idx = json_str.rfind("}")
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = json_str[start_idx:end_idx+1]
                
            try:
                result = json.loads(json_str)
                # Map raw strings back to ENUM safety if possible
                return {
                    "verdict": VerdictEnum(result.get("verdict", "NOT_ENOUGH_INFORMATION")),
                    "confidence": float(result.get("confidence", 0.0)),
                    "reasoning": result.get("reason", "No reasoning parsed"),
                    "evidence_ids": result.get("evidence_ids", [])
                }
            except json.JSONDecodeError:
                logger.error("text_model_json_parse_failed", raw_text=response_text)
                return {
                    "verdict": VerdictEnum.NOT_ENOUGH_INFORMATION,
                    "confidence": 0.0,
                    "reasoning": "Model returned malformed JSON.",
                    "evidence_ids": []
                }
        except Exception as e:
            logger.error("text_model_inference_failed", error=str(e))
            return {
                "verdict": VerdictEnum.NOT_ENOUGH_INFORMATION,
                "confidence": 0.0,
                "reasoning": "Inference engine failed."
            }
        
    def _mock_predict(self, claim: str, evidence: list[EvidenceItem]) -> dict:
        """Mock prediction for testing."""
        import random
        
        # Simple heuristic for mock
        if not evidence:
            return {
                "verdict": VerdictEnum.NOT_ENOUGH_INFORMATION,
                "confidence": 0.0,
                "reasoning": "No evidence provided."
            }
            
        verdict = random.choice(list(VerdictEnum))
        if verdict == VerdictEnum.NOT_ENOUGH_INFORMATION:
            verdict = VerdictEnum.PARTIALLY_TRUE
            
        confidence = random.uniform(0.65, 0.95)
        
        return {
            "verdict": verdict,
            "confidence": confidence,
            "reasoning": f"Based on {len(evidence)} pieces of evidence, the claim appears to be {verdict.value.replace('_', ' ')}.",
        }
