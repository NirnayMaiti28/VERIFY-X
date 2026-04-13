import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import tensorflow as tf
from tensorflow.keras import layers, models

MODEL_BUILDERS = {
    "resnet50": tf.keras.applications.ResNet50,
    "mobilenetv2": tf.keras.applications.MobileNetV2,
    "efficientnetb0": tf.keras.applications.EfficientNetB0,
}


def build_pretrained_cnn(
    model_name="mobilenetv2",
    input_shape=(224, 224, 3),
    dropout_rate=0.3,
    dense_units=256,
):
    model_name = model_name.lower()

    if model_name not in MODEL_BUILDERS:
        raise ValueError(
            f"Unsupported model_name '{model_name}'. "
            "Use one of: resnet50, mobilenetv2, efficientnetb0."
        )

    base_model = MODEL_BUILDERS[model_name](
        weights="imagenet",
        include_top=False,
        input_shape=input_shape,
    )
    base_model.trainable = False

    inputs = layers.Input(shape=input_shape)
    x = base_model(inputs, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(dropout_rate)(x)
    x = layers.Dense(dense_units, activation="relu")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(dropout_rate)(x)
    outputs = layers.Dense(1, activation="sigmoid", dtype="float32")(x)

    model = models.Model(inputs=inputs, outputs=outputs, name=f"{model_name}_fake_detector")
    compile_model(model, learning_rate=1e-4)

    return model, base_model


def compile_model(model, learning_rate, label_smoothing=0.05, weight_decay=1e-4):
    model.compile(
        optimizer=tf.keras.optimizers.AdamW(
            learning_rate=learning_rate,
            weight_decay=weight_decay,
        ),
        loss=tf.keras.losses.BinaryCrossentropy(label_smoothing=label_smoothing),
        metrics=[
            tf.keras.metrics.BinaryAccuracy(name="accuracy"),
            tf.keras.metrics.AUC(name="auc"),
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
        ],
    )


def unfreeze_for_fine_tuning(base_model, trainable_fraction=0.5):
    base_model.trainable = True

    total_layers = len(base_model.layers)
    freeze_until = int(total_layers * (1 - trainable_fraction))

    for layer in base_model.layers[:freeze_until]:
        layer.trainable = False

    for layer in base_model.layers[freeze_until:]:
        if isinstance(layer, layers.BatchNormalization):
            layer.trainable = False
