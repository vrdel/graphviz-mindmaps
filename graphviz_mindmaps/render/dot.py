import base64
import re
import subprocess
import tempfile

from graphviz_mindmaps.fontawesome import FONT_DIR
from graphviz_mindmaps.render.code_image import RenderCodeImage
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
    IMAGE_NODE_TRANSFORMS,
    RenderTransformedImage,
    ResolveBaseNodeTypeToken,
    ResolveColorNodeTypeToken,
    ResolveSymbolNames,
    ResolveVerbatimFillColorToken,
)
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
    return "1.2"


def IsOutlineLeaf(lines, index, level, tabnum):
    for candidate in lines[index + 1:]:
        if not re.search(r"(\t#) (.*)", candidate):
            continue
        next_level = candidate[:candidate.find("#")].count("\t") - tabnum
        return next_level <= level
    return True


def GenDot(lines, argholder, session: RenderSession, runtime: RenderRuntime):
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
        if image_key in IMAGE_NODE_TRANSFORMS:
            return RenderTransformedImage(
                image,
                image_key,
                GenImgPath,
                tmpdir,
                tempfile,
                subprocess,
            )
        return GenImgPath(image)

    jpgname, dotname = "", ""

    tabnum = lines[0].count("\t")

    match = re.search(r"(\t|#) (.*)", lines[0])
    title = match.group(2)

    bgcolor = runtime.default_bgcolor
    penwidth = ResolveRootPenwidth(lines)
    for line in lines[1:]:
        if re.search(r"\t(:|\|)\s*fname", line):
            custom_bg = ParseInlineAttrLine("bgcolor", line)
            if custom_bg:
                bgcolor = custom_bg
            break

    dotbuf += "digraph G {\n\n\tnodesep=\"0.1\";\n\tnewrank=\"true\";\n\tcompound=\"false\";\n\tsplines=\"true\";\n\tordering=out;\n\trankdir=LR;\n\tranksep=0.1;\n\tfontpath=\"%s\";\n\tbgcolor=\"%s\";\n\n\tnode[fontname=\"%s\" fontsize=%s fontcolor=\"%s\" color=\"#000000\" gradientangle=\"90\" penwidth=%s];\n" % (FONT_DIR, bgcolor, font["comic"], fontsize["m"], fontcolor["def"], penwidth)
    dotbuf += "\tedge[arrowhead=none color=\"#8a8a8a\" minlen=3 style=tapered penwidth=6 dir=forward arrowtail=none fontname=\"%s\" fontsize=\"%s\" fontcolor=\"%s\"];\n\n" % (font["comicb"], fontsize["l"], fontcolor["b"])
    dotbuf += "// %s\n" % (match.group(2))
    dotbuf += "\tsubgraph cluster000 {\n\n"
    dotbuf += "\t\tstyle=radial;\n\t\tordering=out;\n\t\tfillcolor=\"%s\";\n\t\tcolor=\"%s\";\n\n" % (bgcolor, bgcolor)
    dotbuf += "\t\t%s[%s label=<<TABLE CELLBORDER=\"0\" CELLSPACING=\"0\" BORDER=\"0\"><TR><TD>%s</TD></TR></TABLE>>];\n" % (rootnodename, nodetype["root"], match.group(2).replace(";", "<BR/>"))

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

        if lines.index(line) < len(lines) - 1:
            nextline = lines[lines.index(line) + 1]
        else:
            nextline = lines[lines.index(line)]

        if re.search(r"(\t#) (.*)", line):
            level = line[:line.find("#")].count("\t") - tabnum

            match = re.search(r"(\t|#) (.*)", line)
            label = match.group(2)
            code_match = re.search(r"<CODEBLOCK lang=\"([^\"]+)\"(?: style=\"([^\"]+)\")? data=\"([^\"]*)\"/>", label)
            code_source = None
            code_language = None
            code_style = "default"
            code_image_path = None
            if code_match:
                code_language = code_match.group(1)
                code_style = code_match.group(2) or "default"
                code_source = base64.b64decode(code_match.group(3)).decode("utf-8")
                label = label[:code_match.start()].rstrip()

            ntype = ""
            vrbt, draw, textleft = ResolveNodeRenderFlags(nextline)

            if code_source is not None:
                if not tmpdir:
                    tmpdir.append(tempfile.mkdtemp())
                code_image_path = RenderCodeImage(code_source, code_language, tmpdir, code_style)
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

            if nextline.find("#") == -1 and state_obj.ntype != "img":
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
                if code_source is not None:
                    ntype = "node"
                elif IsOutlineLeaf(lines, line_index, level, tabnum):
                    ntype = leaf_ntype
                else:
                    ntype = "def"
                state_obj.ntype = ntype
            PreAttrProcLabel(labelhtml, ntype, ResolveBaseNodeTypeToken, runtime.fontawesome_symb, fontcolor)

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
            )
            if code_image_path:
                InsertImageRow(parentlist[level]._label, code_image_path)

            nodelevel[level - 1] += 1
            for index in range(level, len(nodelevel) - 1):
                nodelevel[index] = 1

    dotbuf += EmitTreeNodes(tree, nodetype, fontsize)
    dotbuf += "\n\n"
    dotbuf += "".join(FinalizeEdges(edge, arrlines, arrend))
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
