#!/home/daniel/.pyenv/versions/vrdel-apps-3115/bin/python3

import argparse
import glob
import subprocess


def find_makefiles(search_term):
    return [filename for filename in glob.glob('Makefile*') if search_term in open(filename).read()]


def run_make(target, search_term):
    subprocess.run(['make', '-f', target, search_term])


def main():
    # Create the argument parser
    parser = argparse.ArgumentParser(description='Search for a term in Makefile(s) and execute a make command if found.')
    parser.add_argument('search_term', help='The term to search for in the Makefile(s).')

    args = parser.parse_args()

    target_files = find_makefiles(args.search_term)

    if not target_files:
        print(f"{args.search_term} not found in any Makefile")

    else:
        print(f"Found in {', '.join(target_files)}")
        run_make(target_files[0], args.search_term)


if __name__ == "__main__":
    main()
