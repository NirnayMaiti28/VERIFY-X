import argparse
import os
from pathlib import Path

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import tensorflow as tf

from data_preprocessing import CLASS_NAMES, IMG_SIZE, VALID_EXTENSIONS, get_preprocess_fn
from model_loading import load_keras_model


def parse_args():
    parser = argparse.ArgumentParser(
        description="Predict whether a single image is fake or real."
    )
    parser.add_argument(
        "--image",
        help="Path to the image. If omitted, a file picker will open.",
    )
    parser.add_argument(
        "--model",
        default="efficientnetb0",
        choices=["mobilenetv2", "resnet50", "efficientnetb0"],
        help="Backbone used when training the saved model.",
    )
    parser.add_argument(
        "--model-path",
        help="Path to the saved .keras model. Defaults to <model>_fake_detector.keras.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.10,
        help="Threshold above which the image is predicted as real.",
    )
    return parser.parse_args()


def choose_image_file():
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as exc:
        raise RuntimeError("tkinter is not available. Pass the image path with --image.") from exc

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    file_path = filedialog.askopenfilename(
        title="Select an image to classify",
        filetypes=[
            ("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.webp"),
            ("All files", "*.*"),
        ],
    )
    root.destroy()

    if not file_path:
        raise ValueError("No image was selected.")

    return file_path


def validate_image_path(image_path):
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image file not found: {path}")

    if path.suffix.lower() not in VALID_EXTENSIONS:
        raise ValueError(
            f"Unsupported image extension '{path.suffix}'. "
            f"Use one of: {', '.join(sorted(VALID_EXTENSIONS))}."
        )

    return path


def load_and_prepare_image(image_path, model_name):
    image = tf.keras.utils.load_img(image_path, target_size=(IMG_SIZE, IMG_SIZE))
    image_array = tf.keras.utils.img_to_array(image)
    image_array = tf.expand_dims(image_array, axis=0)
    preprocess_fn = get_preprocess_fn(model_name)
    return preprocess_fn(image_array)


def main():
    args = parse_args()

    image_path = args.image if args.image else choose_image_file()
    image_path = validate_image_path(image_path)

    model_path = Path(args.model_path or f"{args.model}_fake_detector.keras")
    if not model_path.is_file():
        raise FileNotFoundError(
            f"Saved model not found: {model_path}. Train the model first or pass --model-path."
        )

    model = load_keras_model(model_path)
    image_batch = load_and_prepare_image(str(image_path), args.model)

    real_score = float(model.predict(image_batch, verbose=0)[0][0])
    fake_score = 1.0 - real_score

    predicted_index = 1 if real_score >= args.threshold else 0
    predicted_label = CLASS_NAMES[predicted_index]
    confidence = real_score if predicted_index == 1 else fake_score
    uncertainty = abs(real_score - args.threshold)

    print(f"Image: {image_path}")
    print(f"Model: {model_path}")
    print(f"Threshold: {args.threshold:.2f}")
    print(f"Prediction: {predicted_label.upper()}")
    print(f"Confidence: {confidence:.4f}")
    print(f"Fake probability: {fake_score:.4f}")
    print(f"Real probability: {real_score:.4f}")
    if uncertainty <= 0.10:
        print("Note: this prediction is close to the threshold, so treat it as uncertain.")


if __name__ == "__main__":
    main()
