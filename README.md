# Interview Emotion Detection App

This project uses the `fer` library (a pre-trained facial emotion recognition model) to detect emotions from webcam/camera images.

## ✅ Included Dataset (Sample)
To satisfy the request of "including a dataset with the project", this repo now includes a small **sample dataset** at:

- `data/sample_dataset/labels.csv` (labels file)
- `data/sample_dataset/images/` (synthetic sample face images: `happy_01.png`, `sad_01.png`, `surprise_01.png`)

This dataset is not the full FER2013 dataset (which is large), but it provides a lightweight, bundled dataset for demos/tests.

## 🔧 Regenerating the Sample Dataset
If you want to regenerate the sample dataset, run:

```bash
python scripts/generate_sample_dataset.py
```

## 🧠 What dataset does the app actually use?
The app uses the **pre-trained model inside the `fer` library**, which is typically trained on datasets like **FER2013** (not shipped directly in this repo due to size and licensing).

---

## 📥 Download the full FER2013 dataset (optional)
If you want the full FER2013 dataset locally (for model training, evaluation, or experimentation), you can download it from Kaggle using the Kaggle CLI.

### 1) Install and configure Kaggle CLI

```bash
pip install kaggle
```

Then configure your Kaggle API credentials (see https://www.kaggle.com/docs/api).

### 2) Download the dataset

```bash
python scripts/download_fer2013.py
```

This will download & unzip the dataset to:

- `data/fer2013/fer2013.csv`

### 3) Use the dataset in your own training / scripts

The app itself uses a pre-trained model and does not automatically load this dataset, but you can use the downloaded CSV for your own training or analysis.
