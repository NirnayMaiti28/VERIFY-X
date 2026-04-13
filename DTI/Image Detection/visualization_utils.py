from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def ensure_output_dir(output_dir):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def save_training_curves(history, output_dir, model_name):
    output_path = ensure_output_dir(output_dir)
    history_dict = history.history
    epochs = range(1, len(history_dict["loss"]) + 1)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].plot(epochs, history_dict["loss"], label="Train Loss")
    axes[0].plot(epochs, history_dict["val_loss"], label="Val Loss")
    axes[0].set_title("Loss")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    metric_name = "auc" if "auc" in history_dict else "accuracy"
    val_metric_name = f"val_{metric_name}"
    axes[1].plot(epochs, history_dict[metric_name], label=f"Train {metric_name.upper()}")
    axes[1].plot(epochs, history_dict[val_metric_name], label=f"Val {metric_name.upper()}")
    axes[1].set_title(metric_name.upper())
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel(metric_name.upper())
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    fig.tight_layout()
    figure_path = output_path / f"{model_name}_training_curves.png"
    fig.savefig(figure_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return figure_path


def save_confusion_matrix(cm, class_names, output_dir, model_name):
    output_path = ensure_output_dir(output_dir)
    fig, ax = plt.subplots(figsize=(6, 5))
    image = ax.imshow(cm, cmap="Blues")
    fig.colorbar(image, ax=ax)

    ax.set_xticks(np.arange(len(class_names)))
    ax.set_yticks(np.arange(len(class_names)))
    ax.set_xticklabels(class_names)
    ax.set_yticklabels(class_names)
    ax.set_xlabel("Predicted label")
    ax.set_ylabel("True label")
    ax.set_title("Confusion Matrix")

    threshold = cm.max() / 2 if cm.size else 0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            color = "white" if cm[i, j] > threshold else "black"
            ax.text(j, i, int(cm[i, j]), ha="center", va="center", color=color)

    fig.tight_layout()
    figure_path = output_path / f"{model_name}_confusion_matrix.png"
    fig.savefig(figure_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return figure_path
