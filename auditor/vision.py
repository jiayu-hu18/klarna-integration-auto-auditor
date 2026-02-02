"""
Template matching for Klarna logo detection in footer screenshots.
Uses OpenCV with multi-scale grayscale matching (TM_CCOEFF_NORMED).
Supports alpha channel: needle loaded with IMREAD_UNCHANGED; 4-channel uses alpha as mask or composite.
"""
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

# Default: score >= this threshold => found
MATCH_THRESHOLD = 0.70
METHOD = "TM_CCOEFF_NORMED"
# Multi-scale: needle scaled by these factors to handle different logo sizes
SCALES = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
# If ROI height < this, expand ROI by EXPAND_PAD and re-run match
ROI_MIN_HEIGHT_EXPAND = 80
EXPAND_PAD = 150


def _ensure_grayscale(img: "np.ndarray") -> "np.ndarray":
    """Convert to grayscale if BGR/RGB."""
    if img is None:
        return None
    if len(img.shape) == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def _needle_to_gray_with_alpha(needle: "np.ndarray") -> "np.ndarray":
    """
    Convert needle to single-channel for matching. If 4-channel (BGRA), use alpha:
    composite BGR onto neutral gray (128) so transparent pixels don't bias match.
    Multi-scale will resize this result.
    """
    if needle is None:
        return None
    if len(needle.shape) == 2:
        return needle
    if needle.shape[2] == 4:
        bgr = needle[:, :, :3]
        alpha = needle[:, :, 3].astype(np.float32) / 255.0
        alpha_3 = np.expand_dims(alpha, axis=2)
        comp = (bgr.astype(np.float32) * alpha_3 + 128.0 * (1.0 - alpha_3)).astype(np.uint8)
        return cv2.cvtColor(comp, cv2.COLOR_BGR2GRAY)
    return _ensure_grayscale(needle)


def match_template_in_image(
    haystack_path: str,
    needle_path: str,
    threshold: float = 0.70,
) -> Dict[str, Any]:
    """
    Match template image (needle) in a larger image (haystack) using OpenCV.
    Needle is loaded with IMREAD_UNCHANGED; if 4-channel, alpha is used to composite onto gray.
    Multi-scale matching (needle scaled 0.7~1.4). Returns dict with found, score, bbox, method, paths.
    found=True when score >= threshold.
    """
    result = {
        "found": False,
        "score": 0.0,
        "bbox": None,
        "method": METHOD,
        "needle_path": str(needle_path),
        "haystack_path": str(haystack_path),
    }
    if cv2 is None or np is None:
        result["error"] = "opencv-python not installed"
        return result

    haystack_path = Path(haystack_path)
    needle_path = Path(needle_path)
    if not haystack_path.is_file():
        result["error"] = f"haystack not found: {haystack_path}"
        return result
    if not needle_path.is_file():
        result["error"] = f"needle not found: {needle_path}"
        return result

    try:
        haystack = cv2.imread(str(haystack_path))
        needle = cv2.imread(str(needle_path), cv2.IMREAD_UNCHANGED)
        if haystack is None or needle is None:
            result["error"] = "failed to load image(s)"
            return result
    except Exception as e:
        result["error"] = str(e)
        return result

    gray_haystack = _ensure_grayscale(haystack)
    needle_gray = _needle_to_gray_with_alpha(needle)
    if needle_gray is None:
        result["error"] = "failed to convert needle to gray"
        return result

    h_h, w_h = gray_haystack.shape[:2]
    h_n0, w_n0 = needle_gray.shape[:2]
    best_score = -1.0
    best_loc: Optional[Tuple[int, int]] = None
    best_w, best_h = 0, 0
    method_enum = cv2.TM_CCOEFF_NORMED

    for scale in SCALES:
        w_n = max(1, int(w_n0 * scale))
        h_n = max(1, int(h_n0 * scale))
        if w_n > w_h or h_n > h_h:
            continue
        needle_resized = cv2.resize(needle_gray, (w_n, h_n))
        try:
            match = cv2.matchTemplate(gray_haystack, needle_resized, method_enum)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match)
            score = float(max_val)
            if score > best_score:
                best_score = score
                best_loc = max_loc
                best_w, best_h = w_n, h_n
        except Exception:
            continue

    if best_loc is not None:
        x, y = best_loc
        result["score"] = round(best_score, 4)
        result["bbox"] = [int(x), int(y), int(best_w), int(best_h)]
        result["found"] = best_score >= threshold

    return result


def discover_templates(assets_dir: "Path") -> List[str]:
    """Discover all PNG template paths in assets_dir (e.g. klarna_*.png). Returns sorted list of paths."""
    assets_dir = Path(assets_dir)
    if not assets_dir.is_dir():
        return []
    paths = []
    for p in assets_dir.glob("*.png"):
        if p.name.lower().startswith("klarna") or "payment" in p.name.lower() or "wordmark" in p.name.lower():
            paths.append(str(p.resolve()))
    return sorted(paths) if paths else [str(p.resolve()) for p in sorted(assets_dir.glob("*.png"))]


def get_image_size(image_path: str) -> Tuple[int, int]:
    """Return (width, height) of image file, or (0, 0) on error."""
    if cv2 is None:
        return (0, 0)
    try:
        img = cv2.imread(str(image_path))
        if img is not None:
            h, w = img.shape[:2]
            return (w, h)
    except Exception:
        pass
    return (0, 0)


def crop_roi_from_image(haystack_path: str, x: int, y: int, w: int, h: int, output_path: str) -> Optional[str]:
    """
    Crop ROI (x, y, w, h) from haystack image and save to output_path.
    Clips to image bounds. Returns output_path if success else None.
    """
    if cv2 is None:
        return None
    path = Path(haystack_path)
    if not path.is_file():
        return None
    try:
        img = cv2.imread(str(path))
        if img is None:
            return None
        H, W = img.shape[:2]
        x1 = max(0, min(x, W - 1))
        y1 = max(0, min(y, H - 1))
        x2 = max(x1 + 1, min(x + w, W))
        y2 = max(y1 + 1, min(y + h, H))
        roi = img[y1:y2, x1:x2]
        if roi.size == 0:
            return None
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        if cv2.imwrite(str(out), roi):
            return output_path
    except Exception:
        pass
    return None


def expand_roi_bounds(img_width: int, img_height: int, x: int, y: int, w: int, h: int, pad: int = 150) -> Tuple[int, int, int, int]:
    """Expand ROI by pad; clip to image bounds. Returns (x, y, w, h)."""
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(img_width, x + w + pad)
    y2 = min(img_height, y + h + pad)
    return (x1, y1, x2 - x1, y2 - y1)


def draw_match_overlay(
    haystack_path: str,
    output_path: str,
    bbox: List[int],
    color: Tuple[int, int, int] = (0, 255, 0),
    thickness: int = 3,
) -> bool:
    """
    Draw a rectangle at bbox [x,y,w,h] on the haystack image and save to output_path.
    Returns True on success.
    """
    if cv2 is None:
        return False
    path = Path(haystack_path)
    if not path.is_file():
        return False
    try:
        img = cv2.imread(str(path))
        if img is None or len(bbox) != 4:
            return False
        x, y, w, h = bbox
        cv2.rectangle(img, (x, y), (x + w, y + h), color, thickness)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        return cv2.imwrite(str(out), img)
    except Exception:
        return False
