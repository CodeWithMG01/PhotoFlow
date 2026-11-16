from pathlib import Path
import os
import shutil
import json
import re
import struct
from datetime import datetime
from PIL import Image, ExifTags
from pillow_heif import register_heif_opener

register_heif_opener()

VIDEO_EXTENSIONS = {".mov", ".mp4", ".m4v"}

SUPPORTED_MEDIA_EXTENSIONS = {
    # Photos
    ".heic", ".heif", ".hif",
    ".jpg", ".jpeg",
    ".png", ".webp", ".bmp", ".tiff",
    ".dng", ".cr2", ".nef", ".arw",
    # Videos (including iPhone Live Photo .mov clips)
    ".mov", ".mp4", ".m4v"
}

FOLDER_STRUCTURES = {
    "year_month": "Year / Month (e.g. 2024 / 2024-08 August)",
    "year_month_day": "Year / Month / Day (e.g. 2024 / 2024-08 / 2024-08-20)",
    "daily": "Daily Folders (e.g. 2024-08-20)",
    "year_only": "Year Only (e.g. 2024)"
}


def parse_flexible_date(raw) -> datetime | None:
    """Parse various EXIF, ISO, and standard date strings, stripping subseconds and timezones."""
    if not raw:
        return None

    s = str(raw).strip().replace("\x00", "")

    # Strip subseconds (e.g. .123456) and timezones (+02:00, -0500, Z)
    clean = re.sub(r"\.\d+", "", s)
    clean = re.sub(r"[\+\-]\d{2}:?\d{2}$", "", clean)
    clean = clean.rstrip("Zz").replace("T", " ")

    for fmt in (
        "%Y:%m:%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y:%m:%d %H:%M",
        "%Y-%m-%d %H:%M",
        "%Y:%m:%d",
        "%Y-%m-%d",
        "%Y%m%d",
    ):
        try:
            return datetime.strptime(clean[:19], fmt)
        except ValueError:
            continue

    return None


def parse_filename_date(filename: str) -> datetime | None:
    """
    Extract capture date from camera/phone filenames.
    Handles Google Pixel (PXL_20240715_...), Samsung (IMG_20240715_... / VID_20240715_...),
    iPhone, WhatsApp (IMG-20240715-WA...), and standard timestamp prefixes.
    """
    # 1. Match Date + Time: YYYYMMDD_HHMMSS or YYYY-MM-DD-HH-MM-SS
    m = re.search(
        r"(?:[^\d]|^)(19\d\d|20\d\d)[-_]?(0[1-9]|1[0-2])[-_]?(0[1-9]|[12]\d|3[01])[-_T ]?(\d{2})[-_:]?(\d{2})[-_:]?(\d{2})",
        filename
    )
    if m:
        y, mo, d, h, mi, s = m.groups()
        try:
            return datetime(int(y), int(mo), int(d), int(h), int(mi), int(s))
        except ValueError:
            pass

    # 2. Match Date only: YYYYMMDD or YYYY-MM-DD
    m2 = re.search(
        r"(?:[^\d]|^)(19\d\d|20\d\d)[-_]?(0[1-9]|1[0-2])[-_]?(0[1-9]|[12]\d|3[01])",
        filename
    )
    if m2:
        y, mo, d = m2.groups()
        try:
            return datetime(int(y), int(mo), int(d))
        except ValueError:
            pass

    return None


def check_google_photos_json(file_path: Path) -> tuple[datetime | None, str | None, Path | None]:
    """
    Check for companion JSON metadata exported by Google Photos / Google Takeout.
    E.g. IMG_1234.mov.json or IMG_1234.json containing photoTakenTime.
    """
    candidates = [
        file_path.with_name(f"{file_path.name}.json"),
        file_path.with_suffix(".json"),
        file_path.parent / f"{file_path.stem}.json",
    ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    if "photoTakenTime" in data and "timestamp" in data["photoTakenTime"]:
                        ts = float(data["photoTakenTime"]["timestamp"])
                        if ts > 0:
                            return datetime.fromtimestamp(ts), "GooglePhotosJSON", candidate

                    if "creationTime" in data and "timestamp" in data["creationTime"]:
                        ts = float(data["creationTime"]["timestamp"])
                        if ts > 0:
                            return datetime.fromtimestamp(ts), "GooglePhotosJSON", candidate
            except Exception:
                continue

    return None, None, None


def extract_quicktime_timestamp(file_path: Path) -> tuple[datetime | None, str | None]:
    """
    Extract the true recording timestamp from QuickTime .mov and MP4 .mp4 container atoms (moov / mvhd).
    Handles Apple iPhone .mov files, Live Photo video pairs, and camera video clips.
    """
    try:
        with open(file_path, "rb") as f:
            file_size = file_path.stat().st_size
            if file_size < 16:
                return None, None

            while f.tell() < file_size:
                pos = f.tell()
                atom_header = f.read(8)
                if len(atom_header) < 8:
                    break

                atom_size, atom_type = struct.unpack(">I4s", atom_header)
                if atom_size == 1:
                    atom_size = struct.unpack(">Q", f.read(8))[0]
                elif atom_size == 0:
                    atom_size = file_size - pos

                if atom_type == b"moov":
                    # Read moov atom contents (up to 10MB to avoid excessive memory)
                    read_len = min(atom_size - 8, 10 * 1024 * 1024)
                    moov_bytes = f.read(read_len)

                    # 1. Check for Apple creation date ISO text string
                    apple_idx = moov_bytes.find(b"com.apple.quicktime.creationdate")
                    if apple_idx != -1:
                        slice_bytes = moov_bytes[apple_idx:apple_idx + 250]
                        m = re.search(rb"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})", slice_bytes)
                        if m:
                            dt_str = m.group(1).decode("utf-8", errors="ignore").replace("T", " ")
                            try:
                                return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S"), "QuickTimeMetadata"
                            except ValueError:
                                pass

                    # 2. Check mvhd atom (Movie Header)
                    mvhd_idx = moov_bytes.find(b"mvhd")
                    if mvhd_idx != -1:
                        idx = mvhd_idx + 4
                        version = moov_bytes[idx]
                        if version == 0:
                            creation_time = struct.unpack(">I", moov_bytes[idx + 4:idx + 8])[0]
                        else:
                            creation_time = struct.unpack(">Q", moov_bytes[idx + 4:idx + 12])[0]

                        # QuickTime epoch difference: Jan 1, 1904 to Jan 1, 1970 = 2082844800 seconds
                        if creation_time > 2082844800:
                            unix_ts = creation_time - 2082844800
                            # Sanity check: between years 1995 and 2045
                            if 788918400 <= unix_ts <= 2367283200:
                                return datetime.fromtimestamp(unix_ts), "QuickTimeHeader"
                    break
                else:
                    if atom_size <= 8:
                        break
                    f.seek(pos + atom_size)
    except Exception:
        pass

    return None, None


def extract_exif_timestamp(file_path: Path) -> tuple[datetime | None, str | None]:
    """Extract embedded capture timestamp from image EXIF, XMP, or GPS tags."""
    try:
        with Image.open(file_path) as img:
            # 1. Check img._getexif() flat dictionary
            if hasattr(img, "_getexif"):
                raw_exif = img._getexif()
                if raw_exif and isinstance(raw_exif, dict):
                    for tag in (36867, 36868, 306):
                        val = raw_exif.get(tag)
                        if val:
                            dt = parse_flexible_date(val)
                            if dt:
                                return dt, "EXIF"

            # 2. Check img.getexif() and IFDs
            exif = img.getexif()
            if exif:
                for tag in (36867, 36868, 306):
                    val = exif.get(tag)
                    if val:
                        dt = parse_flexible_date(val)
                        if dt:
                            return dt, "EXIF"

                try:
                    exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
                    for tag in (ExifTags.Base.DateTimeOriginal, ExifTags.Base.DateTimeDigitized, ExifTags.Base.DateTime):
                        val = exif_ifd.get(tag)
                        if val:
                            dt = parse_flexible_date(val)
                            if dt:
                                return dt, "EXIF"
                except Exception:
                    pass

                try:
                    gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
                    gps_date = gps_ifd.get(29)
                    if gps_date:
                        dt = parse_flexible_date(gps_date)
                        if dt:
                            return dt, "GPS"
                except Exception:
                    pass

            # 3. Check XMP metadata
            if hasattr(img, "getxmp"):
                try:
                    xmp = img.getxmp()
                    if xmp and isinstance(xmp, dict):
                        desc = xmp.get("xmpmeta", {}).get("RDF", {}).get("Description", {})
                        for k in ("CreateDate", "DateTimeOriginal", "DateCreated"):
                            val = desc.get(k)
                            if val:
                                dt = parse_flexible_date(val)
                                if dt:
                                    return dt, "XMP"
                except Exception:
                    pass
    except Exception:
        pass

    return None, None


def get_photo_timestamp(file_path: Path) -> tuple[datetime, str, Path | None]:
    """
    Extract the true original capture timestamp using a resilient multi-layer hierarchy:
    
    For Photos:
      1. Embedded EXIF / XMP / GPS in the photo file (DateTimeOriginal).
      2. Google Photos companion JSON sidecar file.
      3. Intelligent filename pattern parsing (PXL_202407..., IMG_202407...).
      4. Filesystem timestamp as last resort.
      
    For Videos (.mov, .mp4):
      1. Embedded QuickTime container metadata (moov / mvhd creation_time / Apple creationdate).
      2. Companion Live Photo image (e.g. if IMG_1234.mov has IMG_1234.heic / .jpg).
      3. Google Photos companion JSON sidecar file.
      4. Intelligent filename pattern parsing (VID_202407..., IMG_202407...).
      5. Filesystem timestamp as last resort.
    
    Returns (datetime, source_name, companion_json_path_or_None).
    """
    file_path = Path(file_path).resolve()
    ext = file_path.suffix.lower()

    # Special handling for video containers (.mov, .mp4, .m4v)
    if ext in VIDEO_EXTENSIONS:
        # Layer 1: QuickTime atom header
        dt, source = extract_quicktime_timestamp(file_path)
        if dt:
            return dt, source, None

        # Layer 2: Check for companion Live Photo image (e.g. IMG_1234.HEIC or IMG_1234.JPG)
        for img_ext in (".heic", ".jpg", ".jpeg", ".hif", ".png"):
            sibling = file_path.with_suffix(img_ext)
            if not sibling.exists():
                sibling = file_path.with_suffix(img_ext.upper())
            if sibling.exists() and sibling.is_file():
                s_dt, s_source, _ = get_photo_timestamp(sibling)
                if s_source not in ("File", "Default"):
                    return s_dt, f"LivePhotoSibling({s_source})", None

        # Layer 3: Google Photos companion JSON sidecar
        dt, source, json_path = check_google_photos_json(file_path)
        if dt:
            return dt, source, json_path

        # Layer 4: Filename date parsing
        dt = parse_filename_date(file_path.name)
        if dt:
            return dt, "Filename", None

        # Layer 5: File timestamp
        try:
            stat = file_path.stat()
            candidates = [t for t in (stat.st_mtime, getattr(stat, "st_ctime", None)) if t and t > 0]
            ts = min(candidates) if candidates else stat.st_mtime
            return datetime.fromtimestamp(ts), "File", None
        except Exception:
            return datetime.now(), "Default", None

    # Handling for Photos
    # Layer 1: Embedded EXIF / XMP / GPS
    dt, source = extract_exif_timestamp(file_path)
    if dt:
        return dt, source, None

    # Layer 2: Google Photos companion JSON sidecar
    dt, source, json_path = check_google_photos_json(file_path)
    if dt:
        return dt, source, json_path

    # Layer 3: Intelligent Filename date parsing
    dt = parse_filename_date(file_path.name)
    if dt:
        return dt, "Filename", None

    # Layer 4: Filesystem timestamps (Last resort fallback)
    try:
        stat = file_path.stat()
        candidates = [t for t in (stat.st_mtime, getattr(stat, "st_ctime", None)) if t and t > 0]
        ts = min(candidates) if candidates else stat.st_mtime
        return datetime.fromtimestamp(ts), "File", None
    except Exception:
        return datetime.now(), "Default", None


def unique_destination(destination: Path) -> Path:
    """Generate a unique file path if a file with the same name already exists."""
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


def find_media_files(source_folder: Path, output_folder: Path = None) -> list[Path]:
    """Find all supported photo and video files, ignoring the output folder."""
    source_folder = Path(source_folder).resolve()
    output_folder = Path(output_folder).resolve() if output_folder else None

    media_files = []

    for file_path in source_folder.rglob("*"):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in SUPPORTED_MEDIA_EXTENSIONS:
            continue

        if output_folder and (output_folder == file_path.resolve() or output_folder in file_path.resolve().parents):
            continue

        media_files.append(file_path)

    return sorted(media_files)


def build_destination_subpath(dt: datetime, structure: str) -> Path:
    """Construct subfolder path based on the chosen folder structure."""
    year = dt.strftime("%Y")
    month_num = dt.strftime("%m")
    month_name = dt.strftime("%B")
    day = dt.strftime("%d")

    if structure == "year_month":
        return Path(year) / f"{year}-{month_num} ({month_name})"
    elif structure == "year_month_day":
        return Path(year) / f"{year}-{month_num}" / f"{year}-{month_num}-{day}"
    elif structure == "daily":
        return Path(f"{year}-{month_num}-{day}")
    elif structure == "year_only":
        return Path(year)
    else:
        return Path(year) / f"{year}-{month_num}"


def organize_photos_by_date(
    source_folder: Path,
    output_folder: Path,
    structure: str = "year_month",
    action: str = "copy",  # "copy" or "move"
    rename_files: bool = False,
    progress_callback=None,
    cancel_event=None
) -> dict:
    """
    Sort and organize photo and video collections into date-based folders using true capture timestamps.
    """
    source_folder = Path(source_folder).resolve()
    output_folder = Path(output_folder).resolve()

    if not source_folder.is_dir():
        raise ValueError("Source folder does not exist.")

    if source_folder == output_folder or output_folder in source_folder.parents:
        raise ValueError("Output folder cannot be the source folder or a parent directory.")

    files = find_media_files(source_folder, output_folder)

    results = {
        "total": len(files),
        "organized": 0,
        "failed": 0,
        "sources": {},
        "years": {},
        "cancelled": False,
        "errors": []
    }

    if not files:
        return results

    for index, file_path in enumerate(files, start=1):
        if cancel_event and cancel_event.is_set():
            results["cancelled"] = True
            break

        try:
            dt, source_type, json_sidecar = get_photo_timestamp(file_path)
            results["sources"][source_type] = results["sources"].get(source_type, 0) + 1

            year_str = dt.strftime("%Y")
            results["years"][year_str] = results["years"].get(year_str, 0) + 1

            if rename_files:
                time_prefix = dt.strftime("%Y%m%d_%H%M%S")
                target_filename = f"{time_prefix}_{file_path.name}"
            else:
                target_filename = file_path.name

            subpath = build_destination_subpath(dt, structure)
            target_dir = output_folder / subpath
            target_dir.mkdir(parents=True, exist_ok=True)

            destination = unique_destination(target_dir / target_filename)

            if action == "move":
                shutil.move(str(file_path), str(destination))
            else:
                shutil.copy2(str(file_path), str(destination))

            # Set file modified and access timestamps to the REAL photo/video date
            try:
                os.utime(destination, (dt.timestamp(), dt.timestamp()))
            except OSError:
                pass

            # Copy/move companion JSON sidecar if present
            if json_sidecar and json_sidecar.exists():
                json_dest = target_dir / json_sidecar.name
                try:
                    if action == "move":
                        shutil.move(str(json_sidecar), str(json_dest))
                    else:
                        shutil.copy2(str(json_sidecar), str(json_dest))
                except Exception:
                    pass

            results["organized"] += 1

        except Exception as err:
            results["failed"] += 1
            results["errors"].append(f"{file_path.name}: {err}")

        if progress_callback:
            progress_callback(index, len(files), file_path.name)

    return results
