"""
Emotion detection using custom CNN model and OpenCV Haar Cascade.

This module provides functions for:
- Loading the trained CNN model
- Detecting faces using OpenCV Haar Cascade
- Preprocessing images for prediction
- Predicting emotions from face images

Optimized for real-time prediction.
"""

import cv2
import numpy as np
from tensorflow.keras.models import load_model

# Emotion labels (must match training order)
EMOTIONS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']

# Load Haar Cascade classifier for face detection
FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Global model variable
_model = None

def load_emotion_model(model_path='emotion_model.h5'):
    """
    Load the trained emotion detection model.

    Args:
        model_path (str): Path to the .h5 model file

    Returns:
        keras.Model: Loaded model
    """
    global _model
    if _model is None:
        try:
            _model = load_model(model_path)
            print(f"Model loaded from {model_path}")
        except Exception as e:
            print(f"Error loading model: {e}")
            return None
    return _model

def preprocess_face(face_img):
    """
    Preprocess a face image for CNN prediction.

    Args:
        face_img (numpy.ndarray): Face image (BGR or grayscale)

    Returns:
        numpy.ndarray: Preprocessed image ready for prediction
    """
    # Convert to grayscale if needed
    if len(face_img.shape) == 3:
        face_img = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)

    # Resize to 48x48
    face_img = cv2.resize(face_img, (48, 48))

    # Normalize to [0, 1]
    face_img = face_img.astype(np.float32) / 255.0

    # Add batch and channel dimensions
    face_img = face_img.reshape(1, 48, 48, 1)

    return face_img

def detect_faces(image):
    """
    Detect faces in an image using Haar Cascade.

    Args:
        image (numpy.ndarray): Input image (BGR)

    Returns:
        list: List of face rectangles (x, y, w, h)
    """
    # Convert to grayscale for detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Detect faces
    faces = FACE_CASCADE.detectMultiScale(
        gray,
        scaleFactor=1.2,
        minNeighbors=6,
        minSize=(40, 40),
        flags=cv2.CASCADE_SCALE_IMAGE
    )

    return faces

def predict_emotion_from_face(face_img):
    """
    Predict emotion from a single face image.

    Args:
        face_img (numpy.ndarray): Face image

    Returns:
        tuple: (emotion_label, confidence_score)
    """
    model = load_emotion_model()
    if model is None:
        return "error", 0.0

    # Preprocess the face
    processed_face = preprocess_face(face_img)

    # Predict
    predictions = model.predict(processed_face, verbose=0)[0]

    # Get the emotion with highest probability
    emotion_idx = np.argmax(predictions)
    emotion = EMOTIONS[emotion_idx]
    confidence = float(predictions[emotion_idx])

    return emotion, confidence

def predict_emotion_from_image(image):
    """
    Detect faces in an image and predict emotions for each face.

    Args:
        image (numpy.ndarray): Input image (BGR)

    Returns:
        list: List of dictionaries with face detection and emotion results
    """
    faces = detect_faces(image)
    if len(faces) == 0:
        return []
    results = []

    for (x, y, w, h) in faces:
        # Extract face region
        face_img = image[y:y+h, x:x+w]

        # Predict emotion
        emotion, score = predict_emotion_from_face(face_img)

        # Create result dictionary
        result = {
            'box': [int(x), int(y), int(w), int(h)],
            'emotion': emotion,
            'score': round(score, 3)
        }
        results.append(result)

    return results

def get_emotion_probabilities(face_img):
    """
    Get all emotion probabilities for a face image.

    Args:
        face_img (numpy.ndarray): Face image

    Returns:
        dict: Dictionary of emotion probabilities
    """
    model = load_emotion_model()
    if model is None:
        return {}

    processed_face = preprocess_face(face_img)
    predictions = model.predict(processed_face, verbose=0)[0]

    # Create emotion dictionary
    emotion_probs = {}
    for i, emotion in enumerate(EMOTIONS):
        emotion_probs[emotion] = float(predictions[i])

    return emotion_probs