from photoflow.main import PHOTO_EXTENSIONS


def test_heic_is_supported():
    assert ".heic" in PHOTO_EXTENSIONS


def test_heif_is_supported():
    assert ".heif" in PHOTO_EXTENSIONS


def test_hif_is_supported():
    assert ".hif" in PHOTO_EXTENSIONS


def test_jpg_is_supported():
    assert ".jpg" in PHOTO_EXTENSIONS


def test_png_is_supported():
    assert ".png" in PHOTO_EXTENSIONS
