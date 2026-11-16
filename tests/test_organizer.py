from pathlib import Path
from datetime import datetime
import os
import json
import struct
from PIL import Image, ExifTags

from photoflow.organizer import (
    get_photo_timestamp,
    parse_flexible_date,
    parse_filename_date,
    check_google_photos_json,
    extract_quicktime_timestamp,
    unique_destination,
    find_media_files,
    organize_photos_by_date,
)


def test_parse_flexible_date_subseconds():
    dt1 = parse_flexible_date("2024:07:15 14:30:00.542")
    assert dt1 == datetime(2024, 7, 15, 14, 30, 0)

    dt2 = parse_flexible_date("2024-07-15T14:30:00Z")
    assert dt2 == datetime(2024, 7, 15, 14, 30, 0)


def test_parse_filename_date():
    dt1 = parse_filename_date("PXL_20240715_143022123.jpg")
    assert dt1 == datetime(2024, 7, 15, 14, 30, 22)

    dt2 = parse_filename_date("IMG_20240722_180530.heic")
    assert dt2 == datetime(2024, 7, 22, 18, 5, 30)

    dt3 = parse_filename_date("vacation_2024-07-04.jpg")
    assert dt3 == datetime(2024, 7, 4, 0, 0, 0)


def test_check_google_photos_json(tmp_path):
    img_path = tmp_path / "IMG_1234.jpg"
    img_path.touch()

    json_path = tmp_path / "IMG_1234.jpg.json"
    json_path.write_text(json.dumps({
        "photoTakenTime": {
            "timestamp": "1721044800",
            "formatted": "Jul 15, 2024, 12:00:00 PM UTC"
        }
    }))

    dt, source, found_json = check_google_photos_json(img_path)
    assert source == "GooglePhotosJSON"
    assert dt == datetime.fromtimestamp(1721044800)
    assert found_json == json_path


def test_get_photo_timestamp_exif(tmp_path):
    img_path = tmp_path / "test_exif.jpg"
    img = Image.new("RGB", (20, 20), color="blue")

    exif = img.getexif()
    exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
    exif_ifd[ExifTags.Base.DateTimeOriginal] = "2024:07:15 10:45:30"

    img.save(img_path, format="JPEG", exif=exif)

    dt, source, _ = get_photo_timestamp(img_path)
    assert source == "EXIF"
    assert dt == datetime(2024, 7, 15, 10, 45, 30)


def test_get_photo_timestamp_fallback_filename(tmp_path):
    img_path = tmp_path / "PXL_20240718_120000.jpg"
    img_path.write_bytes(b"dummy")

    dt, source, _ = get_photo_timestamp(img_path)
    assert source == "Filename"
    assert dt.month == 7
    assert dt.day == 18
    assert dt.year == 2024


def test_quicktime_mov_timestamp(tmp_path):
    mov_path = tmp_path / "clip.mov"

    # Construct minimal QuickTime MOV header with mvhd creation_time
    target_dt = datetime(2024, 7, 15, 14, 30, 0)
    qt_ts = int(target_dt.timestamp() + 2082844800)

    ftyp = struct.pack(">I4s4sI", 16, b"ftyp", b"qt  ", 512)
    mvhd_payload = struct.pack(">BBBBII", 0, 0, 0, 0, qt_ts, qt_ts) + (b"\x00" * 40)
    mvhd = struct.pack(">I4s", len(mvhd_payload) + 8, b"mvhd") + mvhd_payload
    moov = struct.pack(">I4s", len(mvhd) + 8, b"moov") + mvhd

    mov_path.write_bytes(ftyp + moov)

    dt, source, _ = get_photo_timestamp(mov_path)
    assert source == "QuickTimeHeader"
    assert dt == target_dt


def test_live_photo_mov_pairing(tmp_path):
    # Sibling pair: IMG_0001.jpg (has EXIF) + IMG_0001.mov (plain file)
    img_path = tmp_path / "IMG_0001.jpg"
    im = Image.new("RGB", (10, 10))
    exif = im.getexif()
    exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.DateTimeOriginal] = "2024:07:20 18:00:00"
    im.save(img_path, format="JPEG", exif=exif)

    mov_path = tmp_path / "IMG_0001.mov"
    mov_path.write_bytes(b"dummy-video-bytes")

    dt, source, _ = get_photo_timestamp(mov_path)
    assert "LivePhotoSibling" in source
    assert dt == datetime(2024, 7, 20, 18, 0, 0)


def test_organize_photos_with_sidecar_json(tmp_path):
    source = tmp_path / "source_photos"
    source.mkdir()

    img = source / "photo.jpg"
    img.touch()

    json_sidecar = source / "photo.jpg.json"
    json_sidecar.write_text(json.dumps({
        "photoTakenTime": {"timestamp": "1721044800"}  # July 2024
    }))

    output = tmp_path / "Organized"

    results = organize_photos_by_date(source, output, structure="year_month", action="copy")

    assert results["total"] == 1
    assert results["organized"] == 1
    assert results["sources"]["GooglePhotosJSON"] == 1

    expected_dir = output / "2024" / "2024-07 (July)"
    assert (expected_dir / "photo.jpg").exists()
    assert (expected_dir / "photo.jpg.json").exists()
