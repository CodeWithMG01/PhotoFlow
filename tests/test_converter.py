from pathlib import Path
import os
import time

import pytest
from PIL import Image

from photoflow.converter import (
    find_heic_files,
    unique_destination,
    convert_image,
    convert_folder,
    SUPPORTED_FORMATS,
)


def test_find_heic_files(tmp_path):
    source = tmp_path / "photos"
    source.mkdir()

    (source / "photo1.HEIC").touch()
    (source / "photo2.heif").touch()
    (source / "photo3.hif").touch()
    (source / "photo4.jpg").touch()

    output = source / "Converted_JPG"
    output.mkdir()
    (output / "previously_converted.heic").touch()

    photos = find_heic_files(source, output)

    assert len(photos) == 3
    assert all(p.parent != output for p in photos)


def test_unique_destination(tmp_path):
    destination = tmp_path / "photo.jpg"
    destination.touch()

    result = unique_destination(destination)

    assert result.name == "photo_2.jpg"


def test_convert_image(tmp_path):
    source = tmp_path / "test.heic"
    destination = tmp_path / "test.jpg"

    # Create a sample HEIC image for testing
    image = Image.new("RGB", (100, 100), color="red")
    image.save(source, format="HEIF")

    result = convert_image(source, destination)

    assert result.exists()

    with Image.open(result) as converted:
        assert converted.format == "JPEG"
        assert converted.size == (100, 100)


def test_invalid_quality(tmp_path):
    source = tmp_path / "test.heic"
    destination = tmp_path / "test.jpg"

    with pytest.raises(ValueError):
        convert_image(source, destination, quality=110)


def test_convert_preserves_exif(tmp_path):
    source = tmp_path / "test_exif.heic"
    destination = tmp_path / "test_exif.jpg"

    # Create HEIF with EXIF tags (Make, Model)
    image = Image.new("RGB", (50, 50), color="blue")
    exif = image.getexif()
    exif[0x010F] = "Apple"
    exif[0x0110] = "iPhone 15 Pro"
    image.save(source, format="HEIF", exif=exif)

    result = convert_image(source, destination)

    with Image.open(result) as converted:
        converted_exif = converted.getexif()
        assert converted_exif.get(0x010F) == "Apple"
        assert converted_exif.get(0x0110) == "iPhone 15 Pro"


def test_convert_preserves_icc_profile(tmp_path):
    source = tmp_path / "test_icc.heic"
    destination = tmp_path / "test_icc.jpg"

    # Create an image with simulated ICC profile bytes
    dummy_icc = b"ICC_PROFILE_TEST_DATA" * 10
    image = Image.new("RGB", (50, 50), color="green")
    image.info["icc_profile"] = dummy_icc
    image.save(source, format="HEIF", icc_profile=dummy_icc)

    result = convert_image(source, destination)

    with Image.open(result) as converted:
        assert converted.info.get("icc_profile") is not None


def test_convert_preserves_timestamps(tmp_path):
    source = tmp_path / "test_time.heic"
    destination = tmp_path / "test_time.jpg"

    image = Image.new("RGB", (50, 50), color="yellow")
    image.save(source, format="HEIF")

    # Set custom past timestamp
    past_timestamp = 1600000000.0
    os.utime(source, (past_timestamp, past_timestamp))

    result = convert_image(source, destination)

    assert abs(result.stat().st_mtime - past_timestamp) < 2.0


def test_convert_handles_transparency(tmp_path):
    source = tmp_path / "transparent.heic"
    destination = tmp_path / "transparent.jpg"

    # Create an RGBA image with fully transparent pixels
    rgba = Image.new("RGBA", (10, 10), color=(255, 0, 0, 0))
    rgba.save(source, format="HEIF")

    result = convert_image(source, destination)

    with Image.open(result) as converted:
        assert converted.mode == "RGB"
        # The transparent pixel should be composited onto white (255, 255, 255)
        pixel = converted.getpixel((0, 0))
        assert pixel == (255, 255, 255)


def test_convert_folder_nested_and_output_inside_source(tmp_path):
    source = tmp_path / "source_photos"
    source.mkdir()

    sub = source / "holiday"
    sub.mkdir()

    img1 = Image.new("RGB", (20, 20), color="red")
    img1.save(source / "img1.heic", format="HEIF")

    img2 = Image.new("RGB", (20, 20), color="blue")
    img2.save(sub / "img2.heif", format="HEIF")

    output = source / "Converted_JPG"

    results = convert_folder(source, output, quality=95)

    assert results["total"] == 2
    assert results["converted"] == 2
    assert results["failed"] == 0
    assert (output / "img1.jpg").exists()
    assert (output / "holiday" / "img2.jpg").exists()
