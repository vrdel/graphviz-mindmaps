import math
import re

from graphviz_mindmaps.constants import (
    arrcolors,
    edgecolors,
    edgeends,
    edgestyles,
    font,
    fontcolor,
    fontstyle,
    linecolors,
    subgraphcolors,
)


def ResolveColorNodeTypeToken(token, nodetype):
    if token in nodetype:
        return token

    aliases = {"nodes": "node"}
    match = re.match(
        r"^(c(?:green|cyan|blue|pink|red|yello|orang|black|grey)|impor|impog|impob|impoy|quest|commen|check|todo|title|node|nodes)(-?[0-9]+)$",
        token,
    )
    if not match:
        return None

    base = aliases.get(match.group(1), match.group(1))
    if base not in nodetype:
        return None

    delta = int(match.group(2))
    fill_match = re.search(r'fillcolor="(#?[0-9A-Fa-f]{6})"', nodetype[base])
    if not fill_match:
        return None

    rgb = fill_match.group(1).lstrip("#")
    channels = [int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)]
    shifted = [min(255, max(0, channel + delta)) for channel in channels]
    newfill = "#%02x%02x%02x" % (shifted[0], shifted[1], shifted[2])

    nodetype[token] = nodetype[base].replace(fill_match.group(1), newfill, 1)
    return token


def ResolveVerbatimFillColorToken(token, vrbtcolors):
    if token in vrbtcolors:
        return vrbtcolors[token]

    match = re.match(
        r"^(c(?:green|cyan|blue|pink|red|yello|orang|white))(-?[0-9]+)$",
        token,
    )
    if not match:
        return None

    base = match.group(1)
    if base not in vrbtcolors:
        return None

    delta = int(match.group(2))
    rgb = vrbtcolors[base].lstrip("#")
    channels = [int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)]
    shifted = [min(255, max(0, channel + delta)) for channel in channels]
    newfill = "#%02x%02x%02x" % (shifted[0], shifted[1], shifted[2])

    vrbtcolors[token] = newfill
    return newfill


def ResolveBaseNodeTypeToken(token):
    match = re.match(r"^(impor|impog|impob|impoy|quest|date|title|link|saying)(-?[0-9]+)$", token)
    if match:
        return match.group(1)
    return token


def ResolveSymbolNames(spec, symbol_map):
    aliases = {
        "info": "info-circle",
        "quest": "question-circle",
        "warn": "warning",
    }

    resolved = []
    for name in spec.split(':'):
        name = name.strip()
        if not name:
            continue
        if name in symbol_map:
            resolved.append(name)
            continue
        aliased = aliases.get(name)
        if aliased and aliased in symbol_map:
            resolved.append(aliased)
    return resolved


def ParseAttributeLine(k, tonode, bgcolor, *args):
    wordcolor, wordfsize, wordfstyle, \
            linecolor, linefsize, linefstyle, \
            arrlines, arrend, \
            sgcolor, sgtitle, sgstyle, \
            edgecolor, edgestyle, edgend, edgethick, edglabel, \
            symbcolor, symbsize, linedate = args

    def ParseIdxSpec(spec, prefix):
        idx = []
        if not spec:
            return idx
        end_mode = prefix.startswith("E")

        def ParseSingleIdx(part):
            part = part.strip()
            if not part:
                return None
            nm = re.match(r"^([0-9]+)$", part)
            if nm:
                n = int(nm.group(1))
                return -n if end_mode else n
            return None

        body = spec[len(prefix):]
        if body.startswith("[") and body.endswith("]"):
            body = body[1:-1]
            for part in body.split(","):
                part = part.strip()
                if not part:
                    continue
                if "-" in part:
                    nm = re.match(r"([0-9]+)-([0-9]+)", part)
                    if nm:
                        s = int(nm.group(1))
                        e = int(nm.group(2))
                        if s <= e:
                            for i in range(s, e + 1):
                                idx.append(-i if end_mode else i)
                        else:
                            for i in range(s, e - 1, -1):
                                idx.append(-i if end_mode else i)
                else:
                    parsed = ParseSingleIdx(part)
                    if parsed is not None:
                        idx.append(parsed)

        else:
            parsed = ParseSingleIdx(body)
            if parsed is not None:
                idx.append(parsed)

        return idx

    m = re.search('(m?[rgbycpkt])?(f[0-9]+)?((?:ld|ul|st|it)+)?', k)
    if m.group(1):
        if m.group(1)[0] == "m":
            linecolor.insert(0, [0, linecolors[m.group(1)[1:]], False])
        else:
            linecolor.insert(0, [0, fontcolor[m.group(1)], True])
        if m.group(2):
            linefsize.append([0, m.group(2)[1:]])
        if m.group(3):
            for si in range(0, len(m.group(3)), 2):
                linefstyle.append([0, fontstyle[m.group(3)[si:si+2]]])
    elif m.group(2):
        linefsize.append([0, m.group(2)[1:]])
        if m.group(3):
            for si in range(0, len(m.group(3)), 2):
                linefstyle.append([0, fontstyle[m.group(3)[si:si+2]]])
    elif m.group(3):
        for si in range(0, len(m.group(3)), 2):
            linefstyle.append([0, fontstyle[m.group(3)[si:si+2]]])

    m = re.search(r'((?:E?l)(?:[0-9]+|\[[0-9,\-]+\]))?(m?[rgbycpkt])?(f[0-9]+)?((?:ld|ul|st|it)+)?', k)
    if m.group(1):
        lprefix = "El" if m.group(1).startswith("El") else "l"
        lineidx = ParseIdxSpec(m.group(1), lprefix)
        for li in lineidx:
            if m.group(4):
                for si in range(0, len(m.group(4)), 2):
                    linefstyle.append([li, fontstyle[m.group(4)[si:si+2]]])
            if m.group(3):
                linefsize.append([li, m.group(3)[1:]])
            if m.group(2):
                if m.group(2)[0] == "m":
                    linecolor.append([li, linecolors[m.group(2)[1:]], False])
                else:
                    linecolor.append([li, fontcolor[m.group(2)], True])

    m = re.search(r'((?:E?l)(?:[0-9]+|\[[0-9,\-]+\]))date', k)
    if m and m.group(1):
        lprefix = "El" if m.group(1).startswith("El") else "l"
        lineidx = ParseIdxSpec(m.group(1), lprefix)
        for li in lineidx:
            linedate.append([li, True])

    m = re.search(r'((?:E?l)(?:[0-9]+|\[[0-9,\-]+\]))?((?:E?w)(?:[0-9]+)|(?:E?w)(?:\[[0-9,\-]+\]))?([rgbycpkt])?(f[0-9]+)?((?:ld|ul|st|it)+)?', k)
    if m.group(2):
        if m.group(1):
            lprefix = "El" if m.group(1).startswith("El") else "l"
            lineidx = ParseIdxSpec(m.group(1), lprefix)
        else:
            lineidx = [None]
        wprefix = "Ew" if m.group(2).startswith("Ew") else "w"
        wordidx = ParseIdxSpec(m.group(2), wprefix)
        for li in lineidx:
            lmeta = {'lineskip': li} if li else None
            for wi in wordidx:
                if m.group(3):
                    wordcolor.append([wi, fontcolor[m.group(3)], lmeta])
                if m.group(4):
                    wordfsize.append([wi, m.group(4)[1:], lmeta])
                if m.group(5):
                    for si in range(0, len(m.group(5)), 2):
                        wordfstyle.append([wi, fontstyle[m.group(5)[si:si+2]], lmeta])

    m = re.search(r'(sym(?:[0-9]+)|sym(?:\[[0-9,]+\]))?([rgbycpkt])?(f[0-9]+)?', k)
    if m.group(1):
        if m.group(1).count("[") == 1 and m.group(1).count("]"):
            nm = re.findall('([0-9]+)(?:,?)', m.group(1))
            for i in nm:
                if m.group(2):
                    symbcolor.append([int(i), fontcolor[m.group(2)]])
                if m.group(3):
                    symbsize.append([int(i), m.group(3)[1:]])
        else:
            if m.group(2):
                symbcolor.append([int(m.group(1)[3:]), fontcolor[m.group(2)]])
            if m.group(3):
                symbsize.append([int(m.group(1)[3:]), m.group(3)[1:]])

    m = re.search(r'(sg([rgbycpwkt])(-?[0-9]+)?([sdtl](?!tart))?(start|end)?([\'\"](.*)[\'\"])?)?', k)
    if m.group(1):
        ckey = m.group(2)
        cval = subgraphcolors[ckey]

        if m.group(3) and cval:
            delta = int(m.group(3))
            mhex = re.match(r"^#([0-9A-Fa-f]{6})([0-9A-Fa-f]{2})?$", cval)
            if mhex:
                rgb = mhex.group(1)
                alpha = mhex.group(2) if mhex.group(2) else ""
                channels = [int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)]
                shifted = [min(255, max(0, ch + delta)) for ch in channels]
                cval = "#%02x%02x%02x%s" % (shifted[0], shifted[1], shifted[2], alpha)

        sgcolor.append(cval)
        if m.group(5) == "start":
            sgcolor[0] = "s" + sgcolor[0]
        elif m.group(5) == "end":
            sgcolor[0] = "e" + sgcolor[0]
        if m.group(4):
            sgstyle.append(edgestyles[m.group(4)])
            if not sgcolor[0]:
                sgcolor[0] = bgcolor
        if m.group(7):
            sgtitle.append(m.group(7))

    m = re.search('((arr[0-9]+)?([rgbycp])?(t[0-9]+)?(start|end)([\'\"].*[\'\"])?)?', k)
    if m.group(1):
        if m.group(5) == "start":
            penwidth = 5 if not m.group(4) else int(m.group(4)[1:])
            arrcolor = arrcolors["d"] if not m.group(3) else arrcolors[m.group(3)]
            arrlabel = "label=<<FONT COLOR=\"%s\">%s</FONT>> " % (fontcolor['r'], m.group(6).strip().strip("\'\"")) if m.group(6) else ""
            arrlines.append([m.group(2)[3:], [tonode], "[minlen=\"0.1\" maxlen=\"0.1\" dir=\"forward\" arrowtail=\"none\" arrowhead=\"vee\" arrowsize=\"2\" style=\"dashed\" constraint=\"false\" color=\"%s\" arrowsize=\"%f\" penwidth=\"%i\" %s]" % (arrcolor, math.sqrt(penwidth / 2), penwidth, arrlabel.replace(';', '<BR/>'))])
        elif m.group(5) == "end":
            arrend.update({m.group(2)[3:]: tonode})

    m = re.search('(edg)?([rgbycp])?(t[0-9]+)?([sdtl])?([amovx])?([\'\"].*[\'\"])?([he])?', k)
    if m.group(1):
        if m.group(2):
            edgecolor.append("%s" % (edgecolors[m.group(2)]))
        if m.group(3):
            edgethick.append("arrowsize=\"%f\" penwidth=\"%i\"" % (math.sqrt(int(m.group(3)[1:]) / 2), int(m.group(3)[1:])))
        elif not m.group(3):
            edgethick.append("arrowsize=\"%f\" penwidth=\"%i\"" % (math.sqrt(5 / 2), 5))
        if m.group(4):
            edgestyle.append("style=\"%s\"" % (edgestyles[m.group(4)]))
        if m.group(5):
            edgend.append("arrowhead=\"%s\"" % (edgeends[m.group(5)]))
        if m.group(7) and m.group(6):
            edgelabeltype = m.group(7)
            if edgelabeltype == 'h':
                edglabel.append("labelfloat=\"true\" labeldistance=\"6\" headlabel=<<FONT COLOR=\"%s\">%s</FONT>>" % (fontcolor['r'], m.group(6).strip().strip("\"").replace(';', '<BR/>')))
            elif edgelabeltype == 'e':
                edglabel.append("labelfloat=\"true\" labeldistance=\"6\" taillabel=<<FONT COLOR=\"%s\">%s</FONT>>" % (fontcolor['r'], m.group(6).strip().strip("\"").replace(';', '<BR/>')))
        elif m.group(6):
            edglabel.append("label=<<FONT COLOR=\"%s\">%s</FONT>>" % (fontcolor['r'], m.group(6).strip().strip("\"").replace(';', '<BR/>')))


def ApplyNodeAttributeTokens(
    tokens,
    tonode,
    state,
    labelhtml,
    arrlines,
    arrend,
    resolve_color_node_type_token,
    resolve_symbol_names,
    gen_img_path,
    symbol_map,
    tmpdir,
    tempfile_module,
    subprocess_module,
    bgcolor,
):
    dood_count = 0
    fontnames = {
        "fontcomic": font["comic"],
        "fontmono": font["mono"],
        "fontdefault": font["comic"],
        "fontsans": "Dejavu Sans",
        "fontserif": "Dejavu Serif",
    }

    for token in tokens:
        if token == "textleft":
            continue
        if token in fontnames:
            state.fontname = fontnames[token]
            continue

        resolved_ntype = resolve_color_node_type_token(token)
        if resolved_ntype and resolved_ntype not in {"verbatim", "verbat", "draw"}:
            state.ntype = resolved_ntype
        else:
            ParseAttributeLine(
                token,
                tonode,
                bgcolor,
                state.wordcolor,
                state.wordfsize,
                state.wordfstyle,
                state.linecolor,
                state.linefsize,
                state.linefstyle,
                arrlines,
                arrend,
                state.sgcolor,
                state.sgtitle,
                state.sgstyle,
                state.edgecolor,
                state.edgestyle,
                state.edgend,
                state.edgethick,
                state.edglabel,
                state.symbcolor,
                state.symbsize,
                state.linedate,
            )

        if token.find("=") <= 0:
            continue

        match = re.match(r"([\W\w]*)(?:=)(.*)", token)
        tokval = [match.group(1), match.group(2)]
        if tokval[0] == "img":
            labelhtml.insert(
                len(labelhtml) - 1,
                "</TD></TR><TR><TD COLSPAN=\"1\" CELLPADDING=\"0\" BORDER=\"1\"><IMG SRC=\""
                + gen_img_path(tokval[1].strip())
                + "\"/>",
            )
            state.ntype = "imgil"
        elif tokval[0] == "symb" and state.ntype != "imgil":
            state.symblist = resolve_symbol_names(tokval[1], symbol_map)
        elif tokval[0] == "dood":
            doodlist = tokval[1].split(":")
            if len(doodlist) > 1:
                tmpdir.append(tempfile_module.mkdtemp())
                exestring = "montage %s -geometry +3+0                                         -tile %dx -background Transparent %s/doodle.png" % (
                    " ".join(doodlist),
                    len(doodlist),
                    tmpdir[-1],
                )
                if subprocess_module.call(exestring, shell=True) == 0:
                    labelhtml.insert(
                        len(labelhtml) - 1,
                        "</TD></TR><TR><TD COLSPAN=\"1\" CELLPADDING=\"10\"                                            BORDER=\"0\"><IMG SRC=\""
                        + "%s/doodle.png" % (tmpdir[-1])
                        + "\"/>",
                    )
            else:
                labelhtml.insert(
                    len(labelhtml) - 1,
                    "</TD></TR><TR><TD COLSPAN=\"1\" CELLPADDING=\"10\"                                        BORDER=\"0\"><IMG SRC=\""
                    + gen_img_path(tokval[1])
                    + "\"/>",
                )
            dood_count += 1
            state.ntype = "dood"

    return dood_count
