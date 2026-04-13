import os
import logging
from pathlib import Path
from io import BytesIO

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import tensorflow as tf
from PIL import Image

logger = logging.getLogger(__name__)


class ImageManipulationDetector:
    """Service for detecting fake/manipulated images using a trained EfficientNetB0 model."""

    IMG_SIZE = 224
    CLASS_NAMES = ["fake", "real"]
    VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}

    def __init__(self, model_path: str = None):
        """
        Initialize the image detector with a trained model.
        
        Args:
            model_path: Path to the .keras model file. 
                       Defaults to efficientnetb0_fake_detector.keras in Image Detection folder.
        """
        if model_path is None:
            # Default to the Image Detection folder
            base_dir = Path(__file__).parent.parent.parent.parent
            model_path = base_dir / "Image Detection" / "efficientnetb0_fake_detector.keras"
        
        self.model_path = Path(model_path)
        self.model = None
        self.preprocess_fn = None
        
        if self.model_path.exists():
            self._load_model()
        else:
            logger.warning(f"Model not found at {self.model_path}. Image detection disabled.")

    def _load_model(self):
        """Load the Keras model with quantization config patching if needed."""
        try:
            self.model = tf.keras.models.load_model(self.model_path)
            self._set_preprocess_fn()
            logger.info(f"Loaded image model from {self.model_path}")
        except (TypeError, ValueError) as exc:
            if self.model_path.suffix != ".keras" or "quantization_config" not in str(exc):
                raise
            # Patch and retry
            self._load_with_patch()

    def _load_with_patch(self):
        """Load model with quantization config patching."""
        from contextlib import contextmanager
        
        @contextmanager
        def _patch_dense_from_config():
            dense_layer = tf.keras.layers.Dense
            original_from_config = dense_layer.from_config.__func__

            def patched_from_config(cls, config):
                config = dict(config)
                config.pop("quantization_config", None)
                return original_from_config(cls, config)

            dense_layer.from_config = classmethod(patched_from_config)
            try:
                yield
            finally:
                dense_layer.from_config = classmethod(original_from_config)

        with _patch_dense_from_config():
            self.model = tf.keras.models.load_model(self.model_path)
        self._set_preprocess_fn()
        logger.info(f"Loaded image model (with patching) from {self.model_path}")

    def _set_preprocess_fn(self):
        """Set the preprocessing function based on EfficientNetB0."""
        self.preprocess_fn = tf.keras.applications.efficientnet.preprocess_input

    def _load_and_prepare_image(self, image_bytes: bytes) -> tf.Tensor:
        """
        Load image from bytes and prepare for model input.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Preprocessed image tensor ready for model inference
        """
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        image = image.resize((self.IMG_SIZE, self.IMG_SIZE))
        image_array = tf.keras.utils.img_to_array(image)
        image_array = tf.expand_dims(image_array, axis=0)
        return self.preprocess_fn(image_array)

    def predict(self, image_bytes: bytes, threshold: float = 0.5) -> dict:
        """
        Predict if an image is fake or real.
        
        Args:
            image_bytes: Raw image bytes
            threshold: Confidence threshold (default 0.5)
            
        Returns:
            dict with keys:
                - is_fake: bool (True if fake, False if real)
                - confidence: float (0.0-1.0)
                - probabilities: dict with 'fake' and 'real' probabilities
                - explanation: str
        """
        if not self.model:
            return {
                "is_fake": None,
                "confidence": 0.0,
                "probabilities": {"fake": 0.0, "real": 0.0},
                "explanation": "Image detection model not loaded.",
                "error": "Model not available"
            }

        try:
            prepared = self._load_and_prepare_image(image_bytes)
            predictions = self.model.predict(prepared, verbose=0)
            
            # predictions[0][0] = probability of "fake"
            # predictions[0][1] = probability of "real"
            fake_prob = float(predictions[0][0])
            real_prob = float(predictions[0][1])
            
            # Determine verdict based on which has higher probability
            is_fake = fake_prob > real_prob
            confidence = max(fake_prob, real_prob)
            
            return {
                "is_fake": is_fake,
                "confidence": round(confidence, 4),
                "probabilities": {
                    "fake": round(fake_prob, 4),
                    "real": round(real_prob, 4)
                },
                "explanation": (
                    f"Image detected as {'manipulated/fake' if is_fake else 'authentic/real'} "
                    f"with {confidence*100:.1f}% confidence."
                ),
                "error": None
            }
        except Exception as exc:
            logger.exception("Image prediction failed")
            return {
                "is_fake": None,
                "confidence": 0.0,
                "probabilities": {"fake": 0.0, "real": 0.0},
                "explanation": f"Image analysis failed: {type(exc).__name__}",
                "error": str(exc)
            }


# Global instance (lazy loaded)
_detector_instance = None


def get_image_detector() -> ImageManipulationDetector:
    """Get or create the global image detector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = ImageManipulationDetector()
    return _detector_instance
