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
    return ["default", "nord", "papercolor", "papercolor-dark", "monokai", "gruvbox", "solarized"]


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
        "img": _node(panel, border=border, style="radial", fontcolor=fg),
        "imgil": _node(panel, border=border, style="radial", fontcolor=fg),
        "dood": "shape=underline fontcolor=\"%s\" color=\"%s\"" % (fg, border),
        "date": "shape=component gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15,0.15\" fillcolor=\"%s;0.93:%s\" color=\"%s\" fontcolor=\"%s\"" % (panel, red, border, fg),
        "link": "shape=component gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15,0.15\" fillcolor=\"%s;0.93:%s\" color=\"%s\" fontcolor=\"%s\"" % (panel, blue, border, fg),
        "example": "shape=note fontname=\"%s\" gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15\" fillcolor=\"%s;0.15:%s\" color=\"%s\" fontcolor=\"%s\"" % (constants.font["mono"], palette["green_bg"], panel, border, fg),
        "draw": _component(constants.vrbtcolors["cwhite"], border=border, fontname=constants.font["mono"]),
        "verbatim": _component(constants.vrbtcolors["def"], border=border, fontname=constants.font["mono"]),
        "commen": "shape=note fontname=\"%s\" fontsize=\"%s\" margin=\"0.2\" style=\"radial\" fillcolor=\"%s\" color=\"%s\" fontcolor=\"%s\"" % (constants.font["comic"], constants.fontsize["l"], palette["yellow_bg"], border, fg),
        "term": "shape=note fontname=\"%s\" gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15\" fillcolor=\"%s\" color=\"%s\" fontcolor=\"%s\"" % (constants.font["mono"], panel, border, fg),
        "check": "shape=rarrow margin=\"0.20\" style=\"filled\" fillcolor=\"%s\" fontcolor=\"%s\" color=\"%s\"" % (blue, fg, blue),
        "todo": "shape=box margin=\"0.20\" style=\"filled, diagonals\" fillcolor=\"%s\" fontcolor=\"%s\" color=\"%s\"" % (palette["yellow_bg"], fg, yellow),
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


def _apply_nord():
    default_bgcolor = "#2e3440"

    constants.fontcolor.update({
        "def": "#eceff4",
        "r": "#bf616a",
        "g": "#a3be8c",
        "b": "#81a1c1",
        "y": "#ebcb8b",
        "c": "#88c0d0",
        "p": "#b48ead",
        "k": "#2e3440",
        "t": "#eceff4",
    })

    constants.linecolors.update({
        "r": "#bf616a",
        "g": "#a3be8c",
        "b": "#81a1c1",
        "y": "#ebcb8b",
        "c": "#8fbcbb",
        "p": "#b48ead",
        "k": "#2e3440",
    })

    constants.vrbtcolors.update({
        "cgreen": "#35483b",
        "cred": "#4c3438",
        "cblue": "#344154",
        "ccyan": "#34494d",
        "cyello": "#4d4734",
        "corang": "#4d3d34",
        "cpink": "#47394d",
        "cwhite": "#eceff4",
        "def": "#3b4252",
    })

    constants.nodetype.update({
        "root": "fontsize=\"%s\" margin=\"0.5\" shape=cds style=radial color=\"#81a1c1\" fillcolor=\"#3b4252\" gradientangle=\"90\" fontcolor=\"#eceff4\"" % constants.fontsize["xxl"],
        "def": "shape=underline fontcolor=\"#eceff4\" color=\"#4c566a\"",
        "underl": "shape=underline fontcolor=\"#eceff4\" color=\"#4c566a\"",
        "node": _node("#3b4252", fontcolor="#eceff4"),
        "list": _node("#334450", shape="rect", style="radial", fontcolor="#eceff4"),
        "data": _node("#3b4252", shape="cylinder", style="radial", fontcolor="#eceff4", margin="0.1,0.3"),
        "answer": _node("#3f5142", shape="cds", style="radial", fontcolor="#eceff4", margin="0.2"),
        "quest": _node("#4a4634", shape="oval", style="radial", fontcolor="#eceff4", margin="0,0"),
        "title": "shape=doubleoctagon fontname=\"%s\" margin=\"0,0\" fontsize=\"%s\" style=\"radial\" fillcolor=\"#5e81ac\" color=\"#81a1c1\" fontcolor=\"#eceff4\"" % (constants.font["comicb"], constants.fontsize["l"]),
        "impor": "shape=signature fontsize=\"%s\" margin=\"0.25\" style=\"radial\" fillcolor=\"#5b3d43\" color=\"#bf616a\" fontcolor=\"#eceff4\"" % constants.fontsize["l"],
        "impog": "shape=signature fontsize=\"%s\" margin=\"0.25\" style=\"radial\" fillcolor=\"#3f5142\" color=\"#a3be8c\" fontcolor=\"#eceff4\"" % constants.fontsize["l"],
        "impob": "shape=signature fontsize=\"%s\" margin=\"0.25\" style=\"radial\" fillcolor=\"#344154\" color=\"#81a1c1\" fontcolor=\"#eceff4\"" % constants.fontsize["l"],
        "img": _node("#3b4252", style="radial", fontcolor="#eceff4"),
        "imgil": _node("#3b4252", style="radial", fontcolor="#eceff4"),
        "dood": "shape=underline fontcolor=\"#eceff4\" color=\"#4c566a\"",
        "date": "shape=component gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15,0.15\" fillcolor=\"#3b4252;0.93:#bf616a\" color=\"#4c566a\" fontcolor=\"#eceff4\"",
        "link": "shape=component gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15,0.15\" fillcolor=\"#3b4252;0.93:#5e81ac\" color=\"#4c566a\" fontcolor=\"#eceff4\"",
        "example": "shape=note fontname=\"%s\" gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15\" fillcolor=\"#3f5142;0.15:#3b4252\" color=\"#4c566a\" fontcolor=\"#eceff4\"" % constants.font["mono"],
        "draw": _component(constants.vrbtcolors["cwhite"], fontname=constants.font["mono"]),
        "verbatim": _component(constants.vrbtcolors["def"], fontname=constants.font["mono"]),
        "commen": "shape=note fontname=\"%s\" fontsize=\"%s\" margin=\"0.2\" style=\"radial\" fillcolor=\"#4a4634\" color=\"#4c566a\" fontcolor=\"#eceff4\"" % (constants.font["comic"], constants.fontsize["l"]),
        "term": "shape=note fontname=\"%s\" gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15\" fillcolor=\"#3b4252\" color=\"#4c566a\" fontcolor=\"#eceff4\"" % constants.font["mono"],
        "check": "shape=rarrow margin=\"0.20\" style=\"filled\" fillcolor=\"#5e81ac\" fontcolor=\"#eceff4\" color=\"#5e81ac\"",
        "todo": "shape=box margin=\"0.20\" style=\"filled, diagonals\" fillcolor=\"#4a4634\" fontcolor=\"#eceff4\" color=\"#ebcb8b\"",
        "decisi": _node("#4d3d34", shape="diamond", fontcolor="#eceff4"),
        "saying": _node("#34494d", shape="egg", style="radial", fontcolor="#eceff4", margin="0.0,0.15"),
        "cgreen": _node("#3f5142", fontcolor="#eceff4"),
        "ccyan": _node("#34494d", fontcolor="#eceff4"),
        "cblue": _node("#344154", fontcolor="#eceff4"),
        "cpink": _node("#47394d", fontcolor="#eceff4"),
        "cred": _node("#5b3d43", fontcolor="#eceff4"),
        "cyello": _node("#4a4634", fontcolor="#eceff4"),
        "corang": _node("#4d3d34", fontcolor="#eceff4"),
        "cgrey": _node("#4c566a", fontcolor="#eceff4"),
        "cblack": _node("#2e3440", fontcolor="#eceff4"),
    })

    constants.edgetype.update({
        "impor": "style=\"bold\" color=\"#bf616a\"",
        "impog": "style=\"bold\" color=\"#a3be8c\"",
        "impob": "style=\"bold\" color=\"#81a1c1\"",
        "cred": "color=\"#bf616a\"",
        "cgreen": "color=\"#a3be8c\"",
        "cblue": "color=\"#81a1c1\"",
        "ccyan": "color=\"#88c0d0\"",
        "cyello": "color=\"#ebcb8b\"",
        "cpink": "color=\"#b48ead\"",
        "corang": "color=\"#d08770\"",
    })

    constants.edgecolors.update({
        "r": "color=\"#bf616a\"",
        "g": "color=\"#a3be8c\"",
        "b": "color=\"#81a1c1\"",
        "c": "color=\"#88c0d0\"",
        "y": "color=\"#ebcb8b\"",
        "p": "color=\"#b48ead\"",
    })
    constants.arrcolors.update({
        "d": "#d8dee9",
        "r": "#bf616a",
        "g": "#a3be8c",
        "b": "#81a1c1",
        "y": "#ebcb8b",
        "c": "#88c0d0",
        "p": "#b48ead",
    })

    return default_bgcolor


THEME_PALETTES = {
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
}


def ApplyTheme(name):
    if name == "default":
        return _restore_defaults()
    if name == "nord":
        _restore_defaults()
        return _apply_nord()
    if name in THEME_PALETTES:
        _restore_defaults()
        return _apply_palette(THEME_PALETTES[name])
    raise ValueError("unknown theme: %s" % name)
