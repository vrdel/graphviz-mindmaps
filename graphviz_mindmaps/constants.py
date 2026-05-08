MAXDEPTH = 32
DEFAULT_BGCOLOR = "#efefef"

fontcolor = {
    "def": "#000000",
    "r": "#B30000",
    "g": "#027b10",
    "b": "#151e94",
    "y": "#ebec50",
    "c": "#00948c",
    "p": "#94008b",
    "k": "#000000",
    "t": "#ffffff",
}

linecolors = {
    "r": "#FF8080",
    "g": "#8BFF80",
    "b": "#80CAFF",
    "y": "#FFF180",
    "c": "#80FFFB",
    "p": "#FF80E7",
    "k": "#000000",
}

subgraphcolors = {
    "r": "#FF000020",
    "g": "#00FF0020",
    "b": "#0000FF20",
    "y": "#FFF40020",
    "c": "#00FFD220",
    "p": "#FF00EA20",
    "w": "#FFFFFF20",
    "k": "#00000020",
    "t": "",
}

vrbtcolors = {
    "cgreen": "#dffde6",
    "cred": "#fde0df",
    "cblue": "#e1dffd",
    "ccyan": "#dffdfa",
    "cyello": "#fcfddf",
    "corang": "#fdecdf",
    "cpink": "#fddff3",
    "cwhite": "#fdfdfd",
    "def": "#dfeafd",
}

fontstyle = {"ul": "U", "ld": "B", "st": "S", "it": "I"}

font = {
    "comic": "Comic Sans MS",
    "mono": "Dejavu Sans Mono",
    "comicb": "Comic Sans MS Bold",
    "balsamiq": "Balsamiq Sans",
    "balsamiqb": "Balsamiq Sans Bold",
}

fontsize = {"s": "12", "m": "14", "l": "16", "xl": "20", "xxl": "24"}

nodetype = {
    "root": "fontsize=\"%s\" margin=\"0.5\" shape=cds style=radial color=\"#000000\" fillcolor=\"#dfdfdf\" gradientangle=\"90\"" % (fontsize["xxl"]),
    "quest": "shape=oval fontname=\"%s\" fontsize=\"%s\" margin=\"0,0\" style=\"radial\" fillcolor=\"#fffbab\" color=\"#8a8a8a\"" % (font["comic"], fontsize["l"]),
    "impor": "shape=signature fontsize=\"%s\" margin=\"0.25\" style=\"radial\" fillcolor=\"#ffb6c1\" color=\"#8a8a8a\"" % (fontsize["l"]),
    "impog": "shape=signature fontsize=\"%s\" margin=\"0.25\" style=\"radial\" fillcolor=\"#b6ffb7\" color=\"#8a8a8a\"" % (fontsize["l"]),
    "impob": "shape=signature fontsize=\"%s\" margin=\"0.25\" style=\"radial\" fillcolor=\"#b6e4ff\" color=\"#8a8a8a\"" % (fontsize["l"]),
    "impoy": "shape=signature fontsize=\"%s\" margin=\"0.25\" style=\"radial\" fillcolor=\"#fff4b6\" color=\"#8a8a8a\"" % (fontsize["l"]),
    "img": "shape=box style=\"radial\" fillcolor=\"#fbfbfb\" color=\"#8a8a8a\"",
    "imgil": "shape=box style=\"radial\" fillcolor=\"#fbfbfb\" color=\"#8a8a8a\"",
    "dood": "shape=underline fontcolor=\"%s\" color=\"#b8b8b8\"" % (fontcolor["def"]),
    "def": "shape=underline fontcolor=\"%s\" color=\"#b8b8b8\"" % (fontcolor["def"]),
    "underl": "color=\"#b8b8b8\" fontcolor=\"%s\" shape=underline " % (fontcolor["def"]),
    "node": "shape=box style=\"rounded,radial\" fontsize=\"%s\" fillcolor=\"#f4f4f4\" color=\"#6a6a6a\"" % (fontsize["l"]),
    "list": "shape=rect style=\"radial\" fontsize=\"%s\" fillcolor=\"#d3f6ff\" color=\"#6a6a6a\"" % (fontsize["l"]),
    "data": "shape=cylinder style=\"radial\" margin=\"0.1,0.3\" fontsize=\"%s\" fillcolor=\"#ffffff\" color=\"#6a6a6a\"" % (fontsize["l"]),
    "answer": "shape=cds style=\"radial\" fontsize=\"%s\" margin=\"0.2\" fillcolor=\"#BAFFAF\" color=\"#6a6a6a\"" % (fontsize["l"]),
    "title": "shape=doubleoctagon fontname=\"%s\" margin=\"0,0\" fontsize=\"%s\" style=\"radial\" fillcolor=\"#abffff\" color=\"#8a8a8a\"" % (font["comicb"], fontsize["l"]),
    "date": "shape=component gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15,0.15\" fillcolor=\"#fbfbfb;0.93:#B30E0E\" color=\"#8a8a8a\"",
    "link": "shape=component gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15,0.15\" fillcolor=\"#edf1ff;0.93:#3283c9\" color=\"#8a8a8a\"",
    "example": "shape=note fontname=\"%s\" gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15\" fillcolor=\"#18A828;0.15:#fbfbfb\" color=\"#8a8a8a\"" % (font["mono"]),
    "draw": "shape=component fontname=\"%s\" style=\"radial\" margin=\"0.15,0.15\" fillcolor=\"%s\" color=\"#8a8a8a\"" % (font["mono"], vrbtcolors["cwhite"]),
    "verbatim": "shape=component fontname=\"%s\" style=\"radial\" margin=\"0.15,0.15\" fillcolor=\"%s\" color=\"#8a8a8a\"" % (font["mono"], vrbtcolors["def"]),
    "commen": "shape=note fontname=\"%s\" fontsize=\"%s\" margin=\"0.2\" style=\"radial\" fillcolor=\"#FFF09A\" color=\"#8a8a8a\"" % (font["comic"], fontsize["l"]),
    "term": "shape=note fontname=\"%s\" gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15\" fillcolor=\"#fbfbfb\" color=\"#8a8a8a\"" % (font["mono"]),
    "check": "shape=rarrow fontcolor=\"%s\" margin=\"0.20\" style=\"filled\" fillcolor=\"#4A90D9\" fontcolor=\"#ffffff\" color=\"#4A90D9\"" % (fontcolor["def"]),
    "todo": "shape=box fontcolor=\"%s\" margin=\"0.20\" style=\"filled, diagonals\" fillcolor=\"#FFF09A\" fontcolor=\"#404040\" color=\"#404040\"" % (fontcolor["def"]),
    "decisi": "shape=diamond style=\"rounded,radial\" fontsize=\"%s\" fillcolor=\"#ffc990\" color=\"#8a8a8a\"" % (fontsize["l"]),
    "saying": "shape=egg style=\"radial\" margin=\"0.0,0.15\" fontsize=\"%s\" fillcolor=\"#A9FFFF\" color=\"#8a8a8a\"" % (fontsize["l"]),
    "cgreen": "shape=box style=\"rounded,radial\" fillcolor=\"#bcffc2\" color=\"#8a8a8a\"",
    "ccyan": "shape=box style=\"rounded,radial\" fillcolor=\"#b9ffff\" color=\"#8a8a8a\"",
    "cblue": "shape=box style=\"rounded,radial\" fillcolor=\"#b2d5fb\" color=\"#8a8a8a\"",
    "cpink": "shape=box style=\"rounded,radial\" fillcolor=\"#ffb8fe\" color=\"#8a8a8a\"",
    "cred": "shape=box style=\"rounded,radial\" fillcolor=\"#fbc1bf\" color=\"#8a8a8a\"",
    "cyello": "shape=box style=\"rounded,radial\" fillcolor=\"#fefb88\" color=\"#8a8a8a\"",
    "corang": "shape=box style=\"rounded,radial\" fillcolor=\"#ffc990\" color=\"#8a8a8a\"",
    "cgrey": "shape=box style=\"rounded,radial\" fillcolor=\"#9e9e9e\" color=\"#8a8a8a\"",
    "cblack": "shape=box style=\"rounded,radial\" fillcolor=\"#2b2b2b\" color=\"#8a8a8a\"",
}

edgetype = {
    "impor": "style=\"bold\" color=\"#AD5459\"",
    "impog": "style=\"bold\" color=\"#64AD54\"",
    "impob": "style=\"bold\" color=\"#547EAD\"",
    "impoy": "style=\"bold\" color=\"#ADA454\"",
    "cred": "color=\"#AD3E39\"",
    "cgreen": "color=\"#45A135\"",
    "cblue": "color=\"#395BAD\"",
    "ccyan": "color=\"#39ACAD\"",
    "cyello": "color=\"#A6A037\"",
    "cpink": "color=\"#A837A0\"",
    "corang": "color=\"#AD7339\"",
}

edgecolors = {
    "r": "color=\"#AD3E39\"",
    "g": "color=\"#45A135\"",
    "b": "color=\"#395BAD\"",
    "c": "color=\"#39ACAD\"",
    "y": "color=\"#A6A037\"",
    "p": "color=\"#A837A0\"",
}

edgestyles = {"s": "solid", "d": "dashed", "t": "dotted", "l": "bold"}
edgeends = {"a": "empty", "m": "odiamond", "o": "odot", "v": "open", "x": "obox"}
arrcolors = {"d": "#5a5a5a", "r": "#AD3E39", "g": "#45A135", "b": "#395BAD", "y": "#A6A037", "c": "#39ACAD", "p": "#A837A0"}

html_rarrow1 = "<FONT FACE=\"FontAwesome\" POINT-SIZE=\"13\" COLOR=\"#6E1B31\">&#xf061;</FONT>"
html_larrow1 = "<FONT FACE=\"FontAwesome\" POINT-SIZE=\"13\" COLOR=\"#6E1B31\">&#xf060;</FONT>"
html_larrow2 = "<FONT FACE=\"FontAwesome\" POINT-SIZE=\"13\" COLOR=\"#6E1B31\">&#xf04a;</FONT>"
html_rarrow2 = "<FONT FACE=\"FontAwesome\" POINT-SIZE=\"13\" COLOR=\"#6E1B31\">&#xf04e;</FONT>"
html_equal = "<FONT POINT-SIZE=\"14\" COLOR=\"#155416\">&#9552;</FONT>"
