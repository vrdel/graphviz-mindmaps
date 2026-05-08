from __future__ import annotations

from graphviz_mindmaps.commands.mm_files import run


def main(argv: list[str] | None = None) -> int:
    return run(argv, move=True, prog="move-mm")


if __name__ == "__main__":
    raise SystemExit(main())
