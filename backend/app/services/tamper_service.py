from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

import cv2
import fitz
import numpy as np
from PIL import Image, ImageChops, ImageEnhance

from app.config import get_settings
from app.services.storage_service import resolve_local_path


def detect_document_tampering(file_path: str | Path) -> dict[str, Any]:
    """Heuristic tampering detector for verification triage.

    The checks below look for compression, blur, edge, noise, and rectangular paste
    inconsistencies. They provide review signals that help decide whether a
    recruiter should inspect a document manually.
    """
    image = load_first_page_or_image(file_path)
    suspicious_regions: list[dict[str, Any]] = []

    ela_map = build_ela_map(image)
    suspicious_regions.extend(find_hot_regions(ela_map, "compression_mismatch", 0.88))

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    suspicious_regions.extend(find_blur_variance_regions(gray))
    suspicious_regions.extend(find_edge_inconsistency_regions(gray))
    suspicious_regions.extend(find_rectangular_regions(gray))
    suspicious_regions.extend(find_noise_inconsistency_regions(gray))
    suspicious_regions.extend(find_text_region_mismatch_regions(gray))

    suspicious_regions = merge_and_limit_regions(suspicious_regions)
    tamper_score = min(100.0, sum(region["score"] for region in suspicious_regions))
    if tamper_score >= 65:
        status = "high_risk"
    elif tamper_score >= 35:
        status = "suspicious"
    elif tamper_score > 0:
        status = "low_signal"
    else:
        status = "clean"

    heatmap_path = create_heatmap(image, suspicious_regions)
    return {
        "tampering_status": status,
        "suspicious_regions": suspicious_regions,
        "tamper_score": round(tamper_score, 2),
        "heatmap_path": heatmap_path,
        "explanation": (
            "This analysis highlights regions with unusual compression, blur, noise, "
            "edge, or pasted-shape signals."
        ),
        "fraud_flags": build_tamper_flags(suspicious_regions, status),
    }


def load_first_page_or_image(file_path: str | Path) -> np.ndarray:
    path = Path(resolve_local_path(str(file_path)))
    if path.suffix.lower() == ".pdf":
        with fitz.open(path) as document:
            page = document[0]
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            array = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height, pixmap.width, 3
            )
            return cv2.cvtColor(array, cv2.COLOR_RGB2BGR)

    image = cv2.imread(str(path))
    if image is None:
        raise FileNotFoundError(path)
    return image


def build_ela_map(image: np.ndarray) -> np.ndarray:
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    original = Image.fromarray(rgb)
    buffer = BytesIO()
    original.save(buffer, "JPEG", quality=88)
    buffer.seek(0)
    compressed = Image.open(buffer)
    diff = ImageChops.difference(original, compressed)
    diff = ImageEnhance.Brightness(diff).enhance(12)
    diff_gray = cv2.cvtColor(np.array(diff), cv2.COLOR_RGB2GRAY)
    return cv2.GaussianBlur(diff_gray, (7, 7), 0)


def find_hot_regions(score_map: np.ndarray, region_type: str, percentile: float) -> list[dict[str, Any]]:
    threshold = max(25, int(np.quantile(score_map, percentile)))
    _, binary = cv2.threshold(score_map, threshold, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = []
    image_area = score_map.shape[0] * score_map.shape[1]
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < image_area * 0.002 or area > image_area * 0.35:
            continue
        regions.append(region(x, y, w, h, region_type, 16.0))
    return regions


def find_blur_variance_regions(gray: np.ndarray) -> list[dict[str, Any]]:
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    local_blur = cv2.blur(np.abs(laplacian), (31, 31))
    inverse = cv2.normalize(255 - local_blur, None, 0, 255, cv2.NORM_MINMAX).astype("uint8")
    return [dict(item, score=10.0) for item in find_hot_regions(inverse, "blur_variance", 0.93)]


def find_edge_inconsistency_regions(gray: np.ndarray) -> list[dict[str, Any]]:
    edges = cv2.Canny(gray, 80, 180)
    dilated = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    return [dict(item, score=8.0) for item in find_hot_regions(dilated, "edge_inconsistency", 0.97)]


def find_rectangular_regions(gray: np.ndarray) -> list[dict[str, Any]]:
    adaptive = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 9
    )
    closed = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = []
    image_area = gray.shape[0] * gray.shape[1]
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        rectangularity = cv2.contourArea(contour) / area if area else 0
        if image_area * 0.01 < area < image_area * 0.25 and rectangularity > 0.78:
            regions.append(region(x, y, w, h, "rectangular_paste_signal", 14.0))
    return regions


def find_noise_inconsistency_regions(gray: np.ndarray) -> list[dict[str, Any]]:
    denoised = cv2.medianBlur(gray, 5)
    noise = cv2.absdiff(gray, denoised)
    return [dict(item, score=10.0) for item in find_hot_regions(noise, "noise_inconsistency", 0.95)]


def find_text_region_mismatch_regions(gray: np.ndarray) -> list[dict[str, Any]]:
    sobel = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    text_like = cv2.convertScaleAbs(sobel)
    return [dict(item, score=7.0) for item in find_hot_regions(text_like, "text_region_mismatch", 0.98)]


def region(x: int, y: int, w: int, h: int, region_type: str, score: float) -> dict[str, Any]:
    return {
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "type": region_type,
        "label": label_for_region(region_type),
        "severity": severity_for_score(score),
        "confidence": min(0.98, round(score / 18, 2)),
        "score": score,
    }


def label_for_region(region_type: str) -> str:
    labels = {
        "compression_mismatch": "Compression anomaly",
        "blur_variance": "Signature region mismatch",
        "edge_inconsistency": "Font mismatch",
        "rectangular_paste_signal": "Date area edited",
        "noise_inconsistency": "Signature region mismatch",
        "text_region_mismatch": "Font mismatch",
    }
    return labels.get(region_type, "Suspicious region")


def severity_for_score(score: float) -> str:
    if score >= 14:
        return "high"
    if score >= 10:
        return "medium"
    return "low"


def merge_and_limit_regions(regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(regions, key=lambda item: item["score"], reverse=True)[:12]


def create_heatmap(image: np.ndarray, regions: list[dict[str, Any]]) -> str:
    settings = get_settings()
    output_dir = Path(settings.processed_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    overlay = image.copy()
    for item in regions:
        x, y, w, h = item["x"], item["y"], item["width"], item["height"]
        color = (0, 0, 255) if item["score"] >= 14 else (0, 165, 255)
        cv2.rectangle(overlay, (x, y), (x + w, y + h), color, 3)
    heatmap = cv2.addWeighted(overlay, 0.72, image, 0.28, 0)
    path = output_dir / f"tamper_heatmap_{uuid4().hex}.png"
    cv2.imwrite(str(path), heatmap)
    return str(path)


def build_tamper_flags(regions: list[dict[str, Any]], status: str) -> list[dict[str, Any]]:
    flags = []
    for item in regions[:6]:
        flag_type = "tamper_suspected_edited_region"
        if item["type"] == "compression_mismatch":
            flag_type = "tamper_compression_mismatch"
        elif "qr" in item["type"]:
            flag_type = "tamper_suspicious_qr_region"
        elif item["type"] in {"blur_variance", "noise_inconsistency"}:
            flag_type = "tamper_signature_stamp_area_inconsistency"
        flags.append(
            {
                "flag_type": flag_type,
                "severity": "high" if status in {"high_risk", "suspicious"} else "low",
                "message": f"Suspicious {item['type'].replace('_', ' ')} detected.",
                "region_coordinates": item,
            }
        )
    return flags
