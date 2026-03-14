#!/home/daniel/.pyenv/versions/gvmm-py3/bin/python3

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from PIL import Image, ImageFile


Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Watch an input directory for PNG files that have a matching JPG in a "
            "destination directory, convert them to JPG, and atomically replace "
            "the destination image."
        )
    )
    parser.add_argument("input_dir", help="Directory to monitor for PNG files")
    parser.add_argument(
        "destination_dir",
        help="Directory that already contains the JPG files to be replaced",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Seconds between scans when watching continuously (default: 1.0)",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=95,
        help="JPEG quality used for conversion (default: 95)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Scan once and exit instead of watching continuously",
    )
    return parser


def normalize_image(image: Image.Image) -> Image.Image:
    if image.mode in ("RGB", "L"):
        return image.convert("RGB")

    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(background, rgba).convert("RGB")

    return image.convert("RGB")


def convert_png_to_jpg(src_png: Path, dest_jpg: Path, quality: int) -> None:
    tmp_jpg = dest_jpg.with_suffix(dest_jpg.suffix + ".tmp")

    with Image.open(src_png) as image:
        rgb_image = normalize_image(image)
        rgb_image.save(
            tmp_jpg,
            format="JPEG",
            quality=quality,
            optimize=False,
            progressive=False,
        )

    os.replace(tmp_jpg, dest_jpg)
    src_png.unlink()


def png_candidates(input_dir: Path) -> list[Path]:
    return sorted(path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() == ".png")


def process_ready_pngs(
    input_dir: Path,
    destination_dir: Path,
    quality: int,
    observed: dict[Path, tuple[int, int]],
    ready_after_stable_scan: bool,
) -> None:
    current_pngs = set()

    for png_path in png_candidates(input_dir):
        current_pngs.add(png_path)
        try:
            stat = png_path.stat()
        except FileNotFoundError:
            continue

        fingerprint = (stat.st_size, stat.st_mtime_ns)
        previous = observed.get(png_path)
        observed[png_path] = fingerprint

        if previous is None:
            continue
        if previous != fingerprint:
            continue
        if not ready_after_stable_scan:
            continue

        dest_jpg = destination_dir / f"{png_path.stem}.jpg"
        if not dest_jpg.exists():
            continue

        try:
            convert_png_to_jpg(png_path, dest_jpg, quality)
            print(f"converted {png_path.name} -> {dest_jpg}")
        except Exception as exc:  # pragma: no cover - surfaced to user directly
            print(f"failed to convert {png_path}: {exc}", file=sys.stderr)

    for stale_path in list(observed):
        if stale_path not in current_pngs:
            del observed[stale_path]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    input_dir = Path(args.input_dir).expanduser().resolve()
    destination_dir = Path(args.destination_dir).expanduser().resolve()

    if not input_dir.is_dir():
        print(f"input directory does not exist: {input_dir}", file=sys.stderr)
        return 2
    if not destination_dir.is_dir():
        print(f"destination directory does not exist: {destination_dir}", file=sys.stderr)
        return 2
    if input_dir == destination_dir:
        print("input and destination directories must be different", file=sys.stderr)
        return 2

    observed: dict[Path, tuple[int, int]] = {}

    if args.once:
        process_ready_pngs(input_dir, destination_dir, args.quality, observed, False)
        process_ready_pngs(input_dir, destination_dir, args.quality, observed, True)
        return 0

    print(f"watching {input_dir} for PNG files matching JPGs in {destination_dir}")
    while True:
        process_ready_pngs(input_dir, destination_dir, args.quality, observed, True)
        time.sleep(args.poll_interval)


if __name__ == "__main__":
    raise SystemExit(main())
