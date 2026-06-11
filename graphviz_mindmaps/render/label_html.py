import re


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


def BuildNodeLabelHtml(label, vrbt, draw, html_larrow1, html_rarrow1, html_larrow2, html_rarrow2, img_path_resolver):
    ntype = ""

    if not vrbt and not draw and ("`" in label or "*" in label):
        label = ApplyInlineBacktickBold(label)

    image_pattern = r"img(?:_neg_gr_cn_sk|_neg_gr_sk|_neg_cn_sk|_neg_sk|_gr_sk|_sk|_neg_gr_cn|_neg_gr|_neg_cn|_neg|_gr)?"
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
    if vrbt or draw:
        label[1] = "<B><U><FONT>" + label[1]
        for index, _ in enumerate(label):
            if index >= 1 and "</TD>" in label[index]:
                label[index] = label[index].replace("</TD>", "</FONT></U></B></TD>")
                break
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
