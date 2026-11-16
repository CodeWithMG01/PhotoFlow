from pathlib import Path
import os
import subprocess
import imageio_ffmpeg

SUPPORTED_VIDEO_INPUTS = {".mov", ".m4v", ".qt"}


def get_ffmpeg_path() -> str:
    """Return the absolute path to the bundled FFmpeg binary."""
    return imageio_ffmpeg.get_ffmpeg_exe()


def find_mov_files(source: Path, output: Path = None) -> list[Path]:
    """Find all .mov and QuickTime video files in source, excluding output folder."""
    source = Path(source).resolve()
    output = Path(output).resolve() if output else None

    videos = []
    for file_path in source.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SUPPORTED_VIDEO_INPUTS:
            continue
        if output and (output == file_path.resolve() or output in file_path.resolve().parents):
            continue
        videos.append(file_path)

    return sorted(videos)


def unique_destination(destination: Path) -> Path:
    """Generate a unique filename avoiding overwrite."""
    if not destination.exists():
        return destination

    counter = 2
    while True:
        candidate = destination.with_name(
            f"{destination.stem}_{counter}{destination.suffix}"
        )
        if not candidate.exists():
            return candidate
        counter += 1


def convert_video(
    source: Path,
    destination: Path,
    crf: int = 20,
    preset: str = "fast",
    cancel_event=None
) -> Path:
    """
    Convert an Apple .mov video into universal Windows-compatible .mp4 (H.264 / AAC / yuv420p).
    
    Preserves original timestamps and ensures immediate playback compatibility.
    """
    source = Path(source).resolve()
    destination = Path(destination).resolve()

    if not source.is_file():
        raise FileNotFoundError(f"Source video not found: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination = unique_destination(destination)

    ffmpeg_bin = get_ffmpeg_path()

    cmd = [
        ffmpeg_bin,
        "-y",
        "-nostats",
        "-loglevel", "error",
        "-i", str(source),
        "-vcodec", "libx264",
        "-crf", str(crf),
        "-preset", preset,
        "-pix_fmt", "yuv420p",
        "-acodec", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(destination)
    ]

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        creationflags=creationflags
    )

    stderr_output = b""
    while True:
        if cancel_event and cancel_event.is_set():
            process.kill()
            if destination.exists():
                try:
                    destination.unlink()
                except OSError:
                    pass
            raise InterruptedError("Video conversion cancelled.")
        try:
            _, stderr_output = process.communicate(timeout=0.2)
            break
        except subprocess.TimeoutExpired:
            continue

    if process.returncode != 0:
        err_msg = stderr_output.decode("utf-8", errors="ignore")
        if destination.exists():
            try:
                destination.unlink()
            except OSError:
                pass
        raise RuntimeError(f"FFmpeg failed (code {process.returncode}): {err_msg[-400:]}")

    # Preserve source access and modified timestamps
    try:
        stat = source.stat()
        os.utime(destination, (stat.st_atime, stat.st_mtime))
    except OSError:
        pass

    return destination


def convert_video_folder(
    source_folder: Path,
    output_folder: Path,
    crf: int = 20,
    progress_callback=None,
    cancel_event=None
) -> dict:
    """Batch convert all .mov files in source_folder into .mp4 files inside output_folder."""
    source_folder = Path(source_folder).resolve()
    output_folder = Path(output_folder).resolve()

    if not source_folder.is_dir():
        raise ValueError("Source folder does not exist.")

    if source_folder == output_folder or output_folder in source_folder.parents:
        raise ValueError("Output folder cannot be the source folder or a parent directory.")

    videos = find_mov_files(source_folder, output_folder)

    results = {
        "total": len(videos),
        "converted": 0,
        "failed": 0,
        "cancelled": False,
        "errors": []
    }

    if not videos:
        return results

    for index, video in enumerate(videos, start=1):
        if cancel_event and cancel_event.is_set():
            results["cancelled"] = True
            break

        try:
            relative_path = video.relative_to(source_folder)
            destination = (
                output_folder
                / relative_path.parent
                / f"{video.stem}.mp4"
            )

            convert_video(video, destination, crf=crf, cancel_event=cancel_event)
            results["converted"] += 1

        except InterruptedError:
            results["cancelled"] = True
            break
        except Exception as error:
            results["failed"] += 1
            results["errors"].append(f"{video.name}: {error}")

        if progress_callback:
            progress_callback(index, len(videos), video.name)

    return results
