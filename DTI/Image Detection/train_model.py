import argparse
import os
from pathlib import Path

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import tensorflow as tf

from data_preprocessing import IMG_SIZE, get_datasets
from pretrained_cnn_model import build_pretrained_cnn, compile_model, unfreeze_for_fine_tuning
from visualization_utils import save_training_curves


def parse_args():
    parser = argparse.ArgumentParser(description="Train an image manipulation detector.")
    parser.add_argument(
        "--model",
        default="efficientnetb0",
        choices=["mobilenetv2", "resnet50", "efficientnetb0"],
        help="Pretrained CNN backbone to use.",
    )
    parser.add_argument(
        "--learning-rate-head",
        type=float,
        default=3e-4,
        help="Learning rate for training the classification head.",
    )
    parser.add_argument(
        "--learning-rate-finetune",
        type=float,
        default=1e-5,
        help="Learning rate for fine-tuning the pretrained backbone.",
    )
    parser.add_argument("--epochs-head", type=int, default=6, help="Epochs with frozen backbone.")
    parser.add_argument("--epochs-finetune", type=int, default=8, help="Epochs for fine-tuning.")
    parser.add_argument(
        "--fine-tune-fraction",
        type=float,
        default=0.5,
        help="Fraction of backbone layers to unfreeze during fine-tuning.",
    )
    parser.add_argument(
        "--plots-dir",
        default="plots",
        help="Directory where training plots will be saved.",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory where the final model, logs, and plots will be saved.",
    )
    return parser.parse_args()


def write_history_csv(history, csv_path):
    history_dict = history.history
    learning_rates = history_dict.get("learning_rate", [])
    if len(learning_rates) < len(history_dict["loss"]):
        fallback_rate = learning_rates[-1] if learning_rates else ""
        learning_rates = learning_rates + [fallback_rate] * (len(history_dict["loss"]) - len(learning_rates))

    with csv_path.open("w", encoding="utf-8") as file:
        file.write(
            "epoch,accuracy,auc,learning_rate,loss,precision,recall,"
            "val_accuracy,val_auc,val_loss,val_precision,val_recall\n"
        )
        for epoch in range(len(history_dict["loss"])):
            file.write(
                f"{epoch},{history_dict['accuracy'][epoch]},{history_dict['auc'][epoch]},"
                f"{learning_rates[epoch]},{history_dict['loss'][epoch]},{history_dict['precision'][epoch]},"
                f"{history_dict['recall'][epoch]},{history_dict['val_accuracy'][epoch]},"
                f"{history_dict['val_auc'][epoch]},{history_dict['val_loss'][epoch]},"
                f"{history_dict['val_precision'][epoch]},{history_dict['val_recall'][epoch]}\n"
            )


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = output_dir / args.plots_dir

    train_dataset, val_dataset, test_dataset, class_weights, class_names = get_datasets(args.model)
    print("Training classes:", class_names)

    print("TensorFlow version:", tf.__version__)
    # print("Detected GPUs:", tf.config.list_physical_devices("GPU"))

    model, base_model = build_pretrained_cnn(
        model_name=args.model,
        input_shape=(IMG_SIZE, IMG_SIZE, 3),
    )
    compile_model(model, learning_rate=args.learning_rate_head)

    checkpoint_path = output_dir / f"{args.model}_fake_detector.keras"
    raw_csv_path = output_dir / f"{args.model}_training_log_raw.csv"

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_auc",
            mode="max",
            patience=4,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_auc",
            mode="max",
            factor=0.3,
            patience=2,
            min_lr=1e-6,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(checkpoint_path),
            monitor="val_auc",
            mode="max",
            save_best_only=True,
        ),
        tf.keras.callbacks.CSVLogger(str(raw_csv_path), append=False),
    ]

    model.summary()

    head_history = model.fit(
        train_dataset,
        validation_data=val_dataset,
        epochs=args.epochs_head,
        class_weight=class_weights,
        callbacks=callbacks,
    )

    histories = [head_history]

    if args.epochs_finetune > 0:
        model = tf.keras.models.load_model(checkpoint_path)
        base_model = model.get_layer(base_model.name)
        unfreeze_for_fine_tuning(base_model, trainable_fraction=args.fine_tune_fraction)
        compile_model(model, learning_rate=args.learning_rate_finetune)

        fine_tune_history = model.fit(
            train_dataset,
            validation_data=val_dataset,
            epochs=args.epochs_head + args.epochs_finetune,
            initial_epoch=args.epochs_head,
            class_weight=class_weights,
            callbacks=callbacks,
        )
        histories.append(fine_tune_history)

    model = tf.keras.models.load_model(checkpoint_path)
    final_path = checkpoint_path
    model.save(final_path)
    print(f"Model saved successfully to {final_path}")

    merged_history = histories[0]
    if len(histories) > 1:
        for key, values in histories[1].history.items():
            merged_history.history.setdefault(key, [])
            merged_history.history[key].extend(values)

    merged_csv_path = output_dir / f"{args.model}_training_log.csv"
    write_history_csv(merged_history, merged_csv_path)
    print(f"Merged training log saved to {merged_csv_path}")

    curves_path = save_training_curves(merged_history, plots_dir, args.model)
    print(f"Training curves saved to {curves_path}")

    test_metrics = model.evaluate(test_dataset, verbose=0)
    print("\nTest metrics:")
    for metric_name, metric_value in zip(model.metrics_names, test_metrics):
        print(f"{metric_name}: {metric_value:.4f}")


if __name__ == "__main__":
    main()
