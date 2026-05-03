from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


DEFAULT_OTL = "mindmap-01.otl"
DEFAULT_MONTAGE = "montage.yml"
DEFAULT_WIKI = "Template.wiki"
DEFAULT_JUSTFILE = "justfile"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="create-mm",
        add_help=False,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("-s", action="store_true", dest="create_single",
                        help="create single mindmap from templates")
    parser.add_argument("-m", action="store_true", dest="create_montage",
                        help="create montage from templates")
    parser.add_argument("-p", dest="otl_mindmap", default=DEFAULT_OTL,
                        help=f"filename of otl mindmap ({DEFAULT_OTL})")
    parser.add_argument("-g", dest="montage", default=DEFAULT_MONTAGE,
                        help=f"filename of montage ({DEFAULT_MONTAGE})")
    parser.add_argument("-w", dest="wiki", default=DEFAULT_WIKI,
                        help=f"filename of vimwiki ({DEFAULT_WIKI})")
    parser.add_argument("-f", dest="makefile", default=DEFAULT_JUSTFILE,
                        help=f"filename of build file ({DEFAULT_JUSTFILE})")
    parser.add_argument("-l", dest="scale", type=int, default=0,
                        help="scale final montage (60)")
    parser.add_argument("-h", "--help", action="help", help="usage")
    return parser


def copy_file(src: Path, dst: Path) -> None:
    print(f"cp {src} {dst}")
    shutil.copyfile(src, dst)


def replace_in_file(path: Path, old: str, new: str) -> None:
    print(f"replace {old!r} -> {new!r} in {path}")
    path.write_text(path.read_text().replace(old, new))


def create_single(args: argparse.Namespace, template_dir: Path) -> None:
    print("Creating single otl mindmap...")
    otl_path = Path(args.otl_mindmap)
    wiki_path = Path(args.wiki)
    justfile_path = Path(args.makefile)
    stem = otl_path.stem

    copy_file(template_dir / DEFAULT_OTL, otl_path)
    replace_in_file(otl_path, "mindmap-01", stem)

    copy_file(template_dir / DEFAULT_JUSTFILE, justfile_path)
    replace_in_file(justfile_path, "mindmap-01", stem)

    if args.wiki != DEFAULT_WIKI:
        copy_file(template_dir / DEFAULT_WIKI, wiki_path)
        replace_in_file(wiki_path, "mindmap-01", stem)
        replace_in_file(justfile_path, DEFAULT_WIKI, args.wiki)


def create_montage(args: argparse.Namespace, template_dir: Path) -> None:
    print("Creating montage otl mindmaps...")
    otl_path = Path(args.otl_mindmap)
    wiki_path = Path(args.wiki)
    justfile_path = Path(args.makefile)
    montage_template = DEFAULT_MONTAGE
    montage_name = args.montage
    montage_path = Path(montage_name)
    stem = otl_path.stem

    copy_file(template_dir / DEFAULT_OTL, otl_path)
    replace_in_file(otl_path, "mindmap-01", stem)

    copy_file(template_dir / DEFAULT_JUSTFILE, justfile_path)
    replace_in_file(justfile_path, "mindmap-01", stem)

    copy_file(template_dir / DEFAULT_WIKI, wiki_path)
    replace_in_file(wiki_path, "mindmap-01", stem)
    replace_in_file(justfile_path, DEFAULT_WIKI, args.wiki)

    copy_file(template_dir / montage_template, montage_path)
    replace_in_file(montage_path, "mindmap-01", stem)
    replace_in_file(justfile_path, DEFAULT_MONTAGE, montage_name)

    if args.scale > 0:
        replace_in_file(justfile_path, 'scale := "60"', f'scale := "{args.scale}"')


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()

    if not argv:
        parser.print_usage(sys.stderr)
        return 2

    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    template_single = repo_root / "templates" / "Single"
    template_montage = repo_root / "templates" / "Montage"

    if args.create_single:
        create_single(args, template_single)

    if args.create_montage:
        create_montage(args, template_montage)

    if not args.create_single and not args.create_montage:
        parser.print_usage(sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
