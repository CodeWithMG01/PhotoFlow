from pathlib import Path
import subprocess
import pytest

from photoflow.video_converter import (
    get_ffmpeg_path,
    find_mov_files,
    unique_destination,
    convert_video,
    convert_video_folder,
)


def test_get_ffmpeg_path():
    path = get_ffmpeg_path()
    assert Path(path).exists()


def test_find_mov_files(tmp_path):
    source = tmp_path / "videos"
    source.mkdir()

    (source / "clip1.mov").touch()
    (source / "clip2.MOV").touch()
    (source / "clip3.m4v").touch()
    (source / "clip4.mp4").touch()
    (source / "photo.jpg").touch()

    output = source / "Converted_MP4"
    output.mkdir()
    (output / "previously_converted.mov").touch()

    movs = find_mov_files(source, output)
    assert len(movs) == 3
    assert all(m.parent != output for m in movs)


def test_unique_destination(tmp_path):
    dest = tmp_path / "video.mp4"
    dest.touch()

    candidate = unique_destination(dest)
    assert candidate.name == "video_2.mp4"


def test_convert_video(tmp_path):
    ffmpeg_bin = get_ffmpeg_path()
    src = tmp_path / "sample.mov"
    dst = tmp_path / "output.mp4"

    # Create a 1-second synthetic color video using ffmpeg
    subprocess.run([
        ffmpeg_bin, "-y", "-f", "lavfi", "-i", "color=c=green:s=160x120:d=1",
        "-c:v", "libx264", str(src)
    ], check=True, capture_output=True)

    result = convert_video(src, dst, crf=22, preset="ultrafast")
    assert result.exists()
    assert result.suffix == ".mp4"
    assert result.stat().st_size > 500


def test_convert_video_folder(tmp_path):
    ffmpeg_bin = get_ffmpeg_path()
    source = tmp_path / "mov_folder"
    source.mkdir()
    output = tmp_path / "mp4_folder"

    src = source / "clip.mov"
    subprocess.run([
        ffmpeg_bin, "-y", "-f", "lavfi", "-i", "color=c=red:s=160x120:d=1",
        "-c:v", "libx264", str(src)
    ], check=True, capture_output=True)

    results = convert_video_folder(source, output, crf=22)
    assert results["total"] == 1
    assert results["converted"] == 1
    assert (output / "clip.mp4").exists()
