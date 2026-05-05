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
    return ["default", "nord"]


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


def ApplyTheme(name):
    if name == "default":
        return _restore_defaults()
    if name == "nord":
        _restore_defaults()
        return _apply_nord()
    raise ValueError("unknown theme: %s" % name)
