import os
import re
import unicodedata


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


def NormalizeVerbatimWhitespace(text):
    normalized = []

    for ch in text:
        if ch in ("\t", "\n", "\r", " "):
            normalized.append(ch)
        elif ch.isspace() or unicodedata.category(ch) == "Zs":
            normalized.append(" ")
        else:
            normalized.append(ch)

    return "".join(normalized)


def ResolveBaseNodeTypeToken(token):
    match = re.match(r"^(impor|impog|impob|quest|date|title|link|saying)(-?[0-9]+)$", token)
    if match:
        return match.group(1)
    return token


def HtmlCompositeArrow(arrow, htmlcode, token, token_index, labelhtml):
    found = token.find(arrow)
    if found == -1:
        return

    if found == 0 and len(token) == len(arrow):
        labelhtml[token_index] = token.replace(arrow, htmlcode)
    elif found == 0 and len(token) > len(arrow):
        splitstr = token.split(arrow, 1)
        labelhtml[token_index] = htmlcode
        labelhtml.insert(token_index + 1, splitstr[1])
    elif found > 0:
        splitstr = token.split(arrow, 1)
        labelhtml[token_index] = splitstr[0] + htmlcode + splitstr[1]

    return labelhtml[token_index]


def ApplyInlineBacktickBold(text, allow_linebreak=False, allow_asterisk=True):
    patterns = [
        r'`([^`]+?)`' if allow_linebreak else r'`([^`;]+?)`',
    ]

    if allow_asterisk:
        patterns.append(
            r'\*([^*]+?)\*' if allow_linebreak else r'\*([^*;]+?)\*'
        )

    for pattern in patterns:
        text = re.sub(pattern, r'<B>\1</B>', text)
    return text


def ConvertLinebreakMarkers(text):
    entities = {}

    def protect_entity(match):
        key = "__ENTITY_%d__" % len(entities)
        entities[key] = match.group(0)
        return key

    protected = re.sub(r"&(?:#?[A-Za-z0-9]+);", protect_entity, text)
    protected = protected.replace(";", "<BR/>")

    for key, value in entities.items():
        protected = protected.replace(key, value)

    return protected


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


def ParseOtlname(keyword, line):
    match = re.search("(%s[ ]*=[ ]*)(\".*\")[ ]*" % keyword, line)
    if match is None:
        match = re.search(r"(%s[ ]*=[ ]*)([\w/.\-~_]*)[ ]*" % keyword, line)
    return match.group(2)


def ParseFnameLine(keyword, line):
    match = re.search("(%s[ ]*=[ ]*)(\".*\")[ ]*(notitle)?" % keyword, line)
    if match is None:
        match = re.search(r"(%s[ ]*=[ ]*)([\w/.\-~_]*)[ ]*(notitle)?" % keyword, line)

    return match.group(2), bool(match.group(3))


def ParseInlineAttrLine(keyword, line):
    match = re.search(r"%s[ ]*=[ ]*(\"[^\"]*\"|'[^']*'|[^\s]+)" % keyword, line)
    if not match:
        return None
    return match.group(1).strip().strip("\"'")


def JoinSepKeyValue(key, line):
    match_index = None
    for index, token in enumerate(line):
        if key in token:
            match_index = index

    if match_index:
        joined_tail = " ".join(line[match_index:])
        if re.match("%s = " % key, joined_tail):
            line[match_index] = line[match_index] + line[match_index + 1] + line[match_index + 2]
            del(line[match_index + 1])
            del(line[match_index + 1])
        elif re.match("(%s =)|(%s= )" % (key, key), joined_tail):
            line[match_index] = line[match_index] + line[match_index + 1]
            del(line[match_index + 1])


def GenImgPath(imgpath, environ=None):
    if environ is None:
        environ = os.environ

    if imgpath.startswith('/'):
        return imgpath
    if imgpath.startswith('~'):
        return imgpath.replace('~', environ['HOME'])
    return environ['PWD'] + '/' + imgpath


def ParLoc(line):
    parloc = line.find("#")
    if parloc == -1:
        parloc = line.find(":")
    if parloc == -1:
        parloc = line.find(";")
    if parloc == -1:
        parloc = line.find("|")
    return parloc


def _EscapeVerbatimBodyLine(text):
    text = NormalizeVerbatimWhitespace(text)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    if "`" in text or "*" in text:
        text = ApplyInlineBacktickBold(text, allow_linebreak=True, allow_asterisk=False)
    text = text.replace(" ", "<WHITESP>")
    text = text.replace("\t", "<TAB>")
    return text + "<BR/> "


def _CollectVerbatimNodeLine(lines, node_line_index):
    body_index = node_line_index + 2
    body_lines = []

    while body_index < len(lines) and '# ' not in lines[body_index] \
            and not re.search(r"\t\s*[a-zA-Z0-9]\s*", lines[body_index]):
        if "\t:" in lines[body_index]:
            body_lines.append(lines[body_index].lstrip("\t:").rstrip())
        elif "\t|" in lines[body_index]:
            body_lines.append(lines[body_index].lstrip("\t|").rstrip())
        elif "\t;" in lines[body_index]:
            body_lines.append(lines[body_index].lstrip("\t;").rstrip())

        if body_lines:
            body_lines[-1] = _EscapeVerbatimBodyLine(body_lines[-1])
        body_index += 1

    vrbtnode = "".join(body_lines).strip("<BR/>")
    vrbtnode = lines[node_line_index] + "<BR/>" + vrbtnode
    return vrbtnode, body_index


def ExtractMindmapBlocks(linesall):
    blocks = []
    worklines = list(linesall)
    cursor = 0

    while cursor < len(worklines) - 1:
        nextline = worklines[cursor + 1]
        level = worklines[cursor][:ParLoc(worklines[cursor])].count("\t")

        if not re.search(r"\t(:|;|\|)\s*fname", nextline):
            cursor += 1
            continue

        title = worklines[cursor]
        tabroot = level
        level += 1
        linesbymm = [title, nextline]

        scan_index = cursor + 2
        while scan_index < len(worklines) - 1 and level > tabroot:
            level = worklines[scan_index][:ParLoc(worklines[scan_index])].count("\t")
            if "# " in worklines[scan_index] and level > tabroot:
                linesbymm.append(worklines[scan_index])
                if "# " not in worklines[scan_index + 1] and level > tabroot:
                    linesbymm.append(worklines[scan_index + 1])
                    if "verbatim" in worklines[scan_index + 1] or \
                            "verbat" in worklines[scan_index + 1] or \
                            "draw" in worklines[scan_index + 1]:
                        vrbtnode, next_index = _CollectVerbatimNodeLine(worklines, scan_index)
                        linesbymm[-2] = vrbtnode
                        cursor = next_index - 1
                elif "# " in worklines[scan_index + 1] and \
                        worklines[scan_index + 1][:ParLoc(worklines[scan_index + 1])].count("\t") == level:
                    cursor = scan_index + 1
                    while level * "\t" + "# " in worklines[cursor]:
                        linesbymm[-1] = linesbymm[-1].rstrip() + worklines[cursor].replace("#", ";").strip()
                        del(worklines[cursor])
                    else:
                        if "# " not in worklines[cursor]:
                            linesbymm.append(worklines[cursor])
            scan_index += 1
        else:
            cursor = scan_index - 2
            blocks.append(linesbymm)

        cursor += 1

    return blocks


def ResolveNodeRenderFlags(nextline):
    vrbt = "verbatim" in nextline or "verbat" in nextline
    draw = "draw" in nextline
    textleft = "textleft" in nextline
    return vrbt, draw, textleft


def BuildNodeLabelHtml(label, vrbt, draw, html_larrow1, html_rarrow1, html_larrow2, html_rarrow2, img_path_resolver):
    ntype = ""

    if not vrbt and not draw and ("`" in label or "*" in label):
        label = ApplyInlineBacktickBold(label)

    if re.match("img[ ]*=", label):
        match = re.match("(img)(?:[  ]*=[  ]*)(.*)", label)
        if match:
            splittedstr = [match.group(1), match.group(2)]
            if splittedstr[0] == "img":
                labelhtml = [
                    "<TABLE BORDER=\"0\" CELLBORDER=\"0\"><TR><TD CELLPADDING=\"0\" BORDER=\"1\"><IMG SRC=\""
                    + img_path_resolver(splittedstr[1].strip())
                    + "\"/></TD></TR></TABLE>"
                ]
                return labelhtml, "img", label

    labelhtml = label.split()
    token_index = 0
    for token in list(labelhtml):
        if not vrbt and not draw and token.find(";") > 0:
            labelhtml[token_index] = ConvertLinebreakMarkers(token)

        if token.find(">") == 0 and len(token) == 1:
            labelhtml[token_index] = token.replace(">", "&gt;")

        if token.find("<") == 0 and len(token) == 1:
            labelhtml[token_index] = token.replace("<", "&lt;")

        if not vrbt and not draw:
            HtmlCompositeArrow("<=", html_larrow1, token, token_index, labelhtml)
            HtmlCompositeArrow("=>", html_rarrow1, token, token_index, labelhtml)
            HtmlCompositeArrow("->", html_rarrow2, token, token_index, labelhtml)
            HtmlCompositeArrow("<-", html_larrow2, token, token_index, labelhtml)
        else:
            HtmlCompositeArrow("<=", "&lt;&#9552;", token, token_index, labelhtml)
            HtmlCompositeArrow("=>", "&#9552;&gt;", token, token_index, labelhtml)

            if '<-' in labelhtml[token_index]:
                labelhtml[token_index] = re.sub("<-", "&lt;-", labelhtml[token_index])

            if '->' in labelhtml[token_index]:
                labelhtml[token_index] = re.sub("->", "-&gt;", labelhtml[token_index])

            if "><<" in labelhtml[token_index] or ">><" in labelhtml[token_index]:
                labelhtml[token_index] = re.sub(
                    "(?<=WHITESP>)<(<WHITESP>)",
                    "&lt;<WHITESP>",
                    labelhtml[token_index],
                )
                labelhtml[token_index] = re.sub(
                    "(?<=WHITESP>)>(<WHITESP>)",
                    "&gt;<WHITESP>",
                    labelhtml[token_index],
                )

        token_index += 1

    labelhtml.insert(0, "<TABLE CELLBORDER=\"0\" CELLSPACING=\"0\" BORDER=\"0\"><TR><TD>")
    i = 1
    while i < len(labelhtml):
        if "<TAB>" in labelhtml[i]:
            labelhtml[i] = labelhtml[i].replace("<TAB>", "&emsp;&emsp;")
        if "<WHITESP>" in labelhtml[i]:
            front = re.search("(<WHITESP>)*", labelhtml[i]).group(0)
            rem = re.split("^(<WHITESP>)*", labelhtml[i])[2]
            tokens = rem.split("<WHITESP>")
            del(labelhtml[i])
            for element in reversed(tokens):
                if element:
                    labelhtml.insert(i, element)
                else:
                    labelhtml[i] = " " + labelhtml[i]
            labelhtml[i] = " " * front.count("<WHITESP") + labelhtml[i]
        if "<BR/>" in labelhtml[i]:
            labelhtml[i] = labelhtml[i].replace("<BR/>", "</TD></TR><TR><TD>")
        else:
            labelhtml.insert(i + 1, "&nbsp;")
            i += 1
        i += 1
    labelhtml.insert(len(labelhtml), "</TD></TR></TABLE>")
    return labelhtml, ntype, label


def TokenizeNodeAttributeLine(nextline):
    tokens = nextline.split()
    spaced_groups = [
        [tokens[index], index]
        for index in range(len(tokens))
        if tokens[index].count("\"") == 1 or tokens[index].count("\'") == 1
    ]

    length = len(spaced_groups)
    for index in range(0, length, 2):
        if (spaced_groups[index + 1][1] - spaced_groups[index][1]) >= 2:
            spaced_groups[index][0] = spaced_groups[index][0] + " " + \
                    " ".join(tokens[spaced_groups[index][1] + 1: spaced_groups[index + 1][1]])

    deleted = 0
    for index in range(0, length, 2):
        del(tokens[spaced_groups[index][1] - deleted: spaced_groups[index + 1][1] + 1 - deleted])
        deleted += spaced_groups[index + 1][1] - spaced_groups[index][1] + 1

    tokens += [spaced_groups[index][0] + " " + spaced_groups[index + 1][0] for index in range(0, length, 2)]

    JoinSepKeyValue("img", tokens)
    JoinSepKeyValue("symb", tokens)
    return tokens
