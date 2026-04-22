#!/usr/bin/env python3

import argparse
import datetime as dt
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"


def read_base_version(pyproject_text: str) -> str:
    match = re.search(r'(?m)^version = "([^"]+)"$', pyproject_text)
    if not match:
        raise SystemExit("Could not find [project].version in pyproject.toml")
    return match.group(1)


def build_devel_version(base_version: str, stamp: str) -> str:
    if ".dev" in base_version:
        base_version = base_version.split(".dev", 1)[0]
    if "+" in base_version:
        base_version = base_version.split("+", 1)[0]
    return f"{base_version}.dev{stamp}"


def rewrite_version(pyproject_text: str, new_version: str) -> str:
    return re.sub(
        r'(?m)^version = "[^"]+"$',
        f'version = "{new_version}"',
        pyproject_text,
        count=1,
    )


def copy_project_tree(temp_root: pathlib.Path) -> pathlib.Path:
    target = temp_root / ROOT.name
    ignore = shutil.ignore_patterns(
        ".git",
        ".specstory",
        "__pycache__",
        "*.pyc",
        "build",
        "dist",
        ".mypy_cache",
        ".pytest_cache",
    )
    shutil.copytree(ROOT, target, ignore=ignore)
    return target


def run_wheel_build(project_dir: pathlib.Path, dist_dir: pathlib.Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--wheel-dir",
            str(dist_dir),
            str(project_dir),
        ],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stamp",
        help="Datestamp suffix for the dev version. Defaults to current local timestamp.",
    )
    parser.add_argument(
        "--dist-dir",
        default=str(ROOT / "dist"),
        help="Output directory for built wheels.",
    )
    args = parser.parse_args()

    stamp = args.stamp or dt.datetime.now().strftime("%Y%m%d%H%M%S")
    pyproject_text = PYPROJECT.read_text()
    base_version = read_base_version(pyproject_text)
    devel_version = build_devel_version(base_version, stamp)

    dist_dir = pathlib.Path(args.dist_dir).resolve()
    dist_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="graphviz-mindmaps-wheel-") as temp_dir_name:
        temp_dir = pathlib.Path(temp_dir_name)
        project_dir = copy_project_tree(temp_dir)
        temp_pyproject = project_dir / "pyproject.toml"
        temp_pyproject.write_text(rewrite_version(pyproject_text, devel_version))
        run_wheel_build(project_dir, dist_dir)

    print(f"Built wheel version {devel_version} into {dist_dir}")


if __name__ == "__main__":
    main()
