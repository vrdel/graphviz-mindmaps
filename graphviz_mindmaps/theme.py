import copy

from graphviz_mindmaps import constants


_DEFAULTS = {
    "fontcolor": copy.deepcopy(constants.fontcolor),
    "linecolors": copy.deepcopy(constants.linecolors),
    "vrbtcolors": copy.deepcopy(constants.vrbtcolors),
    "nodetype": copy.deepcopy(constants.nodetype),
    "edgetype": copy.deepcopy(constants.edgetype),
    "edgecolors": copy.deepcopy(constants.edgecolors),
    "arrcolors": copy.deepcopy(constants.arrcolors),
}


def ThemeNames():
    return ["default", *THEME_PALETTES]


def _restore_defaults():
    for name, values in _DEFAULTS.items():
        target = getattr(constants, name)
        target.clear()
        target.update(copy.deepcopy(values))
    return constants.DEFAULT_BGCOLOR


def _node(fill, border="#4c566a", shape="box", style="rounded,radial", fontcolor=None, margin=None):
    attrs = [
        "shape=%s" % shape,
        "style=\"%s\"" % style,
        "fontsize=\"%s\"" % constants.fontsize["l"],
        "fillcolor=\"%s\"" % fill,
        "color=\"%s\"" % border,
    ]
    if fontcolor:
        attrs.append("fontcolor=\"%s\"" % fontcolor)
    if margin:
        attrs.append("margin=\"%s\"" % margin)
    return " ".join(attrs)


def _component(fill, border="#4c566a", fontname=None):
    attrs = [
        "shape=component",
        "style=\"radial\"",
        "margin=\"0.15,0.15\"",
        "fillcolor=\"%s\"" % fill,
        "color=\"%s\"" % border,
    ]
    if fontname:
        attrs.insert(1, "fontname=\"%s\"" % fontname)
    return " ".join(attrs)


def _apply_palette(palette):
    fg = palette["fg"]
    bg = palette["bg"]
    panel = palette["panel"]
    border = palette["border"]
    muted = palette["muted"]
    accent = palette["accent"]
    red = palette["red"]
    green = palette["green"]
    blue = palette["blue"]
    yellow = palette["yellow"]
    cyan = palette["cyan"]
    purple = palette["purple"]
    orange = palette["orange"]

    constants.fontcolor.update({
        "def": fg,
        "r": red,
        "g": green,
        "b": blue,
        "y": yellow,
        "c": cyan,
        "p": purple,
        "k": bg,
        "t": fg,
    })

    constants.linecolors.update({
        "r": red,
        "g": green,
        "b": blue,
        "y": yellow,
        "c": cyan,
        "p": purple,
        "k": bg,
    })

    constants.vrbtcolors.update({
        "cdef": panel,
        "cgreen": palette["green_bg"],
        "cred": palette["red_bg"],
        "cblue": palette["blue_bg"],
        "ccyan": palette["cyan_bg"],
        "cyello": palette["yellow_bg"],
        "corang": palette["orange_bg"],
        "cpink": palette["purple_bg"],
        "cwhite": palette["white_bg"],
        "def": palette["verbatim_bg"],
    })

    constants.nodetype.update({
        "root": "fontsize=\"%s\" margin=\"0.5\" shape=cds style=radial color=\"%s\" fillcolor=\"%s\" gradientangle=\"90\" fontcolor=\"%s\"" % (constants.fontsize["xxl"], accent, panel, fg),
        "def": "shape=underline fontcolor=\"%s\" color=\"%s\"" % (fg, border),
        "underl": "shape=underline fontcolor=\"%s\" color=\"%s\"" % (fg, border),
        "node": _node(panel, border=border, fontcolor=fg),
        "list": _node(palette["cyan_bg"], border=border, shape="rect", style="radial", fontcolor=fg),
        "data": _node(panel, border=border, shape="cylinder", style="radial", fontcolor=fg, margin="0.1,0.3"),
        "answer": _node(palette["green_bg"], border=green, shape="cds", style="radial", fontcolor=fg, margin="0.2"),
        "quest": _node(palette["yellow_bg"], border=yellow, shape="oval", style="radial", fontcolor=fg, margin="0,0"),
        "title": "shape=doubleoctagon fontname=\"%s\" margin=\"0,0\" fontsize=\"%s\" style=\"radial\" fillcolor=\"%s\" color=\"%s\" fontcolor=\"%s\"" % (constants.font["comicb"], constants.fontsize["l"], accent, blue, fg),
        "impor": "shape=signature fontsize=\"%s\" margin=\"0.25\" style=\"radial\" fillcolor=\"%s\" color=\"%s\" fontcolor=\"%s\"" % (constants.fontsize["l"], palette["red_bg"], red, fg),
        "impog": "shape=signature fontsize=\"%s\" margin=\"0.25\" style=\"radial\" fillcolor=\"%s\" color=\"%s\" fontcolor=\"%s\"" % (constants.fontsize["l"], palette["green_bg"], green, fg),
        "impob": "shape=signature fontsize=\"%s\" margin=\"0.25\" style=\"radial\" fillcolor=\"%s\" color=\"%s\" fontcolor=\"%s\"" % (constants.fontsize["l"], palette["blue_bg"], blue, fg),
        "impoy": "shape=signature fontsize=\"%s\" margin=\"0.25\" style=\"radial\" fillcolor=\"%s\" color=\"%s\" fontcolor=\"%s\"" % (constants.fontsize["l"], palette["yellow_bg"], yellow, fg),
        "img": _node(panel, border=border, shape="none", style="radial", fontcolor=fg),
        "imgil": _node(panel, border=border, style="radial", fontcolor=fg),
        "dood": "shape=underline fontcolor=\"%s\" color=\"%s\"" % (fg, border),
        "date": "shape=component gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15,0.15\" fillcolor=\"%s;0.93:%s\" color=\"%s\" fontcolor=\"%s\"" % (panel, red, border, fg),
        "link": "shape=component gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15,0.15\" fillcolor=\"%s;0.93:%s\" color=\"%s\" fontcolor=\"%s\"" % (panel, blue, border, fg),
        "example": "shape=note fontname=\"%s\" gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15\" fillcolor=\"%s;0.15:%s\" color=\"%s\" fontcolor=\"%s\"" % (constants.font["mono"], palette["green_bg"], panel, border, fg),
        "draw": _component(constants.vrbtcolors["cwhite"], border=border, fontname=constants.font["mono"]),
        "verbatim": _component(constants.vrbtcolors["def"], border=border, fontname=constants.font["mono"]),
        "commen": "shape=note fontname=\"%s\" fontsize=\"%s\" margin=\"0.2\" style=\"radial\" fillcolor=\"%s\" color=\"%s\" fontcolor=\"%s\"" % (constants.font["comic"], constants.fontsize["l"], palette["yellow_bg"], border, fg),
        "term": "shape=note fontname=\"%s\" gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15\" fillcolor=\"%s\" color=\"%s\" fontcolor=\"%s\"" % (constants.font["mono"], panel, border, fg),
        "check": "shape=rarrow margin=\"0.20\" style=\"filled\" fillcolor=\"%s\" fontcolor=\"%s\" color=\"%s\"" % (panel, fg, blue),
        "todo": "shape=box margin=\"0.20\" fontsize=\"18\" style=\"filled, diagonals\" fillcolor=\"%s\" fontcolor=\"%s\" color=\"%s\"" % (palette["yellow_bg"], fg, yellow),
        "decisi": _node(palette["orange_bg"], border=orange, shape="diamond", fontcolor=fg),
        "saying": _node(palette["cyan_bg"], border=cyan, shape="egg", style="radial", fontcolor=fg, margin="0.0,0.15"),
        "cgreen": _node(palette["green_bg"], border=green, fontcolor=fg),
        "ccyan": _node(palette["cyan_bg"], border=cyan, fontcolor=fg),
        "cblue": _node(palette["blue_bg"], border=blue, fontcolor=fg),
        "cpink": _node(palette["purple_bg"], border=purple, fontcolor=fg),
        "cred": _node(palette["red_bg"], border=red, fontcolor=fg),
        "cyello": _node(palette["yellow_bg"], border=yellow, fontcolor=fg),
        "corang": _node(palette["orange_bg"], border=orange, fontcolor=fg),
        "cgrey": _node(muted, border=border, fontcolor=fg),
        "cblack": _node(bg, border=border, fontcolor=fg),
    })

    constants.edgetype.update({
        "impor": "style=\"bold\" color=\"%s\"" % red,
        "impog": "style=\"bold\" color=\"%s\"" % green,
        "impob": "style=\"bold\" color=\"%s\"" % blue,
        "impoy": "style=\"bold\" color=\"%s\"" % yellow,
        "cred": "color=\"%s\"" % red,
        "cgreen": "color=\"%s\"" % green,
        "cblue": "color=\"%s\"" % blue,
        "ccyan": "color=\"%s\"" % cyan,
        "cyello": "color=\"%s\"" % yellow,
        "cpink": "color=\"%s\"" % purple,
        "corang": "color=\"%s\"" % orange,
    })

    constants.edgecolors.update({
        "r": "color=\"%s\"" % red,
        "g": "color=\"%s\"" % green,
        "b": "color=\"%s\"" % blue,
        "c": "color=\"%s\"" % cyan,
        "y": "color=\"%s\"" % yellow,
        "p": "color=\"%s\"" % purple,
    })
    constants.arrcolors.update({
        "d": fg,
        "r": red,
        "g": green,
        "b": blue,
        "y": yellow,
        "c": cyan,
        "p": purple,
    })

    return palette["bg"]


THEME_PALETTES = {
    "nord": {
        "bg": "#2e3440",
        "fg": "#eceff4",
        "panel": "#3b4252",
        "border": "#4c566a",
        "muted": "#4c566a",
        "accent": "#5e81ac",
        "red": "#bf616a",
        "green": "#a3be8c",
        "blue": "#81a1c1",
        "yellow": "#ebcb8b",
        "cyan": "#88c0d0",
        "purple": "#b48ead",
        "orange": "#d08770",
        "red_bg": "#5b3d43",
        "green_bg": "#3f5142",
        "blue_bg": "#344154",
        "yellow_bg": "#4a4634",
        "cyan_bg": "#34494d",
        "purple_bg": "#47394d",
        "orange_bg": "#4d3d34",
        "white_bg": "#eceff4",
        "verbatim_bg": "#3b4252",
    },
    "papercolor": {
        "bg": "#eeeeee",
        "fg": "#444444",
        "panel": "#ffffff",
        "border": "#bcbcbc",
        "muted": "#d0d0d0",
        "accent": "#0087af",
        "red": "#af0000",
        "green": "#008700",
        "blue": "#005faf",
        "yellow": "#d7af00",
        "cyan": "#0087af",
        "purple": "#8787af",
        "orange": "#d75f00",
        "red_bg": "#ffd7d7",
        "green_bg": "#d7ffd7",
        "blue_bg": "#d7eaff",
        "yellow_bg": "#fff5cc",
        "cyan_bg": "#d7ffff",
        "purple_bg": "#eadfff",
        "orange_bg": "#ffe6d7",
        "white_bg": "#ffffff",
        "verbatim_bg": "#f7f7f7",
    },
    "papercolor-dark": {
        "bg": "#1c1c1c",
        "fg": "#d0d0d0",
        "panel": "#303030",
        "border": "#5f5f5f",
        "muted": "#444444",
        "accent": "#5fafaf",
        "red": "#af5f5f",
        "green": "#5faf5f",
        "blue": "#5fafd7",
        "yellow": "#d7af5f",
        "cyan": "#5fafaf",
        "purple": "#af87d7",
        "orange": "#d7875f",
        "red_bg": "#3a2828",
        "green_bg": "#283a28",
        "blue_bg": "#283440",
        "yellow_bg": "#3c3628",
        "cyan_bg": "#283a3a",
        "purple_bg": "#342c40",
        "orange_bg": "#3c3028",
        "white_bg": "#eeeeee",
        "verbatim_bg": "#262626",
    },
    "monokai": {
        "bg": "#272822",
        "fg": "#f8f8f2",
        "panel": "#3e3d32",
        "border": "#75715e",
        "muted": "#49483e",
        "accent": "#66d9ef",
        "red": "#f92672",
        "green": "#a6e22e",
        "blue": "#66d9ef",
        "yellow": "#e6db74",
        "cyan": "#a1efe4",
        "purple": "#ae81ff",
        "orange": "#fd971f",
        "red_bg": "#4a2634",
        "green_bg": "#344622",
        "blue_bg": "#263f46",
        "yellow_bg": "#49452a",
        "cyan_bg": "#284844",
        "purple_bg": "#3b3153",
        "orange_bg": "#4c351f",
        "white_bg": "#f8f8f2",
        "verbatim_bg": "#2f3029",
    },
    "gruvbox": {
        "bg": "#282828",
        "fg": "#ebdbb2",
        "panel": "#3c3836",
        "border": "#665c54",
        "muted": "#504945",
        "accent": "#83a598",
        "red": "#fb4934",
        "green": "#b8bb26",
        "blue": "#83a598",
        "yellow": "#fabd2f",
        "cyan": "#8ec07c",
        "purple": "#d3869b",
        "orange": "#fe8019",
        "red_bg": "#4c2f2a",
        "green_bg": "#45472a",
        "blue_bg": "#334349",
        "yellow_bg": "#4d4227",
        "cyan_bg": "#374832",
        "purple_bg": "#493642",
        "orange_bg": "#4d3928",
        "white_bg": "#fbf1c7",
        "verbatim_bg": "#32302f",
    },
    "solarized": {
        "bg": "#002b36",
        "fg": "#93a1a1",
        "panel": "#073642",
        "border": "#586e75",
        "muted": "#16424d",
        "accent": "#268bd2",
        "red": "#dc322f",
        "green": "#859900",
        "blue": "#268bd2",
        "yellow": "#b58900",
        "cyan": "#2aa198",
        "purple": "#6c71c4",
        "orange": "#cb4b16",
        "red_bg": "#4b2f35",
        "green_bg": "#34422c",
        "blue_bg": "#123f55",
        "yellow_bg": "#443d22",
        "cyan_bg": "#123f43",
        "purple_bg": "#30364f",
        "orange_bg": "#4a3328",
        "white_bg": "#fdf6e3",
        "verbatim_bg": "#073642",
    },
    # Published base/accent colors; node fills blend 14% accent into the panel.
    "solarized-light": {
        "bg": "#fdf6e3",
        "fg": "#657b83",
        "panel": "#eee8d5",
        "border": "#93a1a1",
        "muted": "#eee8d5",
        "accent": "#268bd2",
        "red": "#dc322f",
        "green": "#859900",
        "blue": "#268bd2",
        "yellow": "#b58900",
        "cyan": "#2aa198",
        "purple": "#6c71c4",
        "orange": "#cb4b16",
        "red_bg": "#ebcfbe",
        "green_bg": "#dfddb7",
        "blue_bg": "#d2dbd5",
        "yellow_bg": "#e6dbb7",
        "cyan_bg": "#d3decc",
        "purple_bg": "#dcd7d3",
        "orange_bg": "#e9d2ba",
        "white_bg": "#fdf6e3",
        "verbatim_bg": "#eee8d5",
    },
    "catppuccin-latte": {
        "bg": "#eff1f5",
        "fg": "#4c4f69",
        "panel": "#eff1f5",
        "border": "#9ca0b0",
        "muted": "#ccd0da",
        "accent": "#1e66f5",
        "red": "#d20f39",
        "green": "#40a02b",
        "blue": "#1e66f5",
        "yellow": "#df8e1d",
        "cyan": "#179299",
        "purple": "#8839ef",
        "orange": "#fe640b",
        "red_bg": "#ebd1db",
        "green_bg": "#d6e6d9",
        "blue_bg": "#d2def5",
        "yellow_bg": "#ede3d7",
        "cyan_bg": "#d1e4e8",
        "purple_bg": "#e1d7f4",
        "orange_bg": "#f1ddd4",
        "white_bg": "#eff1f5",
        "verbatim_bg": "#eff1f5",
    },
    "rose-pine-dawn": {
        "bg": "#faf4ed",
        "fg": "#464261",
        "panel": "#fffaf3",
        "border": "#9893a5",
        "muted": "#dfdad9",
        "accent": "#286983",
        "red": "#b4637a",
        "green": "#6d8f89",
        "blue": "#286983",
        "yellow": "#ea9d34",
        "cyan": "#56949f",
        "purple": "#907aa9",
        "orange": "#d7827e",
        "red_bg": "#f4e5e2",
        "green_bg": "#ebebe4",
        "blue_bg": "#e1e6e3",
        "yellow_bg": "#fcedd8",
        "cyan_bg": "#e7ece7",
        "purple_bg": "#efe8e9",
        "orange_bg": "#f9e9e3",
        "white_bg": "#faf4ed",
        "verbatim_bg": "#fffaf3",
    },
    "github-light": {
        "bg": "#ffffff",
        "fg": "#1f2328",
        "panel": "#f6f8fa",
        "border": "#d1d9e0",
        "muted": "#e8ecf0",
        "accent": "#0969da",
        "red": "#d1242f",
        "green": "#1a7f37",
        "blue": "#0969da",
        "yellow": "#9a6700",
        "cyan": "#0969da",
        "purple": "#8250df",
        "orange": "#bc4c00",
        "red_bg": "#f1dade",
        "green_bg": "#d7e7df",
        "blue_bg": "#d5e4f6",
        "yellow_bg": "#e9e4d7",
        "cyan_bg": "#d5e4f6",
        "purple_bg": "#e6e0f6",
        "orange_bg": "#eee0d7",
        "white_bg": "#ffffff",
        "verbatim_bg": "#f6f8fa",
    },
    "one-light": {
        "bg": "#fafafa",
        "fg": "#383a42",
        "panel": "#fafafa",
        "border": "#a0a1a7",
        "muted": "#e5e5e6",
        "accent": "#526fff",
        "red": "#e45649",
        "green": "#50a14f",
        "blue": "#4078f2",
        "yellow": "#c18401",
        "cyan": "#0184bc",
        "purple": "#a626a4",
        "orange": "#986801",
        "red_bg": "#f7e3e1",
        "green_bg": "#e2eee2",
        "blue_bg": "#e0e8f9",
        "yellow_bg": "#f2e9d7",
        "cyan_bg": "#d7e9f1",
        "purple_bg": "#eedcee",
        "orange_bg": "#ece6d7",
        "white_bg": "#fafafa",
        "verbatim_bg": "#fafafa",
    },
    "gruvbox-light": {
        "bg": "#fbf1c7",
        "fg": "#3c3836",
        "panel": "#f2e5bc",
        "border": "#a89984",
        "muted": "#d5c4a1",
        "accent": "#076678",
        "red": "#9d0006",
        "green": "#79740e",
        "blue": "#076678",
        "yellow": "#b57614",
        "cyan": "#427b58",
        "purple": "#8f3f71",
        "orange": "#af3a03",
        "red_bg": "#e6c5a3",
        "green_bg": "#e1d5a4",
        "blue_bg": "#d1d3b2",
        "yellow_bg": "#e9d5a4",
        "cyan_bg": "#d9d6ae",
        "purple_bg": "#e4ceb2",
        "orange_bg": "#e9cda2",
        "white_bg": "#fbf1c7",
        "verbatim_bg": "#f2e5bc",
    },

}


def ApplyTheme(name):
    if name == "default":
        return _restore_defaults()
    if name in THEME_PALETTES:
        _restore_defaults()
        return _apply_palette(THEME_PALETTES[name])
    raise ValueError("unknown theme: %s" % name)
