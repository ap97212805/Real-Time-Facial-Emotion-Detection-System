"""Download the FER2013 dataset into this project.

This script uses the Kaggle CLI to download and unzip the FER2013 dataset.

FER2013 is a popular facial emotion recognition dataset used to train models like the one
used by the `fer` library. The dataset is large (~100MB) so it is not included in the repo.

Usage:
    pip install kaggle
    # Configure your Kaggle API credentials (see https://www.kaggle.com/docs/api)
    python scripts/download_fer2013.py

By default, the dataset will be downloaded to ``data/fer2013``.

NOTE: This script does NOT run automatically when starting the app. It is a helper to
fetch the dataset if you want it locally.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def check_kaggle_installed() -> bool:
    from shutil import which
    # Check if kaggle is in PATH or in venv
    if which("kaggle"):
        return True
    # Check in venv
    venv_kaggle = Path(__file__).resolve().parents[1] / ".venv" / "Scripts" / "kaggle.exe"
    return venv_kaggle.exists()


def run_command(cmd: str, cwd: Path | None = None) -> int:
    """Run a command and forward output."""
    return subprocess.run(cmd, shell=True, cwd=cwd).returncode


def download_fer2013(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)

    # Kaggle dataset slug
    dataset_slug = "msambare/fer2013"

    # If the file already appears to exist, do nothing.
    expected_csv = dest / "fer2013.csv"
    if expected_csv.exists():
        print(f"FER2013 already exists at {expected_csv}.")
        return

    if not check_kaggle_installed():
        raise SystemExit(
            "Kaggle CLI not found. Install it with `pip install kaggle` and configure "
            "your Kaggle API credentials (see https://www.kaggle.com/docs/api)."
        )

    print("Downloading FER2013 from Kaggle (this may take a while)...")
    
    # Use kaggle from venv if available
    kaggle_cmd = "kaggle"
    venv_kaggle = Path(__file__).resolve().parents[1] / ".venv" / "Scripts" / "kaggle.exe"
    if venv_kaggle.exists():
        kaggle_cmd = str(venv_kaggle)
    
    cmd = f'"{kaggle_cmd}" datasets download -d {dataset_slug} -p "{dest}" --unzip'

    ret = run_command(cmd)
    if ret != 0:
        raise SystemExit("Failed to download FER2013 via Kaggle CLI.")

    if not expected_csv.exists():
        raise SystemExit(
            "Download seemed to succeed but fer2013.csv was not found in the destination. "
            "Check the downloaded files in: "
            f"{dest.resolve()}"
        )

    print("FER2013 download complete!")
    print(f"Dataset is available under: {dest.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download FER2013 dataset using Kaggle CLI."
    )
    parser.add_argument(
        "--dest",
        default="data/fer2013",
        help="Destination directory for the dataset (default: data/fer2013)",
    )
    args = parser.parse_args()

    download_fer2013(Path(args.dest))


if __name__ == "__main__":
    main()
