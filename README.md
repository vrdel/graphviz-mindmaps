# graphviz-mindmaps

Graphviz-based mindmap rendering with helper tools for image titling and montage generation.

The repo currently provides user-facing command-line tools:

- `gvmm` renders `.otl` outline files into images or `.dot` output
- `create-mm` creates mindmap project files from templates
- `target-make` finds a Makefile containing a target and runs it
- `montage` builds image montages from `.gmm` specs
- `montage-title` adds a title bar to an image

## Install

The Python package depends on:

- `Pillow`

Install with:

```bash
python3 -m pip install .
```

## Runtime Requirements

Some required tools are external executables and are not installed by `pip`.

Required:

- `dot` from Graphviz
- `gm` from GraphicsMagick

Used in some workflows:

- `galaview.sh`
- `FvwmCommand`
- `make`

## Entrypoints

The wheel exposes these console scripts:

- `gvmm`
- `create-mm`
- `target-make`
- `montage`
- `montage-title`

The repo also contains a local helper script:

- [gvmm-exe.py](/home/daniel/my_work/git.graphviz-mindmaps/graphviz-mindmaps/gvmm-exe.py)

`gvmm-exe.py` runs one of the installed tools inside a selected `pyenv` virtualenv and defaults to `graphviz-mindmap`.

## Usage

Render one or more outline files with `gvmm`:

```bash
gvmm -f notes.otl
gvmm -f notes-1.otl notes-2.otl
gvmm -f notes.otl -i output.jpg
gvmm -f notes.otl -d output.dot
gvmm -f notes.otl -s 80
```

Build a montage from a `.gmm` file:

```bash
montage montage.gmm
montage -o output.jpg montage.gmm
montage -s 80 -b '#4b5262' montage.gmm
```

Add a title bar to an image:

```bash
montage-title -s s -t "Title" image.jpg
montage-title -s m -t "Title" input.jpg output.jpg
```

Run the same tools through the local `pyenv` helper:

```bash
./gvmm-exe.py gvmm -f notes.otl
./gvmm-exe.py create-mm -m
./gvmm-exe.py target-make notes.otl
./gvmm-exe.py montage montage.gmm
./gvmm-exe.py montage-title -s s -t "Title" image.jpg
```

## Notes

- `gvmm` can read outline input from files via `-f` or from standard input.
- `montage` reads the legacy `.gmm` montage format used in this repository.
- `montage-title` is intended to title raw images; the current montage flow titles raw intermediate outputs before writing the final destination.

## License

Licensed under the Apache License, Version 2.0.
See [LICENSE](/home/daniel/my_work/git.graphviz-mindmaps/graphviz-mindmaps/LICENSE).
