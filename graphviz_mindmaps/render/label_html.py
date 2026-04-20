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
