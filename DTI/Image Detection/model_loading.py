from contextlib import contextmanager
from pathlib import Path

import tensorflow as tf


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


def load_keras_model(model_path):
    model_path = Path(model_path)

    try:
        return tf.keras.models.load_model(model_path)
    except (TypeError, ValueError) as exc:
        if model_path.suffix != ".keras" or "quantization_config" not in str(exc):
            raise

    with _patch_dense_from_config():
        return tf.keras.models.load_model(model_path)
