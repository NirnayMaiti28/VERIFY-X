import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

from collections import Counter
import math

import tensorflow as tf

DATASET_DIR = "Data Set 1"
TRAIN_DIR = os.path.join(DATASET_DIR, "train")
VALIDATION_DIR = os.path.join(DATASET_DIR, "validation")
TEST_DIR = os.path.join(DATASET_DIR, "test")
IMG_SIZE = 224
BATCH_SIZE = 32
SEED = 123
AUTOTUNE = tf.data.AUTOTUNE
CLASS_NAMES = ["fake", "real"]
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}

data_augmentation = tf.keras.Sequential(
    [
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(0.05),
        tf.keras.layers.RandomTranslation(0.08, 0.08),
        tf.keras.layers.RandomZoom(0.1),
        tf.keras.layers.RandomContrast(0.15),
        tf.keras.layers.RandomBrightness(0.1),
    ],
    name="data_augmentation",
)


def _collect_samples(split_dir):
    file_paths = []
    labels = []
    skipped_files = []

    for class_index, class_name in enumerate(CLASS_NAMES):
        class_dir = os.path.join(split_dir, class_name)
        if not os.path.isdir(class_dir):
            raise FileNotFoundError(f"Expected dataset folder '{class_dir}' was not found.")

        for root, _, files in os.walk(class_dir):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                extension = os.path.splitext(file_name)[1].lower()
                if extension not in VALID_EXTENSIONS:
                    continue

                # Validate files before building the tf.data pipeline so dataset
                # cardinality stays stable across epochs.
                if not _is_valid_image(file_path):
                    skipped_files.append(file_path)
                    continue

                file_paths.append(file_path)
                labels.append(class_index)

    if not file_paths:
        raise ValueError(f"No valid image files found under '{split_dir}'.")

    if skipped_files:
        print(f"Skipped unreadable image files in '{split_dir}': {len(skipped_files)}")

    return file_paths, labels


def _count_labels(labels):
    counts = Counter(labels)
    return {CLASS_NAMES[index]: counts.get(index, 0) for index in range(len(CLASS_NAMES))}


def _is_valid_image(file_path):
    try:
        image = tf.keras.utils.load_img(file_path, color_mode="rgb")
        image.close()
        return True
    except (OSError, ValueError, tf.errors.InvalidArgumentError, tf.errors.NotFoundError):
        return False


def _get_preprocess_fn(model_name):
    model_name = model_name.lower()

    if model_name == "custom_cnn":
        return lambda images: tf.cast(images, tf.float32) / 255.0

    if model_name == "resnet50":
        return tf.keras.applications.resnet50.preprocess_input

    if model_name == "mobilenetv2":
        return tf.keras.applications.mobilenet_v2.preprocess_input

    if model_name == "efficientnetb0":
        return tf.keras.applications.efficientnet.preprocess_input

    raise ValueError(
        f"Unsupported model_name '{model_name}'. "
        "Use one of: custom_cnn, resnet50, mobilenetv2, efficientnetb0."
    )


def get_preprocess_fn(model_name):
    return _get_preprocess_fn(model_name)


def _load_image_with_keras(file_path):
    if hasattr(file_path, "numpy"):
        file_path = file_path.numpy()

    if isinstance(file_path, bytes):
        file_path = file_path.decode("utf-8")

    image = tf.keras.utils.load_img(file_path, color_mode="rgb", target_size=(IMG_SIZE, IMG_SIZE))
    image_array = tf.keras.utils.img_to_array(image, dtype="float32")
    return image_array


def _decode_image(file_path, label):
    image = tf.py_function(_load_image_with_keras, [file_path], Tout=tf.float32)
    image.set_shape((IMG_SIZE, IMG_SIZE, 3))
    label = tf.cast(label, tf.float32)
    label = tf.expand_dims(label, axis=-1)
    return image, label


def _prepare_dataset(file_paths, labels, preprocess_fn, training):
    dataset = tf.data.Dataset.from_tensor_slices((file_paths, labels))

    if training:
        dataset = dataset.shuffle(buffer_size=len(file_paths), seed=SEED, reshuffle_each_iteration=True)

    dataset = dataset.map(_decode_image, num_parallel_calls=AUTOTUNE)

    if not training:
        dataset = dataset.cache()

    def _map_fn(images, label):
        if training:
            images = data_augmentation(images, training=True)
        images = preprocess_fn(images)
        return images, label

    return (
        dataset.map(_map_fn, num_parallel_calls=AUTOTUNE)
        .batch(BATCH_SIZE)
        .prefetch(AUTOTUNE)
    )


def get_datasets(model_name="mobilenetv2"):
    preprocess_fn = _get_preprocess_fn(model_name)
    train_paths, train_labels = _collect_samples(TRAIN_DIR)
    val_paths, val_labels = _collect_samples(VALIDATION_DIR)
    test_paths, test_labels = _collect_samples(TEST_DIR)

    train_dataset = _prepare_dataset(train_paths, train_labels, preprocess_fn, training=True)
    val_dataset = _prepare_dataset(val_paths, val_labels, preprocess_fn, training=False)
    test_dataset = _prepare_dataset(test_paths, test_labels, preprocess_fn, training=False)

    train_counts = _count_labels(train_labels)
    val_counts = _count_labels(val_labels)
    test_counts = _count_labels(test_labels)
    total_counts = _count_labels(train_labels + val_labels + test_labels)

    total_train_images = len(train_labels)
    class_weights = {
        class_index: total_train_images / (len(CLASS_NAMES) * count)
        for class_index, count in Counter(train_labels).items()
        if count > 0
    }

    print("Classes:", CLASS_NAMES)
    print("Total class counts:", total_counts)
    print("Train split counts:", train_counts)
    print("Validation split counts:", val_counts)
    print("Test split counts:", test_counts)
    print("Class weights:", class_weights)
    print("Train batches:", math.ceil(len(train_labels) / BATCH_SIZE))
    print("Validation batches:", math.ceil(len(val_labels) / BATCH_SIZE))
    print("Test batches:", math.ceil(len(test_labels) / BATCH_SIZE))

    return train_dataset, val_dataset, test_dataset, class_weights, CLASS_NAMES


def main():
    get_datasets()


if __name__ == "__main__":
    main()
