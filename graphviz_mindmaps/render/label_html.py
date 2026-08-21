import re

from graphviz_mindmaps.render.image_transform import IMAGE_TRANSFORM_KEY_PATTERN


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


def EscapeResidualHtmlAngles(text):
    protected_tags = {}

    def protect_tag(match):
        key = "__GVMM_HTML_%d__" % len(protected_tags)
        protected_tags[key] = match.group(0)
        return key

    protected = re.sub(
        r"</?(?:B|I|U|FONT)(?:\s+[^<>]*)?/?>|<BR/>|<TAB>|<WHITESP>",
        protect_tag,
        text,
    )
    protected = protected.replace("<", "&lt;").replace(">", "&gt;")

    for key, value in protected_tags.items():
        protected = protected.replace(key, value)

    return protected


def ApplyVerbatimCalloutRows(labelhtml):
    colors = {
        "RED": "#F2B8B8",
        "YELLOW": "#F1E6A8",
        "GREEN": "#B8E3B4",
        "CYAN": "#B4E4E3",
    }

    def row_content(row):
        match = re.search(r"<TD[^>]*>(.*)", row)
        if not match:
            return ""
        return match.group(1)

    def is_empty_row(row):
        content = row_content(row)
        content = re.sub(r"</?[^>]+>", "", content)
        content = re.sub(r"(?:<SEP>|&nbsp;|\s)+", "", content)
        return content == "" or content == "__GVMM_HR__"

    def is_bullet_row(row):
        content = re.sub(r"^(?:<SEP>|&nbsp;|\s)+", "", row_content(row))
        return re.match(r"^[•–*-](?:<SEP>|&nbsp;|\s)+", content) is not None

    def apply_bgcolor(row, color):
        if "BGCOLOR=" in row:
            return row
        return re.sub(
            r"<TD((?:\s+[^<>]*)?)>",
            r'<TD\1 BGCOLOR="%s">' % color,
            row,
            count=1,
        )

    merged = "<SEP>".join(labelhtml)
    rows = merged.split("</TD></TR><TR>")
    active_color = None
    for index, row in enumerate(rows):
        match = re.search(r"__GVMM_CALLOUT_(RED|YELLOW|GREEN|CYAN)__", row)
        if match:
            active_color = colors[match.group(1)]
            row = row.replace(match.group(0), "")
            rows[index] = apply_bgcolor(row, active_color)
            continue

        if is_empty_row(row) or is_bullet_row(row):
            active_color = None
        elif active_color:
            rows[index] = apply_bgcolor(row, active_color)

    for index in range(len(rows) - 1):
        rows[index] = rows[index] + "</TD></TR><TR>"
    merged = "".join(rows)
    merged = re.sub(
        r"<TR><TD[^>]*>(?:<SEP>|&nbsp;|\s)*__GVMM_HR__(?:<SEP>|&nbsp;|\s)*</TD></TR>",
        "<HR/>",
        merged,
    )
    labelhtml[:] = merged.split("<SEP>")


def BuildNodeLabelHtml(label, vrbt, draw, html_larrow1, html_rarrow1, html_larrow2, html_rarrow2, img_path_resolver):
    ntype = ""

    if not vrbt and not draw and ("`" in label or "*" in label):
        label = ApplyInlineBacktickBold(label)

    image_pattern = IMAGE_TRANSFORM_KEY_PATTERN
    if re.match(image_pattern + r"[ ]*[=:]", label):
        match = re.match(r"(" + image_pattern + r")(?:[  ]*[=:][  ]*)(.*)", label)
        if match:
            splittedstr = [match.group(1), match.group(2)]
            labelhtml = [
                "<TABLE BORDER=\"0\" CELLBORDER=\"0\"><TR><TD CELLPADDING=\"0\" BORDER=\"1\"><IMG SRC=\""
                + img_path_resolver(splittedstr[1].strip(), splittedstr[0])
                + "\"/></TD></TR></TABLE>"
            ]
            return labelhtml, "img", label

    labelhtml = label.split()
    token_index = 0
    in_verbatim_header = bool(vrbt or draw)
    for token in list(labelhtml):
        if (not vrbt and not draw or in_verbatim_header) and token.find(";") > 0:
            labelhtml[token_index] = ConvertLinebreakMarkers(token)
        if "__GVMM_BODY_BOUNDARY__" in token:
            in_verbatim_header = False

        if token.find(">") == 0 and len(token) == 1:
            labelhtml[token_index] = token.replace(">", "&gt;")

        if token.find("<") == 0 and len(token) == 1:
            labelhtml[token_index] = token.replace("<", "&lt;")

        if not vrbt and not draw:
            HtmlCompositeArrow("<=", html_larrow2, token, token_index, labelhtml)
            HtmlCompositeArrow("=>", html_rarrow2, token, token_index, labelhtml)
            HtmlCompositeArrow("->", html_rarrow1, token, token_index, labelhtml)
            HtmlCompositeArrow("<-", html_larrow1, token, token_index, labelhtml)
        else:
            if "__GVMM_LARROW1__" in labelhtml[token_index]:
                labelhtml[token_index] = labelhtml[token_index].replace("__GVMM_LARROW1__", "<-")
                HtmlCompositeArrow("<-", html_larrow1, labelhtml[token_index], token_index, labelhtml)

            if "__GVMM_LARROW2__" in labelhtml[token_index]:
                labelhtml[token_index] = labelhtml[token_index].replace("__GVMM_LARROW2__", "<=")
                HtmlCompositeArrow("<=", html_larrow2, labelhtml[token_index], token_index, labelhtml)

            if "__GVMM_RARROW1__" in labelhtml[token_index]:
                labelhtml[token_index] = labelhtml[token_index].replace("__GVMM_RARROW1__", "->")
                HtmlCompositeArrow("->", html_rarrow1, labelhtml[token_index], token_index, labelhtml)

            if "__GVMM_RARROW2__" in labelhtml[token_index]:
                labelhtml[token_index] = labelhtml[token_index].replace("__GVMM_RARROW2__", "=>")
                HtmlCompositeArrow("=>", html_rarrow2, labelhtml[token_index], token_index, labelhtml)

            if '<-' in labelhtml[token_index]:
                labelhtml[token_index] = re.sub("<-", "&lt;-", labelhtml[token_index])

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

    labelhtml = [EscapeResidualHtmlAngles(token) for token in labelhtml]

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
    if vrbt or draw:
        ApplyVerbatimCalloutRows(labelhtml)
    return labelhtml, ntype, label


def InsertSymbolRows(labelhtml, symblist, symbcolor, symbsize, symbol_map, fontcolor):
    if not symblist:
        return

    index = 0
    symbols = ""
    while index < len(symblist):
        color = "COLOR=\"%s\"" % (fontcolor["r"])
        size = "POINT-SIZE=\"25\""
        for entry in symbcolor:
            if entry[0] - 1 == index:
                color = "COLOR=\"%s\"" % (entry[1])
                break
        for entry in symbsize:
            if entry[0] - 1 == index:
                size = "POINT-SIZE=\"%s\"" % (entry[1])
                break
        symbols += "<FONT FACE=\"FontAwesome\" %s %s>%s</FONT>&nbsp;" % (
            color,
            size,
            symbol_map[symblist[index]],
        )
        index += 1

    wasone = labelhtml[1]
    labelhtml[1] = symbols + "</TD></TR><TR><TD>"
    labelhtml.insert(2, wasone)


def PostAttrProcLabel(label, ntype, vrbt, draw, textleft=False):
    if ntype == "saying":
        label.insert(0, "<I>")
        label.insert(len(label), "</I>")
    if ntype == "example" or vrbt or draw:
        for index in range(len(label)):
            label[index] = label[index].replace("<TD", "<TD ALIGN=\"left\"")
    if ntype == "term":
        for index in range(len(label)):
            if index == 1:
                label[index] = label[index].replace("<TD", "<TD BGCOLOR=\"#18A828\"")
            elif index > 1:
                label[index] = label[index].replace("<TD", "<TD ALIGN=\"left\"")
    if ntype == "list" or textleft:
        for index in range(len(label)):
            label[index] = label[index].replace("<TD", "<TD ALIGN=\"left\"")
    if not vrbt and not draw:
        merged = "".join(label)
        merged = re.sub(r"<TR><TD(?: ALIGN=\"left\")?>(?:<FONT POINT-SIZE=\"[0-9]+\">)?----(?:&nbsp;)?(?:</FONT>)?</TD></TR>", "<HR/>", merged)
        merged = re.sub(r"<TR><TD(?: ALIGN=\"left\")?>(?:<FONT POINT-SIZE=\"[0-9]+\">)?---(?:&nbsp;)?(?:</FONT>)?</TD></TR>", "<HR/>", merged)
        merged = re.sub(r";?&nbsp;----</TD></TR>", "</TD></TR><HR/>", merged)
        merged = re.sub(r";?&nbsp;---</TD></TR>", "</TD></TR><HR/>", merged)
        merged = re.sub(r";?&nbsp;<HR/><TR><TD></TD></TR>", "</TD></TR><HR/>", merged)
        label[:] = [merged]


def PreAttrProcLabel(label, ntype, resolve_base_node_type_token, symbol_map, fontcolor):
    btype = resolve_base_node_type_token(ntype)

    if btype == "title":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"25\">" + symbol_map["info-circle"] + "</FONT></TD></TR><TR><TD>")
    elif btype == "date":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"25\">" + symbol_map["clock-o"] + "</FONT></TD></TR><TR><TD>")
    elif btype == "quest":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"25\">" + symbol_map["question-circle"] + "</FONT></TD></TR><TR><TD>")
    elif btype == "answer":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"25\">" + symbol_map["reply"] + "</FONT></TD></TR><TR><TD>")
    elif btype == "saying":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"15\">" + symbol_map["quote-left"] + "  " + symbol_map["quote-right"] + "</FONT></TD></TR><TR><TD>")
    elif btype == "impor" or btype == "impog" or btype == "impob" or btype == "impoy":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"25\">" + symbol_map["warning"] + "</FONT></TD></TR><TR><TD>")
    elif btype == "todo":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"25\">" + symbol_map["list-ol"] + "</FONT></TD></TR><TR><TD>")
    elif btype == "term":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"%s\" POINT-SIZE=\"1\">" % (fontcolor["k"]) + symbol_map["terminal"] + "</FONT></TD></TR><TR><TD>")
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"%s\" POINT-SIZE=\"15\">" % (fontcolor["k"]) + symbol_map["desktop"] + "</FONT>&nbsp;<FONT FACE=\"FontAwesome\" COLOR=\"%s\" POINT-SIZE=\"20\">" % (fontcolor["k"]) + symbol_map["terminal"] + "</FONT></TD></TR><TR><TD>")
    elif btype == "link":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"25\">" + symbol_map["link"] + "</FONT></TD></TR><TR><TD>")
