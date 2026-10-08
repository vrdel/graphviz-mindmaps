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

Apply a font to a selected word with `l1w2fmld` (first line, second word,
monospace, bold):

```text
# za models.User ide posebna logika
    : commen l1w2fmld
```

Line and word numbers start at 1. Word font selectors accept `fm` (monospace),
`fa` (sans serif), `fe` (serif), and `fd` (default comic font), combined with
size and emphasis such as `l1w2fmf20ld`. Use tabs for `.otl` indentation.

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

Supported themes are `default`, `nord`, `papercolor`, `papercolor-dark`, `monokai`,
`gruvbox`, `solarized`, `solarized-light`, `catppuccin-latte`, `rose-pine-dawn`,
`github-light`, `one-light`, `gruvbox-light`, `dracula`, `catppuccin-mocha`,
`tokyo-night`, `one-dark`, `rose-pine`, `kanagawa`, `everforest-dark`,
`everforest-light`, `ayu-dark`, `ayu-light`, `nightfox`, and `dayfox`.

Additional light themes (adapted with lightly tinted node backgrounds):

- `solarized-light` — warm cream, based on [Solarized](https://ethanschoonover.com/solarized/).
- `catppuccin-latte` — cool light gray with colorful accents, based on [Catppuccin Latte](https://catppuccin.com/palette/).
- `rose-pine-dawn` — warm ivory with muted accents, based on [Rosé Pine Dawn](https://github.com/rose-pine/neovim/blob/main/lua/rose-pine/palette.lua).
- `github-light` — white and pale gray with clear accents, based on [GitHub Primer](https://primer.style/product/primitives/color/).
- `one-light` — near-white with colorful syntax accents, based on [Atom One Light](https://github.com/atom/one-light-syntax/blob/master/styles/colors.less).
- `gruvbox-light` — warm cream with earthy accents, based on [Gruvbox Light](https://github.com/morhetz/gruvbox).
- `everforest-light` — cream with forest accents, based on [Everforest](https://github.com/sainnhe/everforest).
- `ayu-light` — near-white with warm accents, based on [Ayu](https://github.com/ayu-theme/ayu-colors).
- `dayfox` — warm light neutrals with purple text, based on [Dayfox](https://github.com/EdenEast/nightfox.nvim).

Additional dark themes (adapted with subdued, tinted node backgrounds):

- `dracula` — charcoal with vivid accents, based on [Dracula](https://draculatheme.com/contribute).
- `catppuccin-mocha` — dark blue-gray with pastel accents, based on [Catppuccin Mocha](https://catppuccin.com/palette/).
- `tokyo-night` — deep navy with cool accents, based on [Tokyo Night](https://github.com/folke/tokyonight.nvim).
- `one-dark` — charcoal with balanced accents, based on [Atom One Dark](https://github.com/atom/one-dark-syntax/blob/master/styles/colors.less).
- `rose-pine` — deep purple with soft accents, based on [Rosé Pine](https://github.com/rose-pine/neovim/blob/main/lua/rose-pine/palette.lua).
- `kanagawa` — ink-dark with warm accents, based on [Kanagawa Wave](https://github.com/rebelot/kanagawa.nvim).
- `everforest-dark` — green-gray with earthy accents, based on [Everforest](https://github.com/sainnhe/everforest).
- `ayu-dark` — deep charcoal with amber accents, based on [Ayu](https://github.com/ayu-theme/ayu-colors).
- `nightfox` — dark navy with muted accents, based on [Nightfox](https://github.com/EdenEast/nightfox.nvim).

For example: `gvmm --theme catppuccin-latte -f notes.otl` or `: theme=catppuccin-latte` on the root.

Choose a theme for an individual mindmap with a root `theme=` attribute:

```text
# Notes
    : fname=notes.jpg theme=nord
    # Themed node
        : node
```

All themes listed above work with the root attribute. The root theme overrides `--theme` for that mindmap
only. Without it, the command-line theme applies (or `default`). Explicit root
background and node color attributes still override theme colors.

Root attributes can span consecutive lines at the same indentation, starting
with the `fname=` line:

```text
# root_node
    : fname=srce-tech-2610.jpg notitle
    : leaf=node sgmargin=2 theme=github-light
    : bg=#efefef root_bw=4 root_bs=dashed root_bg=seagreen1
    : root_symb=check
```

Use tabs for indentation in `.otl` files. This continuation syntax applies only
to the root; ordinary child attributes remain on their existing attribute line.

Root titles can also span consecutive `#` lines at the same indentation.
Use the usual word and line selectors on the root attribute lines:

```text
# za models.User ide posebna logika
# druga linija naslova
    : fname=notes.jpg notitle root_symb=check
    : l1w2fmld l2f30 l2b
```

This renders `models.User` in bold monospace and the second title line in
30-point blue text. Semicolon-separated titles still work. Selectors count
title lines and words from 1, excluding root icons, and affect only the root.
Font, size, color, emphasis, ranges, and end-relative selectors work as they
do on child labels.

Use `root_bg` for the root node's fill and `root_fg` for its text color:

```text
# Notes
    : fname=notes.jpg theme=nord root_bg="#334155" root_fg="white"
```

These override the theme for the root node only. Named Graphviz colors and hex
colors are supported. The canvas background is controlled separately by `bg`
or `bgcolor`; omitted root colors retain their theme defaults.

Use `root_bw` for the root border width, `root_bs` for its style (such as
`solid`, `dashed`, or `dotted`), and `root_bc` for its color:

```text
# Notes
    : fname=notes.jpg root_bw=3 root_bs=dashed root_bc="#88c0d0"
```

These affect only the root node and override its border settings. The border
style preserves the root fill; `root_bw=0` hides the border. Omitted attributes
keep the existing defaults.

Add Font Awesome icons above the root title with `root_symb`:

```text
# Notes
    : fname=notes.jpg root_symb=book:lightbulb-o root_bg="#334155" root_fg="white"
```

Use the same icon names as `symb=`, separated by colons. Icons use the same
default symbol color as `symb=` (the current theme's red) unless `root_fg` is
explicitly set, in which case it colors both the title and icons. Unknown icon
names are ignored.

Style individual root icons with `root_sym3rf35`: `3` selects the third
resolved icon (counting from 1), `r` selects the theme's red, and `f35` sets its
size to 35 points. Use `root_sym1g` for color only, `root_sym1f40` for size only,
or `root_sym[1,3]gf35` to style several icons. Color codes match child symbols:
`r`, `g`, `b`, `y`, `c`, `p`, `k`, and `t`.

```text
# Notes
    : fname=notes.jpg root_symb=book:star:check
    : root_sym3rf35
```

These controls apply only on the root. An icon's explicit color overrides
`root_fg` without changing the title; other icons retain their default color
and 25-point size. Out-of-range indices are ignored.

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

Override the root ruler style for an individual node with `hr_style=`:

```text
# Notes
    : fname=notes.jpg hr_style=dashed
    # before; ---; after
        : node hr_style=solid
    # Block with dotted ruler
        : block hr_style=dotted
        : before
        : ---
        : after
```

Node overrides accept `solid`, `dashed`, and `dotted`. They apply only to that
node; other nodes inherit the root style. Root `hr_spacing` still applies.

Use `cdef` on a block node to select the current theme's default regular-node fill color:

```text
# Default-colored block
    : block cdef
    : block body
```

For `block`, `verbatim`, and `draw` bodies, line selectors count from the first
nonblank body line. Internal blank lines count; surrounding blank lines and
the node header do not. This applies to both `lN` and end-relative `ElN`
selectors, including ranges such as `l[11-13]r`.

Code blocks can be highlighted and rendered as image-backed Graphviz nodes:

Set `code_theme` on the root to choose the default Pygments style for every code
node in that mindmap. A code node's `style=` overrides it, including
`style=default`. This setting is independent of the mindmap's `theme=` palette.

```text
# Notes
    : fname=notes.jpg theme=nord code_theme=monokai
    # Inherits monokai
        : code python
        : print("hello")
    # Uses its own style
        : code python style=friendly
        : print("world")
```

`code_theme` accepts Pygments style names. If omitted, the style is `default`;
unrecognized names fall back to `default`, just like node-level `style=`.
The setting applies only to the current mindmap.

Set a style directly on an individual code node:

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

## Markdown nodes

Add `md` (or `markdown`) on a node's attribute line. Every following body line
uses `:` at the same tab indentation as that attribute line:

```text
# Markdown examples
	: fname=markdown.jpg notitle
	# node with markdown
		: md md_width=420
		:
		: # header title 1
		:
		: i'm text of **bolded** text of paragraph.
	# normal sibling
		: node
```

The outer node title is retained. Markdown headings stay inside the node;
an unprefixed outline heading ends the body. Remove only the colon prefix and
one separator space when reading a body: extra indentation and trailing spaces
remain significant. Use a bare `:` for Markdown blank lines. Nest Markdown lists
with spaces **after** the colon, rather than additional outline tabs.

The supported profile is CommonMark with explicit strikethrough, highlight, and table rules,
plus static task-list markers. It renders headings, paragraphs, emphasis, inline
code, nested lists, quotes, separators, fenced/indented code, tables, and explicit
or reference links. Soft breaks become spaces; two trailing spaces or a trailing
backslash produce a hard break. Raw HTML is literal text. Links are styled text,
not clickable links in JPG output. Code is syntax-highlighted through Pygments
and embedded as an image; unknown languages fall back to plain text. The root
`code_theme=` selects the code style.

Use `==highlighted text==` for a pale yellow background with dark text in the
Markdown body. Highlights can contain other inline formatting, for example
`==important **bold** text==`, and wrap across lines. Use exactly two equals signs
on each side, without spaces just inside the markers. Escaped markers
(`\=\=literal\=\=`), unmatched markers, and markers inside code remain literal.

`md_width=420` sets the target body width in points. Prose wraps while retaining
inline styles; lists use hanging indentation and table columns share the available
width. An indivisible word or inline-code span may exceed that width. Code and
local images are scaled down to fit. Markdown image syntax is supported for one
image in its own paragraph; relative paths resolve against the `.otl` file.
Remote images are not downloaded. Missing images produce a source-located error.

Normal node colors, borders, icons, and edges still work. Use `hl1w2fmld`, for
example, to style the second word of the first **outer title** line. Body line/word
selectors (`l...` and `w...`) are rejected on Markdown nodes: use Markdown markup
for the body. The existing selector behavior on ordinary nodes is unchanged.
`md`, `code`, `block`, and `draw` cannot be combined on the same node.

Root Markdown uses the same body syntax. The attribute line containing `md` ends
the root's attribute group; subsequent colon-prefixed lines are body text:

```text
# Root title
# second title line
	: fname=notes.jpg notitle
	: theme=github-light root_symb=book
	: md hl2fm md_width=400
	: ## Heading inside the root
	:
	: A **Markdown** paragraph.
	# Child
		: node
```

See [examples/markdown.otl](examples/markdown.otl) for a complete example. Render it
from the example directory with `gvmm -f markdown.otl`, or choose an explicit
output with `gvmm -f examples/markdown.otl -i /tmp/markdown.jpg`.
