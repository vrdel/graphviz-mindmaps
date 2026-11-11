"""Build the pinned upstream Svgbob revision into a repository-local directory."""
import argparse
from pathlib import Path
import shutil
import subprocess


def main():
    repository = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=repository / '.tools' / 'svgbob',
                        help='installation root (default: .tools/svgbob in this repository)')
    args = parser.parse_args()
    cargo = shutil.which('cargo')
    if not cargo:
        parser.error('Cargo and Rust are required to build Svgbob')
    revision = Path(__file__).with_name('svgbob-revision.txt').read_text().strip()
    result = subprocess.run([cargo, 'install', '--git', 'https://github.com/ivanceras/svgbob.git',
                             '--rev', revision, '--locked', '--root', str(args.root), 'svgbob_cli'])
    if result.returncode == 0:
        (args.root / 'REVISION').write_text(revision + '\n')
        print('Installed Svgbob at', args.root / 'bin' / 'svgbob_cli')
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
