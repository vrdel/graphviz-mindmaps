from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

from graphviz_mindmaps.tools.montage import normalize_spec, parse_yaml_like


MINDMAP_SUFFIXES = {".otl"}
MONTAGE_SUFFIXES = {".yml", ".yaml"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
JUSTFILE_NAMES = {"justfile", "Justfile"}
JUSTFILE_SUFFIXES = {".just"}
REFERENCE_SUFFIXES = MINDMAP_SUFFIXES | MONTAGE_SUFFIXES | {
    ".wiki",
    ".html",
    ".htm",
} | IMAGE_SUFFIXES


def is_justfile(path: Path) -> bool:
    return path.name in JUSTFILE_NAMES or path.suffix in JUSTFILE_SUFFIXES


def resolve_reference(base: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return base.parent / path


def add_existing(path: Path, files: dict[Path, Path]) -> None:
    resolved = path.resolve(strict=False)
    if resolved.exists():
        files[resolved] = path


def parse_just_assignments(text: str) -> list[str]:
    values: list[str] = []
    assignment = re.compile(r"""^\s*[A-Za-z_][A-Za-z0-9_-]*\s*:?=\s*(.+?)\s*$""")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = assignment.match(line)
        if not match:
            continue
        value = match.group(1).split("#", 1)[0].strip()
        if len(value) >= 2 and value[0] in {"'", '"'} and value[-1] == value[0]:
            value = value[1:-1]
        if Path(value).suffix.lower() in REFERENCE_SUFFIXES:
            values.append(value)
    return values


def collect_justfile(path: Path, files: dict[Path, Path]) -> None:
    if not path.exists():
        return
    add_existing(path, files)
    for value in parse_just_assignments(path.read_text()):
        collect_path(resolve_reference(path, value), files)


def collect_montage_images(spec: object) -> list[str]:
    images: list[str] = []
    if isinstance(spec, str):
        images.append(spec)
        return images
    if isinstance(spec, list):
        for item in spec:
            images.extend(collect_montage_images(item))
        return images
    if isinstance(spec, dict):
        for row in spec.get("rows", []):
            images.extend(collect_montage_images(row))
    return images


def collect_montage(path: Path, files: dict[Path, Path]) -> None:
    if not path.exists():
        return
    add_existing(path, files)
    parsed = parse_yaml_like(path.read_text())
    normalized = normalize_spec(parsed)
    for image in collect_montage_images(normalized):
        image_path = resolve_reference(path, image)
        add_existing(image_path, files)
        if image_path.suffix.lower() in IMAGE_SUFFIXES:
            collect_mindmap(image_path.with_suffix(".otl"), files)


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] in {"'", '"'} and value[-1] == value[0]:
        return value[1:-1]
    return value


def collect_mindmap(path: Path, files: dict[Path, Path]) -> None:
    if not path.exists():
        return
    add_existing(path, files)
    text = path.read_text()
    for match in re.finditer(r"""(?<!\S)(?:img|fname)=("[^"]+"|'[^']+'|[^\s]+)""", text):
        value = unquote(match.group(1))
        add_existing(resolve_reference(path, value), files)


def collect_path(path: Path, files: dict[Path, Path]) -> None:
    suffix = path.suffix.lower()
    if suffix in MINDMAP_SUFFIXES:
        collect_mindmap(path, files)
    elif suffix in MONTAGE_SUFFIXES:
        collect_montage(path, files)
    elif is_justfile(path):
        collect_justfile(path, files)
    else:
        add_existing(path, files)


def collect_related_files(source: Path) -> list[Path]:
    files: dict[Path, Path] = {}
    collect_path(source, files)
    return sorted(files)


def validate_destinations(files: list[Path], target_dir: Path) -> None:
    by_name: dict[str, Path] = {}
    for path in files:
        existing = by_name.get(path.name)
        if existing and existing != path:
            raise SystemExit(
                "destination name conflict: %s and %s both map to %s"
                % (existing, path, target_dir / path.name)
            )
        by_name[path.name] = path


def transfer_files(files: list[Path], target_dir: Path, move: bool, dry_run: bool) -> None:
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)
    validate_destinations(files, target_dir)
    action = shutil.move if move else shutil.copy2
    verb = "mv" if move else "cp"

    for src in files:
        dst = target_dir / src.name
        if src == dst.resolve(strict=False):
            print("skip %s" % src)
            continue
        if dst.exists():
            raise SystemExit("destination exists: %s" % dst)
        print("%s %s %s" % (verb, src, dst))
        if not dry_run:
            action(src, dst)


def build_parser(prog: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog)
    parser.add_argument("source", help="mindmap .otl, montage .yml/.yaml, or justfile")
    parser.add_argument("target_dir", help="directory to copy/move related files into")
    parser.add_argument("-n", "--dry-run", action="store_true", help="show files without copying/moving")
    return parser


def run(argv: list[str] | None, move: bool, prog: str) -> int:
    parser = build_parser(prog)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    source = Path(args.source)
    if not source.exists():
        parser.error("source does not exist: %s" % source)

    files = collect_related_files(source)
    transfer_files(files, Path(args.target_dir), move=move, dry_run=args.dry_run)
    return 0
