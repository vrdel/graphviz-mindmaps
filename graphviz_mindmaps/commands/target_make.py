from __future__ import annotations

import subprocess
import sys
from pathlib import Path


JUST_TARGET_SUFFIXES = {".otl", ".yaml", ".yml"}


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


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("Usage: target-make <target>", file=sys.stderr)
        return 2

    target_name = argv[0]
    justfile = find_target_justfile(target_name) if Path(target_name).suffix in JUST_TARGET_SUFFIXES else None
    makefile = None if justfile is not None else find_target_makefile(target_name)

    if justfile is not None:
        print(justfile.name, flush=True)
        print(f"Found in {justfile.name}", flush=True)
        result = subprocess.run(["just", "-f", str(justfile), "build", target_name])
        return result.returncode

    if makefile is None:
        print("", flush=True)
        print(f"{target_name} not found in any justfile or Makefile", flush=True)
        return 0

    print(makefile.name, flush=True)
    print(f"Found in {makefile.name}", flush=True)
    result = subprocess.run(["make", "-f", str(makefile), target_name])
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
