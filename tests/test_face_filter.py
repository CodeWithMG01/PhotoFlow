from pathlib import Path
import numpy as np
import pytest

from photoflow.face_filter import (
    SUPPORTED_IMAGE_FORMATS,
    find_photos_to_scan,
    is_match,
    load_face_engines,
)


def test_supported_formats():
    assert ".heic" in SUPPORTED_IMAGE_FORMATS
    assert ".jpg" in SUPPORTED_IMAGE_FORMATS
    assert ".png" in SUPPORTED_IMAGE_FORMATS


def test_find_photos_to_scan(tmp_path):
    source = tmp_path / "photos"
    source.mkdir()

    (source / "img1.JPG").touch()
    (source / "img2.heic").touch()
    (source / "img3.png").touch()
    (source / "doc.txt").touch()

    output = source / "Filtered_Photos"
    output.mkdir()
    (output / "matched.jpg").touch()

    photos = find_photos_to_scan(source, output)
    assert len(photos) == 3
    assert all(p.suffix.lower() in SUPPORTED_IMAGE_FORMATS for p in photos)


def test_engine_initialization():
    detector, recognizer = load_face_engines()
    assert detector is not None
    assert recognizer is not None


def test_face_match_logic():
    _, recognizer = load_face_engines()

    # Synthetic identical 128-D embedding vectors
    feat_a = np.ones((1, 128), dtype=np.float32)
    feat_b = np.ones((1, 128), dtype=np.float32)
    feat_c = -np.ones((1, 128), dtype=np.float32)

    assert is_match(feat_a, feat_b, recognizer, threshold=0.363) is True
    assert is_match(feat_a, feat_c, recognizer, threshold=0.363) is False
