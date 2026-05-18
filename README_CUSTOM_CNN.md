# Custom CNN Emotion Detection for Flask App

This project replaces the FER library with a custom Convolutional Neural Network (CNN) trained on the FER2013 dataset for real-time emotion detection.

## Features

- **CNN Architecture**: Custom-built CNN with Conv2D, MaxPooling, and Dense layers
- **Face Detection**: OpenCV Haar Cascade for face detection (replaces MTCNN)
- **Emotions**: Detects 7 emotions: angry, disgust, fear, happy, neutral, sad, surprise
- **Real-time**: Optimized for webcam/webcam use with preprocessing
- **Flask Integration**: Updated /predict API to use the custom model

## Files

- `train_model.py`: Script to train the CNN on FER2013 dataset
- `emotion_detector.py`: Prediction module with face detection and emotion classification
- `app.py`: Updated Flask app using the custom detector
- `requirements.txt`: Updated dependencies (removed FER, added TensorFlow)

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Download FER2013 Dataset**:
   - Run `scripts/download_fer2013.py` or manually place images in `data/fer2013/train/` and `data/fer2013/test/`

3. **Train the Model**:
   ```bash
   python train_model.py
   ```
   This will create `emotion_model.h5` (takes ~30-60 minutes depending on hardware)

4. **Run the Flask App**:
   ```bash
   python app.py
   ```

## CNN Architecture

```python
Model: "sequential"
_________________________________________________________________
Layer (type)                 Output Shape              Param #
=================================================================
conv2d (Conv2D)              (None, 48, 48, 32)        896
_________________________________________________________________
max_pooling2d (MaxPooling2D) (None, 24, 24, 32)        0
_________________________________________________________________
conv2d_1 (Conv2D)            (None, 24, 24, 64)        18496
_________________________________________________________________
max_pooling2d_1 (MaxPooling2 (None, 12, 12, 64)        0
_________________________________________________________________
conv2d_2 (Conv2D)            (None, 12, 12, 128)       73856
_________________________________________________________________
max_pooling2d_2 (MaxPooling2 (None, 6, 6, 128)         0
_________________________________________________________________
flatten (Flatten)            (None, 4608)              0
_________________________________________________________________
dense (Dense)                (None, 128)               589952
_________________________________________________________________
dropout (Dropout)            (None, 128)               0
_________________________________________________________________
dense_1 (Dense)              (None, 7)                 903
=================================================================
Total params: 684,103
Trainable params: 684,103
Non-trainable params: 0
```

## API Usage

The `/predict` endpoint accepts a base64-encoded image and returns:

```json
{
  "faces": [
    {
      "emotion": "happy",
      "score": 0.85
    }
  ],
  "emotion": "happy",
  "score": 0.85
}
```

## Preprocessing Steps

1. **Face Detection**: Haar Cascade detects faces
2. **Resize**: Face cropped and resized to 48x48
3. **Grayscale**: Convert to grayscale if needed
4. **Normalize**: Pixel values scaled to [0, 1]
5. **Predict**: CNN outputs softmax probabilities

## Optimization for Real-time

- Lightweight CNN architecture
- Efficient face detection with Haar Cascade
- Minimal preprocessing steps
- Batch prediction support

## Training Details

- **Dataset**: FER2013 (28,709 training images)
- **Epochs**: 50
- **Batch Size**: 32
- **Data Augmentation**: Rotation, shift, flip, zoom
- **Loss**: Categorical Crossentropy
- **Optimizer**: Adam
- **Accuracy**: ~65-70% on validation set (typical for FER2013)

## Notes

- Model file `emotion_model.h5` must be present for predictions
- Haar Cascade XML is loaded from OpenCV data
- Compatible with webcam streams for real-time detection