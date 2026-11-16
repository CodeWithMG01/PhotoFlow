from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from photoflow.face_filter import (
    SUPPORTED_IMAGE_FORMATS,
    clean_trip_photos,
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


def test_find_photos_to_scan_when_output_is_source(tmp_path):
    source = tmp_path / "photos"
    source.mkdir()

    (source / "img1.JPG").touch()
    (source / "img2.heic").touch()

    # Excluded subdirectory inside source
    removed_dir = source / "Removed_Other_People"
    removed_dir.mkdir()
    (removed_dir / "bad.jpg").touch()

    # When output_folder is equal to source_folder
    photos = find_photos_to_scan(source, source)
    assert len(photos) == 2
    assert (removed_dir / "bad.jpg") not in photos


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


def test_clean_trip_photos_validation(tmp_path):
    source = tmp_path / "source"
    ref = tmp_path / "ref.jpg"
    ref.touch()

    # Source does not exist
    with pytest.raises(ValueError, match="Source folder does not exist"):
        clean_trip_photos(source, tmp_path / "out", person_a_ref=ref)

    source.mkdir()
    # Missing ref
    with pytest.raises(ValueError, match="reference photo for Person 1"):
        clean_trip_photos(source, tmp_path / "out", person_a_ref=None)


@patch("photoflow.face_filter.load_face_engines")
@patch("photoflow.face_filter.extract_primary_embedding")
@patch("photoflow.face_filter.load_image_bgr")
@patch("photoflow.face_filter.detect_faces")
def test_clean_trip_photos_scenery_kept(mock_detect, mock_load_bgr, mock_extract_ref, mock_load_engines, tmp_path):
    mock_load_engines.return_value = (MagicMock(), MagicMock())
    mock_extract_ref.return_value = np.zeros((1, 128), dtype=np.float32)
    mock_load_bgr.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_detect.return_value = []  # 0 faces -> Scenery

    source = tmp_path / "trip"
    source.mkdir()
    scenery = source / "mountain.jpg"
    scenery.touch()

    ref = tmp_path / "me.jpg"
    ref.touch()
    out = tmp_path / "output"

    res = clean_trip_photos(source, out, person_a_ref=ref, removal_scope="solo_only")

    assert res["kept_scenery"] == 1
    assert res["removed_others"] == 0
    assert scenery.exists()


@patch("photoflow.face_filter.load_face_engines")
@patch("photoflow.face_filter.extract_primary_embedding")
@patch("photoflow.face_filter.load_image_bgr")
@patch("photoflow.face_filter.detect_faces")
@patch("photoflow.face_filter.extract_all_embeddings")
@patch("photoflow.face_filter.is_match")
def test_clean_trip_photos_user_kept(mock_match, mock_all_emb, mock_detect, mock_load_bgr, mock_extract_ref, mock_load_engines, tmp_path):
    mock_load_engines.return_value = (MagicMock(), MagicMock())
    mock_extract_ref.return_value = np.zeros((1, 128), dtype=np.float32)
    mock_load_bgr.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_detect.return_value = [np.array([10, 10, 50, 50])]  # 1 face
    mock_all_emb.return_value = [np.zeros((1, 128), dtype=np.float32)]
    mock_match.return_value = True  # Matches Person 1

    source = tmp_path / "trip"
    source.mkdir()
    my_photo = source / "me_at_beach.jpg"
    my_photo.touch()

    ref = tmp_path / "me.jpg"
    ref.touch()
    out = tmp_path / "output"

    res = clean_trip_photos(source, out, person_a_ref=ref, removal_scope="solo_only")

    assert res["kept_us"] == 1
    assert res["removed_others"] == 0
    assert my_photo.exists()


@patch("photoflow.face_filter.load_face_engines")
@patch("photoflow.face_filter.extract_primary_embedding")
@patch("photoflow.face_filter.load_image_bgr")
@patch("photoflow.face_filter.detect_faces")
@patch("photoflow.face_filter.extract_all_embeddings")
@patch("photoflow.face_filter.is_match")
def test_clean_trip_photos_other_solo_moved(mock_match, mock_all_emb, mock_detect, mock_load_bgr, mock_extract_ref, mock_load_engines, tmp_path):
    mock_load_engines.return_value = (MagicMock(), MagicMock())
    mock_extract_ref.return_value = np.zeros((1, 128), dtype=np.float32)
    mock_load_bgr.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_detect.return_value = [np.array([10, 10, 50, 50])]  # 1 face (solo)
    mock_all_emb.return_value = [np.zeros((1, 128), dtype=np.float32)]
    mock_match.return_value = False  # Not us

    source = tmp_path / "trip"
    source.mkdir()
    other_solo = source / "friend_solo.jpg"
    other_solo.touch()
    sidecar = source / "friend_solo.jpg.json"
    sidecar.write_text('{"description": "friend"}')

    ref = tmp_path / "me.jpg"
    ref.touch()
    out = tmp_path / "output"

    res = clean_trip_photos(source, out, person_a_ref=ref, removal_scope="solo_only")

    assert res["removed_others"] == 1
    assert not other_solo.exists()
    assert not sidecar.exists()

    removed_dir = out / "Removed_Other_People"
    assert (removed_dir / "friend_solo.jpg").exists()
    assert (removed_dir / "friend_solo.jpg.json").exists()


@patch("photoflow.face_filter.load_face_engines")
@patch("photoflow.face_filter.extract_primary_embedding")
@patch("photoflow.face_filter.load_image_bgr")
@patch("photoflow.face_filter.detect_faces")
@patch("photoflow.face_filter.extract_all_embeddings")
@patch("photoflow.face_filter.is_match")
def test_clean_trip_photos_other_group_handling(mock_match, mock_all_emb, mock_detect, mock_load_bgr, mock_extract_ref, mock_load_engines, tmp_path):
    mock_load_engines.return_value = (MagicMock(), MagicMock())
    mock_extract_ref.return_value = np.zeros((1, 128), dtype=np.float32)
    mock_load_bgr.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_detect.return_value = [np.array([10, 10, 50, 50]), np.array([70, 70, 50, 50])]  # 2 faces (group)
    mock_all_emb.return_value = [np.zeros((1, 128), dtype=np.float32), np.zeros((1, 128), dtype=np.float32)]
    mock_match.return_value = False  # Neither is us

    source = tmp_path / "trip"
    source.mkdir()
    other_group = source / "others_group.jpg"
    other_group.touch()

    ref = tmp_path / "me.jpg"
    ref.touch()
    out = tmp_path / "output"

    # In "solo_only" mode, other groups are kept!
    res = clean_trip_photos(source, out, person_a_ref=ref, removal_scope="solo_only")
    assert res["kept_other_groups"] == 1
    assert res["removed_others"] == 0
    assert other_group.exists()

    # In "all_without_us" mode, other groups are moved!
    res2 = clean_trip_photos(source, out, person_a_ref=ref, removal_scope="all_without_us")
    assert res2["removed_others"] == 1
    assert not other_group.exists()
    assert (out / "Removed_Other_People" / "others_group.jpg").exists()

