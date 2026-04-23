# graphviz-mindmaps

Graphviz-based mindmap renderer and related image/montage tooling.

## License

Licensed under the Apache License, Version 2.0.
See [LICENSE](/home/daniel/my_work/graphviz-mindmaps/LICENSE).

## Python Dependency

The wheel declares this Python package dependency:

- `Pillow`

Install with:

```bash
python3 -m pip install .
```

## External Runtime Requirements

The project also shells out to external tools which are not Python packages and are therefore not installed by `pip`.

Required at runtime:

- `dot` from Graphviz
- `gm` from GraphicsMagick
- `montage`
- `montit`

Used in some flows:

- `galaview.sh`
- `FvwmCommand`
- `make`

## Wheel Entrypoints

The packaged wheel currently exposes:

- `gvmm`
- `montage`
- `montit`

## Local Helper

The repo also contains a local helper script:

- [gvmm-exe.py](/home/daniel/my_work/graphviz-mindmaps/gvmm-exe.py)

It runs an arbitrary command inside the configured `pyenv` virtualenv, defaulting to `graphviz-mindmap`.

Examples:

```bash
./gvmm-exe.py gvmm -f notes.otl
./gvmm-exe.py montage list.txt
./gvmm-exe.py montit -s s -t title image.jpg
```
