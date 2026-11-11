from pathlib import Path
import os
import shutil
import urllib.request
import numpy as np
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener
import cv2

register_heif_opener()

SUPPORTED_IMAGE_FORMATS = {
    ".heic", ".heif", ".hif",
    ".jpg", ".jpeg",
    ".png", ".webp", ".bmp", ".tiff"
}

MODELS_DIR = Path(__file__).parent / "models"
YUNET_MODEL = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
SFACE_MODEL = MODELS_DIR / "face_recognition_sface_2021dec.onnx"

YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
SFACE_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"

# Default cosine similarity threshold recommended by OpenCV SFace
DEFAULT_MATCH_THRESHOLD = 0.363


def ensure_models_exist(progress_callback=None) -> tuple[Path, Path]:
    """Ensure ONNX face detection and recognition models exist locally."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    def _download(url: str, dest: Path, label: str):
        if not dest.exists() or dest.stat().st_size < 10000:
            if progress_callback:
                progress_callback(f"Downloading {label} model...")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
                f.write(resp.read())

    _download(YUNET_URL, YUNET_MODEL, "YuNet Face Detector")
    _download(SFACE_URL, SFACE_MODEL, "SFace Face Recognizer")

    return YUNET_MODEL, SFACE_MODEL


def load_face_engines(yunet_path: Path = None, sface_path: Path = None):
    """Instantiate OpenCV YuNet FaceDetectorYN and SFace FaceRecognizerSF."""
    if yunet_path is None or sface_path is None:
        y_p, s_p = ensure_models_exist()
        yunet_path = yunet_path or y_p
        sface_path = sface_path or s_p

    detector = cv2.FaceDetectorYN.create(
        model=str(yunet_path),
        config="",
        input_size=(320, 320),
        score_threshold=0.7,
        nms_threshold=0.3,
        top_k=5000,
        backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
        target_id=cv2.dnn.DNN_TARGET_CPU
    )

    recognizer = cv2.FaceRecognizerSF.create(
        model=str(sface_path),
        config="",
        backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
        target_id=cv2.dnn.DNN_TARGET_CPU
    )

    return detector, recognizer


def load_image_bgr(image_path: Path) -> np.ndarray:
    """Load any image format (HEIC, JPG, PNG) into an OpenCV BGR numpy array with EXIF orientation corrected."""
    with Image.open(image_path) as pil_img:
        pil_img = ImageOps.exif_transpose(pil_img)
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
        rgb_arr = np.array(pil_img)
        return cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)


def detect_faces(img_bgr: np.ndarray, detector: cv2.FaceDetectorYN, max_dimension: int = 1280):
    """Detect faces with dynamic downscaling for high performance on high-res camera photos."""
    h, w = img_bgr.shape[:2]
    scale = 1.0

    if max(h, w) > max_dimension:
        scale = max_dimension / float(max(h, w))
        target_w = int(w * scale)
        target_h = int(h * scale)
        scaled_img = cv2.resize(img_bgr, (target_w, target_h), interpolation=cv2.INTER_AREA)
    else:
        scaled_img = img_bgr
        target_w, target_h = w, h

    detector.setInputSize((target_w, target_h))
    _, faces = detector.detect(scaled_img)

    if faces is None:
        return []

    # Map bounding boxes and 5 landmarks back to full resolution
    if scale != 1.0:
        inv_scale = 1.0 / scale
        rescaled_faces = []
        for face in faces:
            f = face.copy()
            f[0:4] = f[0:4] * inv_scale
            f[4:14] = f[4:14] * inv_scale
            rescaled_faces.append(f)
        return rescaled_faces

    return [f for f in faces]


def extract_primary_embedding(image_path: Path, detector, recognizer) -> np.ndarray:
    """Extract face embedding for the primary (largest) face in a reference photo."""
    img_bgr = load_image_bgr(image_path)
    faces = detect_faces(img_bgr, detector)

    if not faces:
        raise ValueError(f"No face detected in reference photo: {image_path.name}")

    # Select largest face by area (w * h)
    primary_face = max(faces, key=lambda f: f[2] * f[3])
    aligned = recognizer.alignCrop(img_bgr, primary_face)
    return recognizer.feature(aligned)


def extract_all_embeddings(img_bgr: np.ndarray, faces, recognizer) -> list[np.ndarray]:
    """Extract embeddings for all detected faces in a photo."""
    embeddings = []
    for face in faces:
        try:
            aligned = recognizer.alignCrop(img_bgr, face)
            feat = recognizer.feature(aligned)
            embeddings.append(feat)
        except Exception:
            continue
    return embeddings


def is_match(feat_a: np.ndarray, feat_b: np.ndarray, recognizer, threshold: float = DEFAULT_MATCH_THRESHOLD) -> bool:
    """Check if two face embeddings match using cosine similarity."""
    score = recognizer.match(feat_a, feat_b, cv2.FaceRecognizerSF_FR_COSINE)
    return float(score) >= threshold


def find_photos_to_scan(source_folder: Path, output_folder: Path = None) -> list[Path]:
    """Find all image files in source_folder, excluding output_folder."""
    source_folder = Path(source_folder).resolve()
    photos = []

    for file_path in source_folder.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SUPPORTED_IMAGE_FORMATS:
            continue
        if output_folder and (output_folder == file_path.resolve() or output_folder in file_path.resolve().parents):
            continue
        photos.append(file_path)

    return sorted(photos)


def filter_photos_by_faces(
    source_folder: Path,
    output_folder: Path,
    person_a_ref: Path,
    person_b_ref: Path = None,
    action: str = "copy",  # "copy", "move", or "separate"
    threshold: float = DEFAULT_MATCH_THRESHOLD,
    progress_callback=None,
    cancel_event=None
) -> dict:
    """
    Scan source_folder and filter photos containing Person A, Person B, or both.
    
    Permutations handled:
    - Person A solo
    - Person B solo
    - Person A and Person B together
    - Person A or B (or both) within a larger group photo
    """
    source_folder = Path(source_folder).resolve()
    output_folder = Path(output_folder).resolve()

    if not source_folder.is_dir():
        raise ValueError("Source folder does not exist.")

    if not person_a_ref or not Path(person_a_ref).is_file():
        raise ValueError("Please provide a valid reference photo for Person 1.")

    detector, recognizer = load_face_engines()

    if progress_callback:
        progress_callback(0, 1, "Extracting Person 1 reference...")

    person_a_feat = extract_primary_embedding(Path(person_a_ref), detector, recognizer)

    person_b_feat = None
    if person_b_ref and Path(person_b_ref).is_file():
        if progress_callback:
            progress_callback(0, 1, "Extracting Person 2 reference...")
        person_b_feat = extract_primary_embedding(Path(person_b_ref), detector, recognizer)

    photos = find_photos_to_scan(source_folder, output_folder)

    results = {
        "total": len(photos),
        "matched": 0,
        "unmatched": 0,
        "person_a_count": 0,
        "person_b_count": 0,
        "both_count": 0,
        "cancelled": False,
        "errors": []
    }

    matched_dir = output_folder / "Matched_Photos"
    matched_dir.mkdir(parents=True, exist_ok=True)

    other_dir = None
    if action == "separate":
        other_dir = output_folder / "Other_Photos"
        other_dir.mkdir(parents=True, exist_ok=True)

    for index, photo in enumerate(photos, start=1):
        if cancel_event and cancel_event.is_set():
            results["cancelled"] = True
            break

        try:
            img_bgr = load_image_bgr(photo)
            faces = detect_faces(img_bgr, detector)
            photo_embeddings = extract_all_embeddings(img_bgr, faces, recognizer)

            has_a = any(is_match(f, person_a_feat, recognizer, threshold) for f in photo_embeddings)
            has_b = False
            if person_b_feat is not None:
                has_b = any(is_match(f, person_b_feat, recognizer, threshold) for f in photo_embeddings)

            is_target_photo = has_a or has_b

            if has_a and has_b:
                results["both_count"] += 1
            elif has_a:
                results["person_a_count"] += 1
            elif has_b:
                results["person_b_count"] += 1

            relative = photo.relative_to(source_folder)

            if is_target_photo:
                results["matched"] += 1
                dest = matched_dir / relative.parent / photo.name
                dest.parent.mkdir(parents=True, exist_ok=True)

                if action == "move":
                    shutil.move(str(photo), str(dest))
                else:
                    shutil.copy2(str(photo), str(dest))
            else:
                results["unmatched"] += 1
                if action == "separate" and other_dir:
                    dest = other_dir / relative.parent / photo.name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(photo), str(dest))

        except Exception as err:
            results["errors"].append(f"{photo.name}: {err}")

        if progress_callback:
            status_text = f"Photo {index}/{len(photos)}: {'Matched' if is_target_photo else 'Skipped'}"
            progress_callback(index, len(photos), status_text)

    return results
