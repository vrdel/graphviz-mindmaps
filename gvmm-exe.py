#!/usr/bin/env python3
"""Run an arbitrary executable inside a selected pyenv virtualenv."""

import argparse
import os
import subprocess


DEFAULT_PYENV_ROOT = os.path.expanduser("~/.pyenv")
DEFAULT_PYENV_ENV = "graphviz-mindmap"
SUPPORTED_COMMANDS = (
    "gvmm",
    "create-mm",
    "target-make",
    "montage",
    "montage-next",
    "montage-title",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gvmm-exe.py",
        description="Run a graphviz-mindmaps tool inside a selected pyenv virtualenv.",
        epilog=(
            "examples:\n"
            "  %(prog)s gvmm -f notes.otl\n"
            "  %(prog)s create-mm -m\n"
            "  %(prog)s target-make notes.otl\n"
            "  %(prog)s montage montage.gmm\n"
            "  %(prog)s montage-next -o output.jpg montage-next.yaml\n"
            "  %(prog)s montage-title -s s -t title image.jpg\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--pyenv-env",
        default=os.environ.get("PYENV_EXE_ENV", DEFAULT_PYENV_ENV),
        help=(
            "pyenv environment name "
            f"(default: $PYENV_EXE_ENV or {DEFAULT_PYENV_ENV})"
        ),
    )
    parser.add_argument(
        "--pyenv-root",
        default=os.environ.get("PYENV_ROOT", DEFAULT_PYENV_ROOT),
        help=f"pyenv root directory (default: {DEFAULT_PYENV_ROOT})",
    )
    parser.add_argument(
        "command",
        metavar="COMMAND",
        help="supported command: " + ", ".join(SUPPORTED_COMMANDS),
    )
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        metavar="ARGS",
        help="arguments passed to the command",
    )
    return parser


def build_env(pyenv_root: str, pyenv_env: str) -> dict:
    venv_root = os.path.join(pyenv_root, "versions", pyenv_env)
    venv_bin = os.path.join(venv_root, "bin")

    if not os.path.isdir(venv_bin):
        raise FileNotFoundError(f"pyenv environment not found: {venv_bin}")

    env = os.environ.copy()
    env["PYENV_ROOT"] = pyenv_root
    env["PYENV_VERSION"] = pyenv_env
    env["VIRTUAL_ENV"] = venv_root
    env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")
    env.pop("PYTHONHOME", None)
    return env


def main() -> int:
    parser = build_parser()
    parsed = parser.parse_args()
    command = parsed.command

    if command not in SUPPORTED_COMMANDS:
        parser.error("unsupported command %r; expected one of: %s" % (
            parsed.command,
            ", ".join(SUPPORTED_COMMANDS),
        ))

    try:
        env = build_env(parsed.pyenv_root, parsed.pyenv_env)
    except FileNotFoundError as exc:
        parser.error(str(exc))

    argv = [command] + parsed.args

    try:
        result = subprocess.run(argv, env=env)
    except KeyboardInterrupt:
        return 130
    except FileNotFoundError:
        parser.error(
            "command not found in PATH for selected environment: %s" % command
        )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
