import os
import numpy as np
import cv2
import pandas as pd
from tensorflow.keras.models import Sequential
from tensorflow.keras.optimizers import SGD, Adam
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout, BatchNormalization
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.utils import to_categorical
from sklearn.utils.class_weight import compute_class_weight
from tensorflow.keras.regularizers import l2
from tensorflow.keras.callbacks import ReduceLROnPlateau, ModelCheckpoint
from tensorflow.keras import backend as K

EMOTIONS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
NUM_CLASSES = len(EMOTIONS)

def focal_loss(gamma=2., alpha=0.25):
    def focal_loss_fixed(y_true, y_pred):
        epsilon = K.epsilon()
        y_pred = K.clip(y_pred, epsilon, 1. - epsilon)
        pt = y_true * y_pred + (1 - y_true) * (1 - y_pred)
        pt = K.sum(pt, axis=-1)
        ce = -K.log(pt)
        weight = alpha * K.pow((1 - pt), gamma)
        fl = weight * ce
        return K.mean(fl)
    return focal_loss_fixed

def load_data(data_dir='data/fer2013'):
    """Load images from folder structure"""
    images = []
    labels = []
    class_counts = [0] * len(EMOTIONS)

    for emotion_idx, emotion in enumerate(EMOTIONS):
        emotion_dir = os.path.join(data_dir, 'train', emotion)
        if not os.path.exists(emotion_dir):
            print(f"Warning: {emotion_dir} does not exist")
            continue

        print(f"Loading {emotion} images...")
        for img_file in os.listdir(emotion_dir):
            if img_file.endswith('.jpg'):
                img_path = os.path.join(emotion_dir, img_file)
                img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    img = cv2.resize(img, (48, 48))
                    images.append(img)
                    labels.append(emotion_idx)
                    class_counts[emotion_idx] += 1

    print(f"Total images loaded: {len(images)}")
    print(f"Class distribution: {dict(zip(EMOTIONS, class_counts))}")
    if images:
        print(f"Sample image shape: {images[0].shape}")

    images = np.array(images, dtype=np.float32) / 255.0
    images = images.reshape(-1, 48, 48, 1)
    labels = to_categorical(labels, num_classes=NUM_CLASSES)

    print(f"Images shape: {images.shape}, Labels shape: {labels.shape}")

    from sklearn.model_selection import train_test_split
    y_labels = np.argmax(labels, axis=1)
    X_train, X_val, y_train, y_val = train_test_split(
        images, labels, test_size=0.2, random_state=42, stratify=y_labels
    )
    
    print(f"Training set: {len(X_train)} images")
    print(f"Validation set: {len(X_val)} images")
    
    return X_train, X_val, y_train, y_val


def create_cnn_model():
    model = Sequential()

    model.add(Conv2D(64, (3,3), activation='relu', padding='same', input_shape=(48,48,1)))
    model.add(BatchNormalization())
    model.add(Conv2D(64, (3,3), activation='relu', padding='same'))
    model.add(BatchNormalization())
    model.add(MaxPooling2D(2,2))
    model.add(Dropout(0.25))

    model.add(Conv2D(128, (3,3), activation='relu', padding='same'))
    model.add(BatchNormalization())
    model.add(Conv2D(128, (3,3), activation='relu', padding='same'))
    model.add(BatchNormalization())
    model.add(MaxPooling2D(2,2))
    model.add(Dropout(0.35))

    model.add(Conv2D(256, (3,3), activation='relu', padding='same'))
    model.add(BatchNormalization())
    model.add(Conv2D(256, (3,3), activation='relu', padding='same'))
    model.add(BatchNormalization())
    model.add(MaxPooling2D(2,2))
    model.add(Dropout(0.4))

    model.add(Conv2D(256, (3,3), activation='relu', padding='same'))
    model.add(BatchNormalization())
    model.add(Conv2D(256, (3,3), activation='relu', padding='same'))
    model.add(BatchNormalization())
    model.add(MaxPooling2D(2,2))
    model.add(Dropout(0.45))

    model.add(Flatten())
    model.add(Dense(512, activation='relu'))
    model.add(BatchNormalization())
    model.add(Dropout(0.5))

    model.add(Dense(NUM_CLASSES, activation='softmax'))

    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss=focal_loss(gamma=2., alpha=0.25),
        metrics=['accuracy']
    )

    return model


def main():
    print("Loading training data...")
    
    # ✅ FIXED loading
    X_train, X_val, y_train, y_val = load_data()


    # Compute class weights
    y_integers = np.argmax(y_train, axis=1)

    class_weights = compute_class_weight(
    class_weight='balanced',
    classes=np.unique(y_integers),
    y=y_integers
    )

    class_weights = dict(enumerate(class_weights))

    # Boost minority classes (angry, disgust, fear, sad, surprise) to improve detection
    minority_classes = [0, 1, 2, 5, 6]  # indices for angry, disgust, fear, sad, surprise
    for cls in minority_classes:
        class_weights[cls] *= 2.0  # 2x boost for minority classes

    print(f"Adjusted class weights: {class_weights}")

    print(f"Training set: {len(X_train)} images")
    print(f"Validation set: {len(X_val)} images")

    model = create_cnn_model()

    print("\nModel Architecture:")
    model.summary()

    datagen = ImageDataGenerator(
        rotation_range=12,
        zoom_range=0.15,
        width_shift_range=0.1,
        height_shift_range=0.1,
        shear_range=0.12,
        brightness_range=[0.7, 1.3],
        horizontal_flip=True,
        fill_mode='nearest'
    )

    print("\nTraining the model...")

    lr_scheduler = ReduceLROnPlateau(
        monitor='val_loss',
        patience=10,
        factor=0.5,
        min_lr=1e-6
    )

    # No early stopping, full training run is required
    checkpoint = ModelCheckpoint(
        'emotion_model_best.h5',
        monitor='val_accuracy',
        save_best_only=True,
        mode='max',
        verbose=1
    )

    history = model.fit(
        datagen.flow(X_train, y_train, batch_size=64),
        validation_data=(X_val, y_val),
        epochs=200,
        verbose=1,
        class_weight=class_weights,
        callbacks=[lr_scheduler, checkpoint]
    )

    model.save('emotion_model.h5')
    print("\nModel saved as 'emotion_model.h5'")

    val_loss, val_accuracy = model.evaluate(X_val, y_val, verbose=0)
    print(f"Validation Accuracy: {val_accuracy:.2f}")


if __name__ == "__main__":
    main()
    