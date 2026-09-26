# graphviz-mindmaps

Graphviz-based mindmap rendering with helper tools for image titling and montage generation.

The repo currently provides user-facing command-line tools:

- `gvmm` renders `.otl` outline files into images or `.dot` output
- `create-mm` creates mindmap project files from templates
- `copy-mm` copies a mindmap project bundle to another directory
- `move-mm` moves a mindmap project bundle to another directory
- `target-make` finds a justfile or Makefile containing an outline or YAML montage target and runs it
- `montage` builds image montages from YAML specs
- `montage-title` adds a title bar to an image

## Install

The Python package depends on:

- `Pillow`
- `Pygments`

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

- `just`
- `galaview.sh`
- `inkscape`, used as a fallback when Graphviz's cairo bitmap renderer cannot render very large graphs directly

## Entrypoints

The wheel exposes these console scripts:

- `gvmm`
- `create-mm`
- `copy-mm`
- `move-mm`
- `target-make`
- `montage`
- `montage-title`

The repo also contains a local helper script:

- [gvmm-exe.py](/home/daniel/my_work/git.graphviz-mindmaps/graphviz-mindmaps/gvmm-exe.py)

`gvmm-exe.py` runs one of the installed tools inside a selected `pyenv` virtualenv and defaults to `graphviz-mindmap`.

## Usage

Create template projects:

```bash
create-mm -s
create-mm -s -f justfile
create-mm -m
create-mm -m -p notes.otl -g montage.yml -w Notes.wiki -f justfile
create-mm -m -l 80
create-mm -m -o final-notes.jpg
```

`create-mm -s` creates a single mindmap starter with `mindmap-01.otl`; pass `-f justfile` to create a build file too. `create-mm -m` creates a montage project with `montage.yml`, `justfile`, `Template.wiki`, and `mindmap-01.otl`.
Use `-o` with `-m` to change the generated justfile's final montage image name.

Render one or more outline files with `gvmm`:

```bash
gvmm -f notes.otl
gvmm -f notes-1.otl notes-2.otl
gvmm -f notes.otl -i output.jpg
gvmm -f notes.otl -d output.dot
gvmm -f notes.otl -s 80
gvmm -f notes.otl --theme nord
gvmm -f notes.otl --theme gruvbox
```

Supported themes are `default`, `nord`, `papercolor`, `papercolor-dark`, `monokai`, `gruvbox`, and `solarized`.

Choose a theme for an individual mindmap with a root `theme=` attribute:

```text
# Notes
    : fname=notes.jpg theme=nord
    # Themed node
        : node
```

Supported themes are `default`, `nord`, `papercolor`, `papercolor-dark`, `monokai`,
`gruvbox`, and `solarized`. The root theme overrides `--theme` for that mindmap
only. Without it, the command-line theme applies (or `default`). Explicit root
background and node color attributes still override theme colors.

Set a default style for untyped leaf nodes from the root attribute line:

```text
# Notes
    : fname=notes.jpg notitle leaf=node
    # parent
        :
        # leaf rendered as node
            :
```

If `leaf=` is omitted, untyped leaf nodes keep the default underline style. Explicit node attributes still win, so `: todo`, `: quest`, `: cgreen`, and similar typed nodes are unchanged.

Horizontal rules created by `---` have 4 points of extra space above and below
by default. Set `hr_spacing` on a root attribute line to change this for all nodes:

```text
# Notes
    : fname=notes.jpg hr_spacing=4
    # before; ---; after
        : node
```

Use a nonnegative integer; `hr_spacing=0` removes the extra spacing. The setting
also applies to rules in block nodes and does not affect line-selector numbering.

Set `hr_style=solid`, `hr_style=dashed`, or `hr_style=dotted` on the root to
choose the ruler style (default: `solid`). For example:

```text
# Notes
    : fname=notes.jpg hr_style=dashed hr_spacing=2
    # before; ---; after
        : node
```

Use `cdef` on a block node to select the current theme's default regular-node fill color:

```text
# Default-colored block
    : block cdef
    : block body
```

Code blocks can be highlighted and rendered as image-backed Graphviz nodes:

```text
# Python snippet
    : code python style=monokai
    :
    : def hello(name):
    :     return f"hello {name}"
```

Add `l1`, `l12`, or an inclusive range such as `l[2-5]` to the code directive
to highlight those lines with the Pygments style's highlight color:

```text
# Python snippet
    : code python style=monokai l1 l[3-4]
    : def hello(name):
    :     greeting = f"hello {name}"
    :     print(greeting)
    :     return greeting
```

Line numbers start at the first nonblank code line, excluding the node title,
directive, and surrounding blank lines. Internal blank lines count.
Use `El1` for the last nonblank code line or `El[1-5]` for the last five lines.
Multiple selectors are combined; `l[1,3-5,12]` also works.
Line numbers beyond the code body have no effect.

Append `r`, `g`, or `b` for pale red, green, or blue highlights:
`: code python l1r l2g l3b`. Colors match the saturation and brightness of
Pygments' default yellow highlight. Ranges and end-relative selectors also
accept colors, for example `l[2-5]g` and `El1b`. If selectors overlap, the last
one wins. Selectors without a color keep the selected Pygments style's highlight color.

Build a montage from a YAML file:

```bash
montage -o output.jpg montage.yml
montage -s 80 -b '#4b5262' -o output.jpg montage.yml
```

Montage YAML supports image entries, joined image groups, row breaks, and nested submontages:

```yaml
title: simple montage
entries:
  - image: mindmap-01.jpg
  - image_negate: mindmap-02.jpg|50
  - image_negate_contrast: mindmap-02.jpg
  - image_gray: mindmap-03.jpg
  - image_negate_gray: mindmap-04.jpg
  - image_negate_gray_contrast: mindmap-04.jpg
  - image_sketch: mindmap-03.jpg
  - image_negate_sketch: mindmap-04.jpg
  - image_negate_gray_contrast_sketch: mindmap-04.jpg|50
  - join: [mindmap-01.jpg, mindmap-02.jpg]
  - new_row: true
  - submontage:
      title: nested montage
      entries:
        - join: [detail-01.jpg, detail-02.jpg]
```

Find and run a generated build target:

```bash
target-make mindmap-01.otl
target-make montage.yml
target-make mindmap-01.otl p
```

For justfile projects generated by `create-mm`, `target-make mindmap-01.otl` runs `just -f justfile build mindmap-01.otl`; `target-make montage.yml` runs `just -f justfile build montage.yml`. Add the optional `p` argument to invoke the `buildpreview` recipe instead, for example `just -f justfile buildpreview mindmap-01.otl`. For Makefiles, the same argument selects a target prefixed with `preview-`; `target-make mindmap-01.otl p` runs `make -f Makefile... preview-mindmap-01.otl`.

Copy or move a whole mindmap project bundle:

```bash
copy-mm justfile archive/
copy-mm mindmap-01.otl archive/
copy-mm montage.yml archive/

move-mm justfile archive/
move-mm mindmap-01.otl archive/
move-mm montage.yml archive/
```

When the source is a justfile, `copy-mm` and `move-mm` include referenced `.otl`, `.yml/.yaml`, wiki, output, and image files. When the source is an individual `.otl` or montage YAML file, the tools first look for a related `justfile`, `Justfile`, or `*.just` in the same directory and then move the same complete bundle. If no related justfile exists, `.otl` sources include their `fname=` output and `img=` attachments; montage YAML sources include referenced images and sibling `.otl` files where present.

Image nodes and attached images support temporary transforms with `img_neg=`, `img_neg_cn=`, `img_gr=`, `img_neg_gr=`, and `img_neg_gr_cn=`. Add the final `sk` stage for a grayscale contour sketch, for example `img_sk=`, `img_neg_sk=`, or `img_neg_gr_cn_sk=`. `cn` applies automatic contrast after the preceding transforms. A final theme color adds an overlay after the other effects. The optional numeric suffix sets its opacity percentage, so `img_sk_cgreen10:photo.png` blends the theme's green into the image at 10%; without a suffix, the overlay defaults to 20%. The supported colors are `cdef`, `cgreen`, `ccyan`, `cblue`, `cpink`, `cred`, `cyello`, `corang`, and `cwhite`. Append `|percent` to proportionally scale a transformed image, for example `img_neg_gr_cn_sk:photo.png|20`. The original image is preserved.

Repeat an image attribute on consecutive lines to add multiple images to one node. Images are placed next to each other in one row, in source order, and the node text spans the full image row:

```text
# Example node
    : img_neg_sk_cred40=first.png|65
    : img_neg_sk_cred40=second.png|65
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
./gvmm-exe.py copy-mm montage.yml archive/
./gvmm-exe.py move-mm notes.otl archive/
./gvmm-exe.py target-make notes.otl
./gvmm-exe.py montage -o output.jpg montage.yml
./gvmm-exe.py montage-title -s s -t "Title" image.jpg
```

Browse bundled Font Awesome icon names and codes:

```bash
python3 tools/build_fontawesome_catalog.py
```

Open [fontawesome-codes.html](fontawesome-codes.html) to view the rendered icon catalog. The package ships `graphviz_mindmaps/assets/fontawesome/FontAwesome.otf`.

## Notes

- `gvmm` can read outline input from files via `-f` or from standard input.
- `montage` reads YAML montage specs. Use `submontage` for nested montage entries.
- `montage-title` is intended to title raw images; the current montage flow titles raw intermediate outputs before writing the final destination.

## License

Licensed under the Apache License, Version 2.0.
See [LICENSE](/home/daniel/my_work/git.graphviz-mindmaps/graphviz-mindmaps/LICENSE).
