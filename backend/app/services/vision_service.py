from pathlib import Path

import cv2
import numpy as np


def load_image_grayscale(file_path: str | Path) -> np.ndarray | None:
    """Load a document image in grayscale for OpenCV tampering checks."""
    return cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)

