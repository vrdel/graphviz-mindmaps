#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


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


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("Usage: gvmm-target-make.py <target>", file=sys.stderr)
        return 2

    target_name = argv[0]
    makefile = find_target_makefile(target_name)

    if makefile is None:
        print("", flush=True)
        print(f"{target_name} not found in any Makefile", flush=True)
        return 0

    print(makefile.name, flush=True)
    print(f"Found in {makefile.name}", flush=True)
    result = subprocess.run(["make", "-f", str(makefile), target_name])
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
