from __future__ import annotations

import subprocess
import sys
from pathlib import Path


MONTAGE_SPEC_SUFFIXES = {".yaml", ".yml"}
MINDMAP_SUFFIXES = {".otl"}


def read_text(path: Path) -> str | None:
    try:
        return path.read_text()
    except OSError:
        return None


def find_target_makefile(target: str) -> Path | None:
    for path in sorted(Path.cwd().glob("Makefile*")):
        if not path.is_file():
            continue
        contents = read_text(path)
        if contents is None:
            continue
        if target in contents:
            return path
    return None


def find_target_justfile(target: str) -> Path | None:
    for pattern in ("justfile", "Justfile", "*.just"):
        for path in sorted(Path.cwd().glob(pattern)):
            if not path.is_file():
                continue
            contents = read_text(path)
            if contents is None:
                continue
            if target in contents:
                return path
    return None


def find_target_yaml(target: str) -> Path | None:
    for pattern in ("*.yaml", "*.yml"):
        for path in sorted(Path.cwd().glob(pattern)):
            if not path.is_file():
                continue
            contents = read_text(path)
            if contents is None:
                continue
            if target in contents:
                return path
    return None


def make_target_for(path_or_target: str) -> str:
    if Path(path_or_target).suffix in MONTAGE_SPEC_SUFFIXES:
        return f"step-{Path(path_or_target).name}"
    return path_or_target


def just_target_for(path_or_target: str) -> str:
    suffix = Path(path_or_target).suffix
    if suffix in MONTAGE_SPEC_SUFFIXES:
        return "montage"
    if suffix in MINDMAP_SUFFIXES:
        return "mindmap"
    return path_or_target


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("Usage: target-make <target>", file=sys.stderr)
        return 2

    target_name = argv[0]
    justfile = find_target_justfile(target_name)
    just_target = just_target_for(target_name)
    makefile = None if justfile is not None else find_target_makefile(target_name)
    make_target = make_target_for(target_name)

    if justfile is None and makefile is None:
        yaml_file = find_target_yaml(target_name)
        if yaml_file is not None:
            just_target = just_target_for(yaml_file.name)
            justfile = find_target_justfile(yaml_file.name)
            make_target = make_target_for(yaml_file.name)
            if justfile is None:
                makefile = find_target_makefile(make_target)
                if makefile is None:
                    makefile = find_target_makefile(yaml_file.name)

    if justfile is not None:
        print(justfile.name, flush=True)
        print(f"Found in {justfile.name}", flush=True)
        result = subprocess.run(["just", "-f", str(justfile), just_target])
        return result.returncode

    if makefile is None:
        print("", flush=True)
        print(f"{target_name} not found in any justfile or Makefile", flush=True)
        return 0

    print(makefile.name, flush=True)
    print(f"Found in {makefile.name}", flush=True)
    result = subprocess.run(["make", "-f", str(makefile), make_target])
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
