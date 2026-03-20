#!/home/daniel/.pyenv/versions/gvmm-py3/bin/python3

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TITLE_BACKGROUND = "#a0a0a0"
UNTITLED_NESTED_BACKGROUND = "#efefef"


def strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    escaped = False
    out = []

    for ch in line:
        if escaped:
            out.append(ch)
            escaped = False
            continue
        if ch == "\\":
            out.append(ch)
            escaped = True
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            out.append(ch)
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            out.append(ch)
            continue
        if ch == "#" and not in_single and not in_double:
            break
        out.append(ch)

    return "".join(out).rstrip()


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value[0] in {"'", '"'} and value[-1] == value[0]:
        return value[1:-1]
    if value == "null":
        return None
    if value in {"true", "false"}:
        return value == "true"
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if value.startswith("[") and value.endswith("]"):
        return parse_inline_list(value[1:-1])
    return value


def parse_inline_list(body: str) -> list[Any]:
    lexer = shlex.shlex(body, posix=True)
    lexer.whitespace = ","
    lexer.whitespace_split = True
    lexer.commenters = ""
    return [parse_scalar(token) for token in lexer if token.strip()]


@dataclass
class ParsedLine:
    indent: int
    content: str


def preprocess_yaml_lines(text: str) -> list[ParsedLine]:
    lines: list[ParsedLine] = []
    for raw in text.splitlines():
        cleaned = strip_comment(raw)
        if not cleaned.strip():
            continue
        stripped = cleaned.lstrip(" ")
        indent = len(cleaned) - len(stripped)
        if "\t" in cleaned[:indent]:
            raise ValueError("tabs are not supported in YAML indentation")
        lines.append(ParsedLine(indent=indent, content=stripped))
    return lines


def parse_yaml_like(text: str) -> Any:
    lines = preprocess_yaml_lines(text)
    if not lines:
        return {}
    value, next_index = parse_block(lines, 0, lines[0].indent)
    if next_index != len(lines):
        raise ValueError("unexpected trailing content")
    return value


def parse_block(lines: list[ParsedLine], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index
    if lines[index].indent != indent:
        raise ValueError("invalid indentation")
    if lines[index].content.startswith("- "):
        return parse_list(lines, index, indent)
    return parse_dict(lines, index, indent)


def parse_dict(lines: list[ParsedLine], index: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}

    while index < len(lines):
        line = lines[index]
        if line.indent < indent:
            break
        if line.indent > indent:
            raise ValueError(f"unexpected indentation near: {line.content}")
        if line.content.startswith("- "):
            break
        if ":" not in line.content:
            raise ValueError(f"expected key/value pair near: {line.content}")

        key, rest = line.content.split(":", 1)
        key = key.strip()
        rest = rest.strip()
        index += 1

        if rest:
            result[key] = parse_scalar(rest)
            continue

        if index < len(lines) and lines[index].indent > indent:
            result[key], index = parse_block(lines, index, lines[index].indent)
        else:
            result[key] = {}

    return result, index


def parse_list(lines: list[ParsedLine], index: int, indent: int) -> tuple[list[Any], int]:
    result: list[Any] = []

    while index < len(lines):
        line = lines[index]
        if line.indent < indent:
            break
        if line.indent > indent:
            raise ValueError(f"unexpected indentation near: {line.content}")
        if not line.content.startswith("- "):
            break

        rest = line.content[2:].strip()
        index += 1

        if not rest:
            if index < len(lines) and lines[index].indent > indent:
                item, index = parse_block(lines, index, lines[index].indent)
            else:
                item = None
            result.append(item)
            continue

        if rest.startswith("- "):
            nested_indent = indent + 2
            nested_lines = [ParsedLine(indent=nested_indent, content=rest)]
            while index < len(lines) and lines[index].indent > indent:
                nested_lines.append(lines[index])
                index += 1
            item, _ = parse_block(nested_lines, 0, nested_indent)
            result.append(item)
            continue

        if ":" in rest and not rest.startswith("["):
            key, remainder = rest.split(":", 1)
            key = key.strip()
            remainder = remainder.strip()
            item: dict[str, Any] = {}

            if remainder:
                item[key] = parse_scalar(remainder)
            else:
                if index < len(lines) and lines[index].indent > indent:
                    item[key], index = parse_block(lines, index, lines[index].indent)
                else:
                    item[key] = {}

            if index < len(lines) and lines[index].indent > indent:
                extra, index = parse_block(lines, index, lines[index].indent)
                if not isinstance(extra, dict):
                    raise ValueError("list item mapping continuation must be a mapping")
                item.update(extra)

            result.append(item)
            continue

        result.append(parse_scalar(rest))

    return result, index


def ensure_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return value


def normalize_item(item: Any) -> Any:
    if isinstance(item, str):
        return item

    if isinstance(item, list):
        return [str(elem) for elem in item]

    if not isinstance(item, dict):
        raise ValueError(f"unsupported item type: {item!r}")

    if "image" in item:
        return str(item["image"])
    if "join" in item:
        return [str(elem) for elem in ensure_list(item["join"], "join")]
    if "montage" in item:
        if not isinstance(item["montage"], dict):
            raise ValueError("montage item must contain a mapping")
        return normalize_spec(item["montage"])

    if any(key in item for key in ("rows", "entries", "title", "size")):
        return normalize_spec(item)

    raise ValueError(f"unsupported item mapping: {item!r}")


def normalize_row(row: Any) -> list[Any]:
    if isinstance(row, dict):
        items = row.get("items")
        if items is None:
            raise ValueError("row mapping must contain 'items'")
        row_items = ensure_list(items, "row items")
    else:
        row_items = ensure_list(row, "row")

    return [normalize_item(item) for item in row_items]


def normalize_entries(entries: list[Any]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    current_row: list[Any] = []

    def flush_row() -> None:
        nonlocal current_row
        if current_row:
            rows.append(current_row)
            current_row = []

    for entry in entries:
        if isinstance(entry, dict) and entry.get("new_row"):
            flush_row()
            continue
        current_row.append(normalize_item(entry))

    flush_row()
    return rows


def normalize_spec(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise ValueError("montage spec must be a mapping")

    normalized = dict(spec)
    if "entries" in spec:
        normalized["rows"] = normalize_entries(ensure_list(spec["entries"], "entries"))
    else:
        normalized["rows"] = [normalize_row(row) for row in ensure_list(spec.get("rows"), "rows")]
    return normalized


def run_command(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def symlink_or_copy(src: Path, dst: Path) -> None:
    try:
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        os.symlink(src, dst)
    except OSError:
        from shutil import copyfile
        copyfile(src, dst)


def copy_output(src: Path, dst: Path) -> None:
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    shutil.copyfile(src, dst)


class MontageRenderer:
    def __init__(self, spec_path: Path, outfile: str, scale: str | None = None, no_clean: bool = False):
        self.spec_path = spec_path
        self.outfile = outfile
        self.scale = scale
        self.no_clean = no_clean
        self.curdir = Path.cwd()
        self.tool_dir = Path(__file__).resolve().parent
        self.auto_nested_index = 1
        self.temp_root = Path(tempfile.mkdtemp(prefix="montage-next-"))
        self.intermediate_outputs: list[Path] = []

    def background_for(self, title: str | None, nested: bool) -> str:
        return UNTITLED_NESTED_BACKGROUND if nested and not title else TITLE_BACKGROUND

    def resolve_output(self, spec: dict[str, Any], nested: bool) -> Path:
        if not nested:
            return self.curdir / self.outfile

        if nested:
            name = f"{self.spec_path.stem}-m{self.auto_nested_index}.jpg"
            self.auto_nested_index += 1
            return self.curdir / name

    def resolve_title(self, spec: dict[str, Any], output_path: Path) -> str | None:
        if "title" not in spec:
            return None
        title = spec["title"]
        if title == "auto":
            return output_path.name
        return None if title in (None, "") else str(title)

    def resolve_size(self, spec: dict[str, Any], nested: bool) -> str:
        size = spec.get("size")
        if size:
            return str(size)
        return "s" if nested else "m"

    def render_image_group(self, images: list[str], background: str) -> Path:
        tmp_path = self.temp_root / f"group-{next(tempfile._get_candidate_names())}.jpg"
        if len(images) == 1:
            symlink_or_copy(self.curdir / images[0], tmp_path)
            return tmp_path

        cmd = [
            "gm", "montage",
            "-monitor",
            "-background", background,
            "-geometry", "+0+0",
            "-tile", "1x",
            *images,
            str(tmp_path),
        ]
        run_command(cmd)
        return tmp_path

    def render_row(self, row: list[Any], background: str) -> Path:
        item_paths: list[Path] = []

        for item in row:
            if isinstance(item, str):
                item_paths.append(self.curdir / item)
            elif isinstance(item, list):
                images = [str(elem) for elem in item]
                item_paths.append(self.render_image_group(images, background))
            elif isinstance(item, dict):
                item_paths.append(self.render_spec(item, nested=True))
            else:
                raise ValueError(f"unsupported row item: {item!r}")

        tmp_path = self.temp_root / f"row-{next(tempfile._get_candidate_names())}.jpg"
        if len(item_paths) == 1:
            symlink_or_copy(item_paths[0], tmp_path)
            return tmp_path

        cmd = [
            "gm", "montage",
            "-monitor",
            "-background", background,
            "-geometry", "+0+0",
            "-tile", f"{len(item_paths)}x",
            *[str(path) for path in item_paths],
            str(tmp_path),
        ]
        run_command(cmd)
        return tmp_path

    def render_spec(self, spec: dict[str, Any], nested: bool = False) -> Path:
        output_path = self.resolve_output(spec, nested=nested)
        if nested:
            self.intermediate_outputs.append(output_path)
        title = self.resolve_title(spec, output_path)
        size = self.resolve_size(spec, nested=nested)
        rows = ensure_list(spec.get("rows"), "rows")
        background = self.background_for(title, nested=nested)

        row_paths: list[Path] = []
        for row in rows:
            row_items = ensure_list(row, "row")
            row_paths.append(self.render_row(row_items, background))

        if len(row_paths) == 1:
            copy_output(row_paths[0], output_path)
        else:
            cmd = [
                "gm", "montage",
                "-monitor",
                "-background", background,
                "-geometry", "+0+0",
                "-tile", "1x",
                *[str(path) for path in row_paths],
                str(output_path),
            ]
            run_command(cmd)

        if title:
            run_command([str(self.tool_dir / "montit.py"), "-s", size, "-t", title, str(output_path)])

        if self.scale and not nested:
            run_command(["gm", "convert", "-scale", f"{self.scale}%", str(output_path), str(output_path)])

        return output_path

    def cleanup(self) -> None:
        if not self.no_clean:
            for path in reversed(self.intermediate_outputs):
                try:
                    if path.exists() or path.is_symlink():
                        path.unlink()
                except OSError:
                    pass
        shutil.rmtree(self.temp_root, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", dest="scale", nargs="?", const="specified")
    parser.add_argument("-o", dest="outfile", type=str, required=True)
    parser.add_argument("-n", "--no-clean", dest="no_clean", action="store_true")
    parser.add_argument("cmfile")
    return parser


def load_spec(path: Path) -> dict[str, Any]:
    parsed = parse_yaml_like(path.read_text())
    if not isinstance(parsed, dict):
        raise ValueError("top-level YAML document must be a mapping")
    return normalize_spec(parsed)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    scale = None if args.scale in (None, "specified") else args.scale
    spec_path = Path(args.cmfile).resolve()
    renderer = MontageRenderer(
        spec_path=spec_path,
        outfile=args.outfile,
        scale=scale,
        no_clean=args.no_clean,
    )
    try:
        spec = load_spec(spec_path)
        renderer.render_spec(spec, nested=False)
    finally:
        renderer.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
