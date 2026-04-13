import argparse
import os
from pathlib import Path

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import numpy as np
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix, f1_score

from data_preprocessing import get_datasets
from model_loading import load_keras_model
from visualization_utils import save_confusion_matrix


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate an image manipulation detector.")
    parser.add_argument(
        "--model",
        default="mobilenetv2",
        choices=["mobilenetv2", "resnet50", "efficientnetb0"],
        help="Model backbone used during training.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Classification threshold for the sigmoid output.",
    )
    parser.add_argument(
        "--auto-threshold",
        action="store_true",
        help="Search thresholds from 0.10 to 0.90 and use the best F1 score.",
    )
    parser.add_argument(
        "--plots-dir",
        default="plots",
        help="Directory where evaluation plots will be saved.",
    )
    parser.add_argument(
        "--model-path",
        help="Path to a saved .keras model. Defaults to <model>_fake_detector.keras.",
    )
    return parser.parse_args()


def find_best_threshold(y_true, y_scores):
    best_threshold = 0.5
    best_f1 = -1.0

    for threshold in np.arange(0.10, 0.91, 0.05):
        predictions = (y_scores >= threshold).astype(int)
        score = f1_score(y_true, predictions, average="macro", zero_division=0)
        if score > best_f1:
            best_f1 = score
            best_threshold = float(threshold)

    return best_threshold, best_f1


def main():
    args = parse_args()

    _, _, test_dataset, _, class_names = get_datasets(args.model)
    model_path = Path(args.model_path or f"{args.model}_fake_detector.keras")
    if not model_path.is_file():
        raise FileNotFoundError(
            f"Saved model not found: {model_path}. Pass --model-path or place the file in the project root."
        )
    model = load_keras_model(model_path)

    y_true = []
    y_pred = []
    y_scores = []

    for images, labels in test_dataset:
        predictions = model.predict(images, verbose=0)
        binary_predictions = (predictions >= args.threshold).astype(int)

        y_true.extend(labels.numpy().astype(int).flatten())
        y_pred.extend(binary_predictions.flatten())
        y_scores.extend(predictions.flatten())

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    y_scores = np.array(y_scores)

    if args.auto_threshold:
        best_threshold, best_f1 = find_best_threshold(y_true, y_scores)
        print(f"Best threshold by F1: {best_threshold:.2f} (F1: {best_f1:.4f})")
        args.threshold = best_threshold
        y_pred = (y_scores >= args.threshold).astype(int)

    cm = confusion_matrix(y_true, y_pred)
    cm_path = save_confusion_matrix(cm, class_names, args.plots_dir, args.model)

    print(f"Model path: {model_path}")
    print(f"Class mapping: 0 -> {class_names[0]}, 1 -> {class_names[1]}")
    print("Confusion Matrix:")
    print(cm)
    print(f"Confusion matrix plot saved to {cm_path}")
    print(f"\nThreshold used: {args.threshold:.2f}")

    metric_values = model.evaluate(test_dataset, verbose=0)
    print("\nTest metrics:")
    for metric_name, metric_value in zip(model.metrics_names, metric_values):
        print(f"{metric_name}: {metric_value:.4f}")
    print(f"Average confidence: {y_scores.mean():.4f}")
    print(f"Predicted real count: {int(y_pred.sum())}")
    print(f"Predicted fake count: {int((1 - y_pred).sum())}")

    print("\nClassification Report:")
    print(classification_report(y_true, y_pred, target_names=class_names, zero_division=0))


if __name__ == "__main__":
    main()
