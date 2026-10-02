import base64
import re
import subprocess
import tempfile

from graphviz_mindmaps.theme import ApplyTheme

from graphviz_mindmaps.fontawesome import FONT_DIR
from graphviz_mindmaps.render.code_image import ExtractCodeHighlights, RenderCodeImage
from graphviz_mindmaps.parser.markdown import DecodeMarkdownBody
from graphviz_mindmaps.render.markdown import AppendMarkdownLabel, RenderMarkdown
from graphviz_mindmaps.constants import (
    MAXDEPTH,
    edgetype,
    font,
    fontcolor,
    fontsize,
    html_larrow1,
    html_larrow2,
    html_rarrow1,
    html_rarrow2,
    nodetype,
    vrbtcolors,
)
from graphviz_mindmaps.execute.image import WriteDot, WriteImg
from graphviz_mindmaps.model.document import RenderRuntime, RenderSession
from graphviz_mindmaps.model.graph import (
    AppendNodeEdge,
    BuildNodeRefs,
    EmitTreeNodes,
    FinalizeEdges,
    Tree,
)
from graphviz_mindmaps.model.styles import (
    NodePrepState,
    SkipPositive,
    SkipPositiveLineScopedWords,
    SkipUnscopedWords,
)
from graphviz_mindmaps.parser.attributes import (
    ApplyNodeAttributeTokens,
    RenderTransformedImage,
    ResolveBaseNodeTypeToken,
    ResolveColorNodeTypeToken,
    ResolveSymbolNames,
    ResolveVerbatimFillColorToken,
)
from graphviz_mindmaps.render.image_transform import IsImageTransformKey
from graphviz_mindmaps.parser.outline import (
    GenImgPath,
    ParseFnameLine,
    ParseInlineAttrLine,
    ParseOtlname,
    ResolveNodeRenderFlags,
    TokenizeNodeAttributeLine,
)
from graphviz_mindmaps.render.label_html import (
    BuildNodeLabelHtml,
    InsertSymbolRows,
    PostAttrProcLabel,
    PreAttrProcLabel,
    SpanRowsAcrossImages,
)


def InsertImageRow(labelhtml, image_path):
    open_row = (
        "<TR><TD COLSPAN=\"1\" CELLPADDING=\"0\" BORDER=\"0\"><IMG SRC=\""
        + image_path
        + "\"/>"
    )
    if len(labelhtml) == 1 and "</TABLE>" in labelhtml[0]:
        row = open_row + "</TD></TR>"
        labelhtml[0] = labelhtml[0].replace("</TABLE>", row + "</TABLE>", 1)
    else:
        labelhtml.insert(len(labelhtml) - 1, "</TD></TR>" + open_row)


def StripCodeDirective(attrline):
    attrline = re.sub(r"(?<=\s)code(?:[=: ]+[A-Za-z0-9_.+\-#]+)?", "", attrline, count=1)
    return re.sub(r"(?<=\s)style=[A-Za-z0-9_.+\-#]+", "", attrline, count=1)


def ExtractVerbatimFillToken(attrline):
    for token in attrline.split():
        if ResolveVerbatimFillColorToken(token, vrbtcolors):
            return token
    return None


def ResolveLeafNodeType(lines):
    for line in lines[1:]:
        if re.search(r"(\t#) (.*)", line):
            break
        leaf_type = ParseInlineAttrLine("leaf", line)
        if not leaf_type:
            continue
        resolved = ResolveColorNodeTypeToken(leaf_type, nodetype)
        if not resolved:
            raise ValueError("unknown leaf node type: %s" % leaf_type)
        return resolved
    return "def"


def ResolveRootPenwidth(lines):
    for line in lines[1:]:
        if re.search(r"(\t#) (.*)", line):
            break
        penwidth = ParseInlineAttrLine("penwidth", line)
        if penwidth:
            return penwidth
    return "0"


def ResolveRootBgcolor(lines, default_bgcolor):
    for line in lines[1:]:
        if re.search(r"(\t#) (.*)", line):
            break
        bgcolor = ParseInlineAttrLine("bgcolor", line)
        if bgcolor:
            return bgcolor
        bg = ParseInlineAttrLine("bg", line)
        if bg:
            return bg
    return default_bgcolor


def ResolveRootSubgraphs(lines):
    for line in lines[1:]:
        if re.search(r"(\t#) (.*)", line):
            break
        if re.search(r"(?<!\S)sgno(?!\S)", line):
            return 0
        subgraphs = ParseInlineAttrLine("subgraphs", line)
        if subgraphs:
            value = subgraphs.lower()
            if value in {"false", "no", "off"}:
                return 0
            if value in {"true", "yes", "on"}:
                return None
            if re.match(r"^[0-9]+$", value):
                return int(value)
            if re.match(r"^[0-9]+(?:,[0-9]+)+$", value):
                return max(int(part) for part in value.split(","))
    return None


def ResolveRootOrientation(lines):
    orientations = {
        "lr": "LR",
        "left-right": "LR",
        "left_to_right": "LR",
        "tb": "TB",
        "top-bottom": "TB",
        "top_to_bottom": "TB",
        "bt": "BT",
        "bottom-top": "BT",
        "bottom_to_top": "BT",
        "rl": "RL",
        "right-left": "RL",
        "right_to_left": "RL",
    }
    for line in lines[1:]:
        if re.search(r"(\t#) (.*)", line):
            break
        orientation = ParseInlineAttrLine("orientation", line)
        if orientation:
            return orientations.get(orientation.lower(), "LR")
    return "LR"


def ResolveRootSgmargin(lines):
    for line in lines[1:]:
        if re.search(r"(\t#) (.*)", line):
            break
        sgmargin = ParseInlineAttrLine("sgmargin", line)
        if sgmargin:
            return sgmargin
        sgm = ParseInlineAttrLine("sgm", line)
        if sgm:
            return sgm
    return "8"


def ResolveRootHrStyle(lines):
    for line in lines[1:]:
        if re.search(r"(\t#) (.*)", line):
            break
        value = ParseInlineAttrLine("hr_style", line)
        if value:
            value = value.lower()
            if value not in {"solid", "dashed", "dotted"}:
                raise ValueError("hr_style must be solid, dashed, or dotted")
            return value
    return "solid"


def ResolveRootHrSpacing(lines):
    for line in lines[1:]:
        if re.search(r"(\t#) (.*)", line):
            break
        value = ParseInlineAttrLine("hr_spacing", line)
        if value:
            if not re.fullmatch(r"[0-9]+", value):
                raise ValueError("hr_spacing must be a nonnegative integer")
            return int(value)
    return 4


def ResolveRootNodeDefaults(lines):
    defaults = {}
    keymap = {
        "global_bc": "color",
        "global_bw": "penwidth",
        "global_bs": "style",
    }
    for line in lines[1:]:
        if re.search(r"(\t#) (.*)", line):
            break
        for key, dotkey in keymap.items():
            value = ParseInlineAttrLine(key, line)
            if value:
                defaults[dotkey] = value
    return defaults


def ResolveRootEdgeDefaults(lines):
    defaults = {}
    keymap = {
        "global_edge_color": "color",
        "global_ec": "color",
        "global_edge_style": "style",
        "global_es": "style",
    }
    for line in lines[1:]:
        if re.search(r"(\t#) (.*)", line):
            break
        for key, dotkey in keymap.items():
            value = ParseInlineAttrLine(key, line)
            if value:
                defaults[dotkey] = value
    return defaults


def IsOutlineLeaf(lines, index, level, tabnum):
    for candidate in lines[index + 1:]:
        if not re.search(r"(\t#) (.*)", candidate):
            continue
        next_level = candidate[:candidate.find("#")].count("\t") - tabnum
        return next_level <= level
    return True


def BuildRootLabel(lines, title, symbol_map, tree):
    symbols = []
    symbol_color = fontcolor["r"]
    symbol_colors = {}
    symbol_sizes = {}
    text_tokens = []
    for line in lines[1:]:
        if re.search(r"(\t#) (.*)", line):
            break
        value = ParseInlineAttrLine("root_symb", line)
        if value:
            symbols = ResolveSymbolNames(value, symbol_map)
        root_fg = ParseInlineAttrLine("root_fg", line)
        if root_fg:
            symbol_color = root_fg
        text_tokens.extend(
            token for token in TokenizeNodeAttributeLine(line)
            if re.match(r"^(?:E?[lhw])(?:[0-9]|\[|l[0-9]|l\[)", token)
        )
        for token in line.split():
            match = re.fullmatch(r"root_sym([0-9]+|\[[0-9]+(?:,[0-9]+)*\])([rgbycpkt])?(?:f([0-9]+))?", token)
            if not match:
                continue
            for index in map(int, match.group(1).strip("[]").split(",")):
                if match.group(2):
                    symbol_colors.setdefault(index, fontcolor[match.group(2)])
                if match.group(3):
                    symbol_sizes.setdefault(index, match.group(3))
    labelhtml, _, _ = BuildNodeLabelHtml(
        title, False, False, html_larrow1, html_rarrow1,
        html_larrow2, html_rarrow2, GenImgPath,
    )
    state = NodePrepState(ntype="root")
    ApplyNodeAttributeTokens(
        text_tokens, "node1", state, labelhtml, [], {},
        lambda token: None, ResolveSymbolNames, GenImgPath,
        symbol_map, [], tempfile, subprocess, "",
    )
    label_node = Tree.Node(
        tree, "node1", label=labelhtml, ntype="root",
        wordcolor=state.wordcolor, wordfsize=state.wordfsize,
        wordfstyle=state.wordfstyle, linecolor=state.linecolor,
        linefsize=state.linefsize, linefstyle=state.linefstyle,
        linefont=state.linefont, linedate=state.linedate,
    )
    label_node._wordattr(state.wordfont, "<FONT FACE=", "</FONT>")
    label_node.wordfsize()
    label_node.wordfstyle()
    label_node.linefsize()
    label_node.colorifywords()
    label_node.linefstyle()
    label_node.linefont()
    label_node.colorifylines()
    label_node.linedate()
    PostAttrProcLabel(label_node._label, "root", False, False, False)
    label = "".join(label_node._label)
    if symbols:
        icons = "&nbsp;".join(
            '<FONT FACE="FontAwesome" COLOR="%s" POINT-SIZE="%s">%s</FONT>'
            % (symbol_colors.get(index, symbol_color), symbol_sizes.get(index, "25"), symbol_map[name])
            for index, name in enumerate(symbols, start=1)
        )
        label = label.replace("<TR>", "<TR><TD>" + icons + "</TD></TR><TR>", 1)
    return label


def ResolveRootNodeAttributes(lines, attrs):
    for line in lines[1:]:
        if re.search(r"(\t#) (.*)", line):
            break
        for key, attribute in (("root_bg", "fillcolor"), ("root_fg", "fontcolor"),
                               ("root_bw", "penwidth"), ("root_bs", "style"),
                               ("root_bc", "color")):
            value = ParseInlineAttrLine(key, line)
            if value:
                pattern = r'\b%s=(?:"([^"]*)"|([^\s]+))' % attribute
                existing = re.search(pattern, attrs)
                if attribute == "style" and existing:
                    styles = (existing.group(1) or existing.group(2) or "").split(",")
                    styles = [style.strip() for style in styles
                              if style.strip() and style.strip() not in {"solid", "dashed", "dotted"}]
                    value = ",".join(dict.fromkeys(styles + value.split(",")))
                replacement = '%s="%s"' % (attribute, value)
                if existing:
                    attrs = re.sub(pattern, lambda match: replacement, attrs)
                else:
                    attrs += " " + replacement
    return attrs


def ResolveRootTheme(lines):
    for line in lines[1:]:
        if re.search(r"(\t#) (.*)", line):
            break
        value = ParseInlineAttrLine("theme", line)
        if value:
            return value
    return None


def ResolveRootCodeTheme(lines):
    for line in lines[1:]:
        if re.search(r"(\t#) (.*)", line):
            break
        value = ParseInlineAttrLine("code_theme", line)
        if value:
            return value
    return "default"


def GenDot(lines, argholder, session: RenderSession, runtime: RenderRuntime):
    root_heading, root_markdown = DecodeMarkdownBody(lines[0])
    lines = [root_heading, *lines[1:]]
    root_theme = ResolveRootTheme(lines)
    root_code_theme = ResolveRootCodeTheme(lines)
    theme_bgcolor = ApplyTheme(root_theme or runtime.theme_name)
    default_bgcolor = theme_bgcolor if root_theme else runtime.default_bgcolor
    tree = Tree(
        nodetype,
        vrbtcolors,
        fontcolor,
        font,
        fontsize,
        runtime.fontawesome_symb,
        ResolveVerbatimFillColorToken,
        PostAttrProcLabel,
    )
    parentlist = [None] * MAXDEPTH

    rootnodename = "node1"
    root = tree.addroot(rootnodename)
    parentlist[0] = root

    dotbuf = session.dotbuf
    title = session.title
    notitle = session.notitle
    bgcolor = session.bgcolor
    tmpdir = session.tmpdir

    def ResolveImagePath(image, image_key="img"):
        if IsImageTransformKey(image_key):
            return RenderTransformedImage(
                image,
                image_key,
                GenImgPath,
                tmpdir,
                tempfile,
            )
        return GenImgPath(image)

    jpgname, dotname = "", ""

    tabnum = lines[0].count("\t")

    match = re.search(r"(\t|#) (.*)", lines[0])
    title = match.group(2)

    bgcolor = ResolveRootBgcolor(lines, default_bgcolor)
    penwidth = ResolveRootPenwidth(lines)
    rankdir = ResolveRootOrientation(lines)
    tree.subgraph_depth = ResolveRootSubgraphs(lines)
    tree.default_sgmargin = ResolveRootSgmargin(lines)
    tree.hr_spacing = ResolveRootHrSpacing(lines)
    tree.hr_style = ResolveRootHrStyle(lines)
    root_node_defaults = ResolveRootNodeDefaults(lines)
    root_edge_defaults = ResolveRootEdgeDefaults(lines)
    node_default_attrs = {
        "fontname": font["comic"],
        "fontsize": fontsize["m"],
        "fontcolor": fontcolor["def"],
        "color": "#000000",
        "gradientangle": "90",
        "penwidth": penwidth,
    }
    node_default_attrs.update(root_node_defaults)
    tree.default_bordercolor = root_node_defaults.get("color")
    tree.default_borderwidth = root_node_defaults.get("penwidth")
    tree.default_borderstyle = root_node_defaults.get("style")
    node_default_attr = " ".join('%s="%s"' % (key, value) for key, value in node_default_attrs.items())
    edge_default_attrs = {
        "arrowhead": "none",
        "color": "#8a8a8a",
        "minlen": "3",
        "style": "tapered",
        "penwidth": "6",
        "dir": "forward",
        "arrowtail": "none",
        "fontname": font["comicb"],
        "fontsize": fontsize["l"],
        "fontcolor": fontcolor["b"],
    }
    edge_default_attrs.update(root_edge_defaults)
    edge_default_attr = " ".join('%s="%s"' % (key, value) for key, value in edge_default_attrs.items())
    root_attrs = ResolveRootNodeAttributes(lines, nodetype["root"])
    root_label = BuildRootLabel(lines, match.group(2), runtime.fontawesome_symb, tree)
    if root_markdown is not None:
        root_options = []
        for attr in lines[1:]:
            if re.match(r"^\t*# ", attr):
                break
            root_options.append(attr)
        root_options = ' '.join(root_options)
        root_label = AppendMarkdownLabel(root_label, RenderMarkdown(
            root_markdown, tmpdir, ParseInlineAttrLine('md_width', root_options) or 420,
            foreground=ParseInlineAttrLine('root_fg', root_options),
            code_theme=root_code_theme,
        ))

    dotbuf += "digraph G {\n\n\tnodesep=\"0.1\";\n\tnewrank=\"true\";\n\tcompound=\"false\";\n\tsplines=\"true\";\n\tordering=out;\n\trankdir=%s;\n\tranksep=0.1;\n\tfontpath=\"%s\";\n\tbgcolor=\"%s\";\n\n\tnode[%s];\n" % (rankdir, FONT_DIR, bgcolor, node_default_attr)
    dotbuf += "\tedge[%s];\n\n" % edge_default_attr
    dotbuf += "// %s\n" % (match.group(2))
    dotbuf += "\tsubgraph cluster000 {\n\n"
    dotbuf += "\t\tstyle=radial;\n\t\tordering=out;\n\t\tfillcolor=\"%s\";\n\t\tcolor=\"%s\";\n\n" % (bgcolor, bgcolor)
    dotbuf += "\t\t%s[%s label=<%s>];\n" % (rootnodename, root_attrs, root_label)

    dotname = "%s.dot" % (match.group(2))
    jpgname = "%s.jpg" % (match.group(2))
    leaf_ntype = ResolveLeafNodeType(lines)

    edge, arrlines = [], []
    arrend = {}
    nodelevel = [1] * MAXDEPTH

    for line_index, line in enumerate(lines[1:], start=1):
        if re.search(r"\t(:|\|)\s*fname", line):
            jpgname, should_hide_title = ParseFnameLine("fname", line)
            jpgname = jpgname.strip()
            if should_hide_title:
                session.notitle = True
                notitle = True
            if re.search("otlname", line):
                title = ParseOtlname("otlname", line) + "  -  " + title

        nextline = lines[line_index + 1] if line_index + 1 < len(lines) else line

        if re.search(r"(\t#) (.*)", line):
            level = line[:line.find("#")].count("\t") - tabnum

            match = re.search(r"(\t|#) (.*)", line)
            label = match.group(2)
            label, markdown_body = DecodeMarkdownBody(label)
            markdown_width = ParseInlineAttrLine('md_width', nextline) or 420
            code_match = re.search(r"<CODEBLOCK lang=\"([^\"]+)\"(?: style=\"([^\"]+)\")? data=\"([^\"]*)\"/>", label)
            code_source = None
            code_language = None
            code_style = root_code_theme
            code_image_path = None
            if code_match:
                code_language = code_match.group(1)
                code_style = code_match.group(2) or root_code_theme
                code_source = base64.b64decode(code_match.group(3)).decode("utf-8")
                label = label[:code_match.start()].rstrip()

            ntype = ""
            vrbt, draw, textleft = ResolveNodeRenderFlags(nextline)

            if code_source is not None:
                highlight_lines, nextline = ExtractCodeHighlights(nextline)
                if not tmpdir:
                    tmpdir.append(tempfile.mkdtemp())
                code_image_path = RenderCodeImage(
                    code_source, code_language, tmpdir, code_style, highlight_lines
                )
                try:
                    labelhtml, ntype, label = BuildNodeLabelHtml(
                        label,
                        vrbt,
                        draw,
                        html_larrow1,
                        html_rarrow1,
                        html_larrow2,
                        html_rarrow2,
                        ResolveImagePath,
                    )
                except (IndexError, KeyError) as exc:
                    print(exc, label)
            else:
                try:
                    labelhtml, ntype, label = BuildNodeLabelHtml(
                        label,
                        vrbt,
                        draw,
                        html_larrow1,
                        html_rarrow1,
                        html_larrow2,
                        html_rarrow2,
                        ResolveImagePath,
                    )
                except (IndexError, KeyError) as exc:
                    print(exc, label)

            state_obj = NodePrepState(ntype=ntype)
            fromnode, tonode, tabs = BuildNodeRefs(rootnodename, nodelevel, level)
            verbatim_fill_token = None

            if not re.search(r"(\t#) (.*)", nextline) and state_obj.ntype != "img":
                attrline = StripCodeDirective(nextline) if code_source is not None else nextline
                if vrbt or draw:
                    verbatim_fill_token = ExtractVerbatimFillToken(attrline)
                    if verbatim_fill_token:
                        attrline = re.sub(r"(?<!\S)%s(?!\S)" % re.escape(verbatim_fill_token), "", attrline, count=1)
                nextline = TokenizeNodeAttributeLine(attrline)
                ApplyNodeAttributeTokens(
                    nextline,
                    tonode,
                    state_obj,
                    labelhtml,
                    arrlines,
                    arrend,
                    lambda token: ResolveColorNodeTypeToken(token, nodetype),
                    ResolveSymbolNames,
                    GenImgPath,
                    runtime.fontawesome_symb,
                    tmpdir,
                    tempfile,
                    subprocess,
                    bgcolor,
                )
                if verbatim_fill_token and state_obj.ntype in {"", "def"}:
                    state_obj.ntype = verbatim_fill_token

            InsertSymbolRows(labelhtml, state_obj.symblist, state_obj.symbcolor, state_obj.symbsize, runtime.fontawesome_symb, fontcolor)

            ntype = state_obj.ntype
            if not ntype:
                if code_source is not None or markdown_body is not None:
                    ntype = "node"
                elif IsOutlineLeaf(lines, line_index, level, tabnum):
                    ntype = leaf_ntype
                else:
                    ntype = "def"
                state_obj.ntype = ntype
            PreAttrProcLabel(labelhtml, ntype, ResolveBaseNodeTypeToken, runtime.fontawesome_symb, fontcolor)
            SpanRowsAcrossImages(labelhtml, state_obj.embedded_image_count)

            if vrbt or draw:
                wordskip = len(line.split("<BR/>", 1)[0].split()) - 1
                SkipUnscopedWords(state_obj.wordfsize, s=wordskip)
                SkipUnscopedWords(state_obj.wordcolor, s=wordskip)
                SkipUnscopedWords(state_obj.wordfstyle, s=wordskip)

            if state_obj.symblist:
                SkipUnscopedWords(state_obj.wordfsize, s=len(state_obj.symblist))
                SkipUnscopedWords(state_obj.wordcolor, s=len(state_obj.symblist))
                SkipUnscopedWords(state_obj.wordfstyle, s=len(state_obj.symblist))

            if ntype == "term" or ntype == "link":
                SkipUnscopedWords(state_obj.wordfsize, s=2)
                SkipUnscopedWords(state_obj.wordcolor, s=2)
                SkipUnscopedWords(state_obj.wordfstyle, s=2)

            if ntype in {"title", "quest", "date", "impor", "impog", "impob", "impoy"} or (ntype != "img" and "FontAwesome" in labelhtml[1]):
                if state_obj.wordcolor:
                    SkipPositiveLineScopedWords(state_obj.wordcolor, lsinw=1)
                if state_obj.wordfsize:
                    SkipPositiveLineScopedWords(state_obj.wordfsize, lsinw=1)
                if state_obj.wordfstyle:
                    SkipPositiveLineScopedWords(state_obj.wordfstyle, lsinw=1)
                if state_obj.linedate:
                    SkipPositive(state_obj.linedate, s=1)
                if state_obj.linecolor and not state_obj.linecolor[0][0] == 0:
                    SkipPositive(state_obj.linecolor, s=1)
                if state_obj.linefsize and not state_obj.linefsize[0][0] == 0:
                    SkipPositive(state_obj.linefsize, s=1)
                if state_obj.linefstyle and not state_obj.linefstyle[0][0] == 0:
                    SkipPositive(state_obj.linefstyle, s=1)
                if state_obj.linefont and not state_obj.linefont[0][0] == 0:
                    SkipPositive(state_obj.linefont, s=1)

            if ntype == "term" or ntype == "link":
                if state_obj.linecolor and not state_obj.linecolor[0][0] == 0:
                    SkipPositive(state_obj.linecolor, s=1)
                if state_obj.linefsize and not state_obj.linefsize[0][0] == 0:
                    SkipPositive(state_obj.linefsize, s=1)
                if state_obj.linefstyle and not state_obj.linefstyle[0][0] == 0:
                    SkipPositive(state_obj.linefstyle, s=1)
                if state_obj.linefont and not state_obj.linefont[0][0] == 0:
                    SkipPositive(state_obj.linefont, s=1)

            edgeattrs = state_obj.edgeattrs()
            AppendNodeEdge(edge, tabs, fromnode, tonode, ntype, edgeattrs, edgetype)

            parentlist[level] = tree.addchild_rev(
                tonode,
                tabs,
                ntype,
                labelhtml,
                parentlist[level - 1],
                state_obj.wordcolor,
                state_obj.linecolor,
                state_obj.wordfsize,
                state_obj.linefsize,
                state_obj.wordfstyle,
                state_obj.linefstyle,
                state_obj.linefont,
                state_obj.linedate,
                state_obj.sgcolor_value(),
                state_obj.sgtitle_value(),
                state_obj.sgstyle_value(),
                vrbt,
                draw,
                textleft,
                state_obj.fontname,
                state_obj.bgcolor,
                state_obj.fgcolor,
                state_obj.child_subgraphs,
                state_obj.sgmargin,
                state_obj.bordercolor,
                state_obj.borderwidth,
                state_obj.borderstyle,
                hr_style=state_obj.hr_style,
                wordfont=state_obj.wordfont,
            )
            if code_image_path:
                InsertImageRow(parentlist[level]._label, code_image_path)
            if markdown_body is not None:
                node = parentlist[level]
                attrs = node._apply_node_overrides(nodetype[ntype])
                body_label = RenderMarkdown(
                    markdown_body, tmpdir, markdown_width,
                    face=state_obj.fontname or ParseInlineAttrLine('fontname', attrs),
                    foreground=state_obj.fgcolor or ParseInlineAttrLine('fontcolor', attrs),
                    size=next((entry[1] for entry in state_obj.linefsize if entry[0] == 0),
                              ParseInlineAttrLine('fontsize', attrs) or fontsize['m']),
                    code_theme=root_code_theme,
                )
                node._label = [AppendMarkdownLabel(''.join(node._label), body_label)]

            nodelevel[level - 1] += 1
            for index in range(level, len(nodelevel) - 1):
                nodelevel[index] = 1

    dotbuf += EmitTreeNodes(tree, nodetype, fontsize)
    dotbuf += "\n\n"
    dotbuf += "".join(FinalizeEdges(edge, arrlines, arrend, tree.subgraph_depth))
    dotbuf += "\t}\n}"

    if argholder.dotname and argholder.dotname == "specified":
        argholder.dotname = dotname
    if not argholder.jpgname:
        argholder.jpgname = jpgname

    if argholder.dotname:
        WriteDot(dotbuf, argholder.dotname)
    else:
        result = WriteImg(dotbuf, argholder, session.gvroot, title, notitle, tmpdir)
        dotbuf = result["dotbuf"]
        tmpdir = result["tmpdir"]
        notitle = result["notitle"]
        session.gvroot = result["gvroot"]

    session.dotbuf = dotbuf
    session.title = title
    session.notitle = notitle
    session.bgcolor = bgcolor
    session.tmpdir = tmpdir
    return session
