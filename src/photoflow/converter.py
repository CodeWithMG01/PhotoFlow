from pathlib import Path
import os
import threading
import concurrent.futures
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()

SUPPORTED_FORMATS = {".heic", ".heif", ".hif"}
PHOTO_EXTENSIONS = {".heic", ".heif", ".hif", ".jpg", ".jpeg", ".png"}


def find_heic_files(source: Path, output: Path) -> list[Path]:
    """Find HEIC, HEIF, and HIF files, excluding the output folder."""

    source = source.resolve()
    output = output.resolve()

    photos = []

    for file_path in source.rglob("*"):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in SUPPORTED_FORMATS:
            continue

        # Do not scan previously converted photos
        if output == file_path.resolve() or output in file_path.resolve().parents:
            continue

        photos.append(file_path)

    return sorted(photos)


def unique_destination(destination: Path) -> Path:
    """Generate a filename without overwriting existing files."""

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


def convert_image(
    source: Path,
    destination: Path,
    quality: int = 95
) -> Path:
    """Convert one HEIC/HEIF/HIF image into JPG without losing quality or metadata."""

    source = Path(source).resolve()
    destination = Path(destination).resolve()

    if not 1 <= quality <= 100:
        raise ValueError("Quality must be between 1 and 100.")

    if source.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValueError("Unsupported image format.")

    destination.parent.mkdir(parents=True, exist_ok=True)

    # Never overwrite an existing JPG
    destination = unique_destination(destination)

    with Image.open(source) as image:
        # Extract ICC color profile (e.g. Display P3) and DPI resolution
        icc_profile = image.info.get("icc_profile")
        dpi = image.info.get("dpi")

        # Correct rotation based on EXIF tag and retrieve updated EXIF
        image = ImageOps.exif_transpose(image)
        exif = image.getexif()

        # Handle alpha transparency safely (composite over white)
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            rgba = image.convert("RGBA")
            background = Image.new("RGB", rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.split()[3])
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")

        # Prepare save parameters with full chroma fidelity (subsampling=0)
        save_kwargs = {
            "format": "JPEG",
            "quality": quality,
            "optimize": True,
            "subsampling": 0,  # 4:4:4 full color fidelity
        }
        if icc_profile:
            save_kwargs["icc_profile"] = icc_profile
        if exif and len(exif) > 0:
            save_kwargs["exif"] = exif
        if dpi:
            save_kwargs["dpi"] = dpi

        image.save(destination, **save_kwargs)

    # Preserve original filesystem modification and access timestamps
    try:
        stat = source.stat()
        os.utime(destination, (stat.st_atime, stat.st_mtime))
    except OSError:
        pass

    return destination


def convert_folder(
    source_folder: Path,
    output_folder: Path,
    quality: int = 95,
    progress_callback=None,
    cancel_event=None,
    max_workers: int = None
) -> dict:
    """Convert all HEIC/HEIF/HIF images in a folder and its subfolders."""

    source_folder = Path(source_folder).resolve()
    output_folder = Path(output_folder).resolve()

    if not source_folder.is_dir():
        raise ValueError("Source folder does not exist.")

    if source_folder == output_folder or output_folder in source_folder.parents:
        raise ValueError("Output folder must not be the source folder or a parent of it.")

    if not 1 <= quality <= 100:
        raise ValueError("Quality must be between 1 and 100.")

    photos = find_heic_files(source_folder, output_folder)

    results = {
        "total": len(photos),
        "converted": 0,
        "failed": 0,
        "cancelled": False,
        "errors": []
    }

    if not photos:
        return results

    if max_workers is None:
        max_workers = min(8, os.cpu_count() or 4)

    # Sequential execution for 1 worker or single file
    if max_workers <= 1 or len(photos) == 1:
        for index, photo in enumerate(photos, start=1):
            if cancel_event and cancel_event.is_set():
                results["cancelled"] = True
                break

            try:
                relative_path = photo.relative_to(source_folder)
                destination = (
                    output_folder
                    / relative_path.parent
                    / f"{photo.stem}.jpg"
                )
                convert_image(photo, destination, quality)
                results["converted"] += 1
            except Exception as error:
                results["failed"] += 1
                results["errors"].append(f"{photo.name}: {error}")

            if progress_callback:
                progress_callback(index, len(photos))
    else:
        # Multi-threaded execution for high throughput
        processed_count = 0
        lock = threading.Lock()

        def _process_single(photo: Path):
            if cancel_event and cancel_event.is_set():
                return None, None
            try:
                relative_path = photo.relative_to(source_folder)
                destination = (
                    output_folder
                    / relative_path.parent
                    / f"{photo.stem}.jpg"
                )
                convert_image(photo, destination, quality)
                return True, None
            except Exception as error:
                return False, f"{photo.name}: {error}"

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_photo = {
                executor.submit(_process_single, p): p for p in photos
            }

            for future in concurrent.futures.as_completed(future_to_photo):
                if cancel_event and cancel_event.is_set():
                    results["cancelled"] = True
                    for f in future_to_photo:
                        f.cancel()
                    break

                try:
                    success, err = future.result()
                    if success is True:
                        with lock:
                            results["converted"] += 1
                    elif success is False:
                        with lock:
                            results["failed"] += 1
                            if err:
                                results["errors"].append(err)
                except Exception as exc:
                    with lock:
                        results["failed"] += 1
                        results["errors"].append(str(exc))

                with lock:
                    processed_count += 1
                    current_processed = processed_count

                if progress_callback:
                    progress_callback(current_processed, len(photos))

    return results
