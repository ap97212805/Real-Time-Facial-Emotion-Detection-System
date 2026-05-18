"""Generate a small sample face-emotion dataset for this project.

This script creates a tiny dataset (a few synthetic images) under data/sample_dataset.
It is meant to allow the app to ship with a "dataset" included, even if the real
FER2013 dataset is too large to bundle.

Usage:
    python scripts/generate_sample_dataset.py

Outputs:
    data/sample_dataset/labels.csv
    data/sample_dataset/images/*.png
"""

import os
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    raise SystemExit("Pillow is required to generate the sample dataset. Install it with `pip install pillow`.")

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "sample_dataset"
IMAGES_DIR = DATA_DIR / "images"

DATA_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Simple synthetic face generator (not realistic, just for demo).
def create_face_image(path: Path, face_color, mouth_color, eye_color, text: str):
    img = Image.new("RGB", (128, 128), color=face_color)
    draw = ImageDraw.Draw(img)

    # Draw eyes
    draw.ellipse((34, 38, 54, 58), fill=eye_color)
    draw.ellipse((74, 38, 94, 58), fill=eye_color)
    # Draw mouth
    draw.arc((34, 58, 94, 108), start=0, end=180, fill=mouth_color, width=6)

    # Write label text for easy manual verification
    draw.text((10, 110), text, fill=(255, 255, 255))
    img.save(path)

# Create sample images
create_face_image(IMAGES_DIR / "happy_01.png", face_color=(100, 200, 100), mouth_color=(255, 255, 255), eye_color=(0, 0, 0), text="happy")
create_face_image(IMAGES_DIR / "sad_01.png", face_color=(100, 100, 200), mouth_color=(255, 255, 255), eye_color=(0, 0, 0), text="sad")
create_face_image(IMAGES_DIR / "surprise_01.png", face_color=(200, 200, 100), mouth_color=(255, 255, 255), eye_color=(0, 0, 0), text="surprise")

# Create labels file
labels_path = DATA_DIR / "labels.csv"
with open(labels_path, "w", encoding="utf-8") as f:
    f.write("filename,emotion\n")
    f.write("images/happy_01.png,happy\n")
    f.write("images/sad_01.png,sad\n")
    f.write("images/surprise_01.png,surprise\n")

print(f"Sample dataset created at: {DATA_DIR}")
