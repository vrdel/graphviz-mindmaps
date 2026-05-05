import base64
import os
import re
import unicodedata


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


def _EscapeVerbatimBodyLine(text, apply_inline_backtick_bold):
    text = NormalizeVerbatimWhitespace(text)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    if "`" in text or "*" in text:
        text = apply_inline_backtick_bold(text, allow_linebreak=True, allow_asterisk=False)
    text = text.replace(" ", "<WHITESP>")
    text = text.replace("\t", "<TAB>")
    return text + "<BR/> "


def _CollectVerbatimNodeLine(lines, node_line_index, apply_inline_backtick_bold):
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
            body_lines[-1] = _EscapeVerbatimBodyLine(body_lines[-1], apply_inline_backtick_bold)
        body_index += 1

    vrbtnode = "".join(body_lines).strip("<BR/>")
    vrbtnode = lines[node_line_index] + "<BR/>" + vrbtnode
    return vrbtnode, body_index


def ParseCodeLanguage(line):
    match = re.search(r"(?:^|\s)code(?:[=: ]+([A-Za-z0-9_.+\-#]+))?", line)
    if not match:
        return None
    return match.group(1) or "text"


def _CollectCodeNodeLine(lines, node_line_index, language):
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

        body_index += 1

    source = "\n".join(body_lines)
    encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
    codenode = lines[node_line_index] + "<CODEBLOCK lang=\"%s\" data=\"%s\"/>" % (language, encoded)
    return codenode, body_index


def ExtractMindmapBlocks(linesall, apply_inline_backtick_bold):
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
                    language = ParseCodeLanguage(worklines[scan_index + 1])
                    if language:
                        codenode, next_index = _CollectCodeNodeLine(worklines, scan_index, language)
                        linesbymm[-2] = codenode
                        cursor = next_index - 1
                    elif "verbatim" in worklines[scan_index + 1] or \
                            "verbat" in worklines[scan_index + 1] or \
                            "draw" in worklines[scan_index + 1]:
                        vrbtnode, next_index = _CollectVerbatimNodeLine(worklines, scan_index, apply_inline_backtick_bold)
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
