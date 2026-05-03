from __future__ import annotations

import subprocess
import sys
from pathlib import Path


MONTAGE_SPEC_SUFFIXES = {".gmm", ".yaml", ".yml"}


def find_target_makefile(target: str) -> Path | None:
    for path in sorted(Path.cwd().glob("Makefile*")):
        if not path.is_file():
            continue
        try:
            contents = path.read_text()
        except OSError:
            continue
        if target in contents:
            return path
    return None


def find_target_yaml(target: str) -> Path | None:
    for pattern in ("*.yaml", "*.yml"):
        for path in sorted(Path.cwd().glob(pattern)):
            if not path.is_file():
                continue
            try:
                contents = path.read_text()
            except OSError:
                continue
            if target in contents:
                return path
    return None


def make_target_for(path_or_target: str) -> str:
    if Path(path_or_target).suffix in MONTAGE_SPEC_SUFFIXES:
        return f"step-{Path(path_or_target).name}"
    return path_or_target


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("Usage: target-make <target>", file=sys.stderr)
        return 2

    target_name = argv[0]
    makefile = find_target_makefile(target_name)
    make_target = make_target_for(target_name)

    if makefile is None:
        yaml_file = find_target_yaml(target_name)
        if yaml_file is not None:
            make_target = make_target_for(yaml_file.name)
            makefile = find_target_makefile(make_target)
            if makefile is None:
                makefile = find_target_makefile(yaml_file.name)

    if makefile is None:
        print("", flush=True)
        print(f"{target_name} not found in any Makefile", flush=True)
        return 0

    print(makefile.name, flush=True)
    print(f"Found in {makefile.name}", flush=True)
    result = subprocess.run(["make", "-f", str(makefile), make_target])
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
