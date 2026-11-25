#!/usr/bin/env python3
"""Entry script for the make.fun bounty "Sum up 25 November's world news
in one image" (competition ``news-image-20261125``).

The entry itself is ``entry.png`` — a newspaper front page ("THE WORLD
TODAY", Wednesday, November 25, 2026) drawn with PIL in this session,
summing up that day's biggest world stories:

* CIA and the Office of the Director of National Intelligence hit by a
  hack of their unclassified systems (no classified data touched);
* a US jury convicts Huawei on 10 of 12 counts, including stealing
  trade secrets;
* Houthis strike a tower in Riyadh's finance district, injuring 11 —
  the tower's second attack in a week;
* Israel warns Iran is developing chemical weapons, with US-Israeli
  strike plans drawn up;
* China opens an investigation into Politburo member and Shanghai
  party chief Chen Jining;
* NATO sends AWACS radar planes to Poland after Russian missiles
  landed there;
* the WHO evacuates health workers from an Ebola-treatment hospital
  in Ituri, DR Congo, after three days sheltering from fighting.

Running this script copies ``entry.png`` (which lives next to this
file) to ``/output/entry.png``. It is deliberately deterministic: no
network access, no image processing, no randomness — just a plain file
copy, followed by checks that the copy is a whole, well-formed PNG of
the expected size, byte for byte identical to the source. Any problem
(a missing source, a wrong signature, wrong dimensions, a size over
the 1 MiB bounty cap, or a hash mismatch after the copy) fails loudly
with a non-zero exit code instead of silently producing a broken
output.

Usage:
    python3 main.py
"""

import hashlib
import shutil
import struct
import sys
from pathlib import Path

# The entry image, resolved relative to this file so the script works
# from any working directory.
SOURCE = Path(__file__).parent / "entry.png"
# The fixed output location the bounty harness reads from.
DEST = Path("/output/entry.png")

# What the gate requires of the entry image.
EXPECTED_WIDTH = 1024
EXPECTED_HEIGHT = 1024
MAX_BYTES = 1_048_576  # 1 MiB
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def sha256_of(path: Path) -> str:
    """Return the hex SHA-256 digest of a file's bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_png_dimensions(path: Path) -> tuple[int, int]:
    """Parse width and height out of a PNG file's IHDR chunk.

    Raises:
        ValueError: if the file is not a PNG or its IHDR is malformed.
    """
    with path.open("rb") as handle:
        header = handle.read(33)
    if len(header) < 33 or header[:8] != PNG_SIGNATURE:
        raise ValueError(f"not a PNG file (bad signature): {path}")
    length, chunk_type = struct.unpack(">I4s", header[8:16])
    if chunk_type != b"IHDR" or length != 13:
        raise ValueError(f"not a PNG file (missing IHDR): {path}")
    width, height = struct.unpack(">II", header[16:24])
    return width, height


def validate_entry(path: Path) -> str:
    """Check the entry image against the bounty gate; return its hash.

    Raises:
        FileNotFoundError: if the entry image does not exist.
        ValueError: if any gate check fails.
    """
    if not path.is_file():
        raise FileNotFoundError(f"entry image not found: {path}")

    size = path.stat().st_size
    if size > MAX_BYTES:
        raise ValueError(
            f"entry image too large: {size} bytes (cap {MAX_BYTES})"
        )

    width, height = read_png_dimensions(path)
    if (width, height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
        raise ValueError(
            f"unexpected dimensions: {width}x{height}, "
            f"expected {EXPECTED_WIDTH}x{EXPECTED_HEIGHT}"
        )

    return sha256_of(path)


def copy_entry(source: Path, dest: Path) -> tuple[int, str]:
    """Copy ``source`` to ``dest`` and verify the copy; return (bytes, hash).

    The copy is only trusted once the destination file hashes to the
    same digest as the source, so a truncated or corrupted write is
    caught here rather than at grading time.

    Raises:
        FileNotFoundError: if the source image does not exist.
        ValueError: if the copied file differs from the source.
    """
    source_hash = validate_entry(source)

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)

    dest_hash = sha256_of(dest)
    if dest_hash != source_hash:
        raise ValueError(
            f"hash mismatch after copy: source {source_hash}, "
            f"destination {dest_hash}"
        )
    return dest.stat().st_size, dest_hash


def main() -> int:
    try:
        byte_count, image_hash = copy_entry(SOURCE, DEST)
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Copied {SOURCE} -> {DEST}")
    print(f"  bytes : {byte_count}")
    print(f"  sha256: {image_hash}")
    print(f"  size  : {EXPECTED_WIDTH}x{EXPECTED_HEIGHT} PNG")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
