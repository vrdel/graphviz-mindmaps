from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path


DEFAULT_OTL = "mindmap-01.otl"
DEFAULT_MONTAGE = "montage.yml"
DEFAULT_OUTPUT = "final_montage.jpg"
DEFAULT_WIKI_OUTPUT = "Montage_montage.jpg"
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
    parser.add_argument("-a", "--auto", action="store_true",
                        help="derive montage project filenames from -o")
    parser.add_argument("-p", dest="otl_mindmap",
                        help=f"filename of otl mindmap ({DEFAULT_OTL})")
    parser.add_argument("-g", dest="montage",
                        help=f"filename of montage ({DEFAULT_MONTAGE})")
    parser.add_argument("-o", dest="output",
                        help=f"filename of final montage image ({DEFAULT_OUTPUT})")
    parser.add_argument("-w", dest="wiki",
                        help="create vimwiki file and enable its build step (optional)")
    parser.add_argument("-j", "-f", dest="justfile",
                        help=f"filename of justfile ({DEFAULT_JUSTFILE})")
    parser.add_argument("-l", dest="scale", type=int, default=0,
                        help="scale final montage (0 keeps the template default)")
    parser.add_argument("-h", "--help", action="help", help="usage")
    return parser


def copy_file(src: Path, dst: Path) -> None:
    print(f"cp {src} {dst}")
    shutil.copyfile(src, dst)


def replace_in_file(path: Path, old: str, new: str) -> None:
    print(f"replace {old!r} -> {new!r} in {path}")
    path.write_text(path.read_text().replace(old, new))


def configure_wiki(args: argparse.Namespace, template_dir: Path,
                   justfile_path: Path | None, stem: str) -> Path | None:
    if not args.wiki:
        if justfile_path:
            justfile_path.write_text(''.join(
                line for line in justfile_path.read_text().splitlines(keepends=True)
                if not line.startswith('wiki :=') and '{{wiki}}' not in line
            ))
        return None

    wiki_path = Path(args.wiki)
    copy_file(template_dir / DEFAULT_WIKI, wiki_path)
    replace_in_file(wiki_path, "mindmap-01", stem)
    if justfile_path:
        replace_in_file(justfile_path, DEFAULT_WIKI, args.wiki)
    return wiki_path


def create_single(args: argparse.Namespace, template_dir: Path) -> None:
    print("Creating single otl mindmap...")
    otl_path = Path(args.otl_mindmap)
    justfile_path = Path(args.justfile) if args.justfile else None
    stem = otl_path.stem

    copy_file(template_dir / DEFAULT_OTL, otl_path)
    replace_in_file(otl_path, "mindmap-01", stem)

    if justfile_path:
        copy_file(template_dir / DEFAULT_JUSTFILE, justfile_path)
        replace_in_file(justfile_path, "mindmap-01", stem)

    configure_wiki(args, template_dir, justfile_path, stem)


def create_montage(args: argparse.Namespace, template_dir: Path) -> None:
    print("Creating montage otl mindmaps...")
    otl_path = Path(args.otl_mindmap)
    justfile_path = Path(args.justfile or DEFAULT_JUSTFILE)
    montage_template = DEFAULT_MONTAGE
    montage_name = args.montage
    montage_path = Path(montage_name)
    stem = otl_path.stem

    copy_file(template_dir / DEFAULT_OTL, otl_path)
    replace_in_file(otl_path, "mindmap-01", stem)

    copy_file(template_dir / DEFAULT_JUSTFILE, justfile_path)
    replace_in_file(justfile_path, "mindmap-01", stem)

    wiki_path = configure_wiki(args, template_dir, justfile_path, stem)

    copy_file(template_dir / montage_template, montage_path)
    replace_in_file(montage_path, "mindmap-01", stem)
    replace_in_file(justfile_path, DEFAULT_MONTAGE, montage_name)

    if args.scale > 0:
        justfile_path.write_text(re.sub(r'^scale := "[^"]*"$',
                                       f'scale := "{args.scale}"',
                                       justfile_path.read_text(), flags=re.MULTILINE))
    if args.output:
        replace_in_file(justfile_path, DEFAULT_OUTPUT, args.output)
        if wiki_path:
            replace_in_file(wiki_path, DEFAULT_WIKI_OUTPUT, args.output)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()

    if not argv:
        parser.print_usage(sys.stderr)
        return 2

    args = parser.parse_args(argv)
    if args.auto:
        if not args.create_montage or args.create_single:
            parser.error('--auto requires -m without -s')
        if not args.output:
            parser.error('--auto requires an output filename with -o')
        output = Path(args.output)
        args.otl_mindmap = args.otl_mindmap or str(output.with_name(output.stem + '-1.otl'))
        args.montage = args.montage or str(output.with_suffix('.yml'))
        args.justfile = args.justfile or str(output.with_suffix('.just'))
    args.otl_mindmap = args.otl_mindmap or DEFAULT_OTL
    args.montage = args.montage or DEFAULT_MONTAGE

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
