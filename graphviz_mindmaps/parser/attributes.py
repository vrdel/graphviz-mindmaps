import re


def ResolveColorNodeTypeToken(token, nodetype):
    if token in nodetype:
        return token

    aliases = {"nodes": "node"}
    match = re.match(
        r"^(c(?:green|cyan|blue|pink|red|yello|orang|black|grey)|impor|impog|impob|quest|commen|check|todo|title|node|nodes)(-?[0-9]+)$",
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
    match = re.match(r"^(impor|impog|impob|quest|date|title|link|saying)(-?[0-9]+)$", token)
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


def ApplyNodeAttributeTokens(
    tokens,
    tonode,
    state,
    labelhtml,
    arrlines,
    arrend,
    parse_attribute_line,
    resolve_color_node_type_token,
    resolve_symbol_names,
    gen_img_path,
    symbol_map,
    tmpdir,
    tempfile_module,
    subprocess_module,
):
    dood_count = 0

    for token in tokens:
        if token == "textleft":
            continue

        resolved_ntype = resolve_color_node_type_token(token)
        if resolved_ntype and resolved_ntype not in {"verbatim", "verbat", "draw"}:
            state.ntype = resolved_ntype
        else:
            parse_attribute_line(
                token,
                tonode,
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
