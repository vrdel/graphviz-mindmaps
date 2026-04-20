#!/home/daniel/.pyenv/versions/gvmm-py3/bin/python3

import sys, re, subprocess, argparse, os, fontawesome, tempfile
from graphviz_mindmaps.constants import (
    DEFAULT_BGCOLOR,
    MAXDEPTH,
    arrcolors,
    edgecolors,
    edgeends,
    edgestyles,
    edgetype,
    font,
    fontcolor,
    fontsize,
    fontstyle,
    html_larrow1,
    html_larrow2,
    html_rarrow1,
    html_rarrow2,
    linecolors,
    nodetype,
    subgraphcolors,
    vrbtcolors,
)
from graphviz_mindmaps.execute.image import (
    ScaleImg as PackageScaleImg,
    WriteDot as PackageWriteDot,
    WriteImg as PackageWriteImg,
)
from graphviz_mindmaps.execute.montage import (
    CheckCM as PackageCheckCM,
    WriteMontage as PackageWriteMontage,
)
from graphviz_mindmaps.execute.restart import SendRestartMSG as PackageSendRestartMSG
from graphviz_mindmaps.model.graph import (
    AppendNodeEdge,
    BuildNodeRefs,
    EmitTreeNodes,
    FinalizeEdges,
    Tree,
)
from graphviz_mindmaps.model.styles import NodePrepState
from graphviz_mindmaps.parser.attributes import (
    ApplyNodeAttributeTokens,
    ParseAttributeLine,
    ResolveBaseNodeTypeToken,
    ResolveColorNodeTypeToken,
    ResolveSymbolNames,
    ResolveVerbatimFillColorToken,
)
from graphviz_mindmaps.parser.outline import (
    ExtractMindmapBlocks,
    GenImgPath,
    ParseFnameLine as ParseFnameLineDetails,
    ParseInlineAttrLine,
    ParseOtlname,
    ResolveNodeRenderFlags,
    TokenizeNodeAttributeLine,
)
from graphviz_mindmaps.render.label_html import (
    ApplyInlineBacktickBold,
    BuildNodeLabelHtml,
    InsertSymbolRows,
    PostAttrProcLabel,
    PreAttrProcLabel,
)

gvroot = "/home/daniel/my_notes/"
dotbuf = ""
tmpdir = []
title = ""
montagetitle = None
notitle = False
bgcolor = DEFAULT_BGCOLOR

cfg = os.environ['HOME'] + "/.galapix/galapix.cfg"

class ArgHolder(object):
    pass

def WriteDot(DotFile):
    PackageWriteDot(dotbuf, DotFile)


def SendRestartMSG(sockwildcard, sockcfg=None):
    PackageSendRestartMSG(cfg, sockwildcard, sockcfg)


def ScaleImg(argholder):
    PackageScaleImg(argholder, gvroot)


def WriteImg(argholder):
    global gvroot
    global dotbuf
    global tmpdir
    global notitle
    result = PackageWriteImg(dotbuf, argholder, gvroot, title, notitle, tmpdir)
    gvroot = result["gvroot"]
    dotbuf = result["dotbuf"]
    tmpdir = result["tmpdir"]
    notitle = result["notitle"]


def CheckCM(img):
    return PackageCheckCM(img)


def WriteMontage(argholder):
    global gvroot
    global montagetitle
    PackageWriteMontage(argholder, gvroot, SendRestartMSG)


def Skip(maplist, s=None, lsinw=None):
    if maplist:
        seen_lmeta = set()
        j = 0
        while j < len(maplist):
            if lsinw and len(maplist[j]) > 2 and type(maplist[j][2]) == dict:
                lmeta = maplist[j][2]
                lmeta_id = id(lmeta)
                if lmeta_id not in seen_lmeta and lmeta.get('lineskip') is not None:
                    lmeta['lineskip'] += lsinw
                    seen_lmeta.add(lmeta_id)
            if s:
                maplist[j][0] += s
            j += 1

def SkipPositive(maplist, s):
    if not maplist or not s:
        return
    j = 0
    while j < len(maplist):
        if maplist[j][0] > 0:
            maplist[j][0] += s
        j += 1

def SkipUnscopedWords(maplist, s):
    if not maplist or not s:
        return

    j = 0
    while j < len(maplist):
        lmeta = maplist[j][2] if len(maplist[j]) > 2 else None
        if not (type(lmeta) == dict and lmeta.get('lineskip') is not None):
            maplist[j][0] += s
        j += 1

def SkipPositiveLineScopedWords(maplist, lsinw):
    if not maplist or not lsinw:
        return

    seen_lmeta = set()
    j = 0
    while j < len(maplist):
        lmeta = maplist[j][2] if len(maplist[j]) > 2 else None
        if type(lmeta) == dict and lmeta.get('lineskip') is not None:
            lmeta_id = id(lmeta)
            if lmeta_id not in seen_lmeta and lmeta['lineskip'] > 0:
                lmeta['lineskip'] += lsinw
                seen_lmeta.add(lmeta_id)
        j += 1


def ParseFnameLine(keyword, line):
    global notitle
    fname, should_hide_title = ParseFnameLineDetails(keyword, line)
    if should_hide_title:
        notitle = True
    return fname

def GenDot(lines, argholder, parser):
    tree = Tree(
        nodetype,
        vrbtcolors,
        fontcolor,
        font,
        fontsize,
        fontawesome.symb,
        ResolveVerbatimFillColorToken,
        PostAttrProcLabel,
    )
    parentlist = [None] * MAXDEPTH

    rootnodename = "node1"
    root = tree.addroot(rootnodename)
    parentlist[0] = root

    global dotbuf, title, notitle, montagetitle, bgcolor
    jpgname, dotname = "", ""

    tabnum = lines[0].count("\t")

    m = re.search(r'(\t|#) (.*)', lines[0])
    title = m.group(2)

    # bgcolor can be specified on the same line as fname. Reset per map.
    bgcolor = DEFAULT_BGCOLOR
    for line in lines[1:]:
        if re.search(r"\t(:|\|)\s*fname", line):
            custom_bg = ParseInlineAttrLine("bgcolor", line)
            if custom_bg:
                bgcolor = custom_bg
            break

    dotbuf += "digraph G {\n\n\tnodesep=\"0.1\";\n\tnewrank=\"true\";\n\tcompound=\"false\";\n\tsplines=\"true\";\n\tordering=out;\n\trankdir=LR;\n\tranksep=0.1;\n\tbgcolor=\"%s\";\n\n\tnode[fontname=\"%s\" fontsize=%s fontcolor=\"%s\" color=\"#000000\" gradientangle=\"90\" penwidth=2.5];\n" % (bgcolor, font['comic'], fontsize['m'], fontcolor['def'])
    dotbuf += "\tedge[arrowhead=none color=\"#8a8a8a\" minlen=3 style=tapered penwidth=6 dir=forward arrowtail=none fontname=\"%s\" fontsize=\"%s\" fontcolor=\"%s\"];\n\n" % (font['comicb'], fontsize['l'], fontcolor['b'])
    dotbuf += "// %s\n" % (m.group(2))
    dotbuf += "\tsubgraph cluster000 {\n\n"
    dotbuf += "\t\tstyle=radial;\n\t\tordering=out;\n\t\tfillcolor=\"%s\";\n\t\tcolor=\"%s\";\n\n" % (bgcolor, bgcolor)
    dotbuf += "\t\t%s[%s label=<<TABLE CELLBORDER=\"0\" CELLSPACING=\"0\" BORDER=\"0\"><TR><TD>%s</TD></TR></TABLE>>];\n" % (rootnodename, nodetype['root'], m.group(2).replace(";", "<BR/>"))

    dotname = "%s.dot" % (m.group(2))
    jpgname = "%s.jpg" % (m.group(2))

    edge, arrlines, labelhtml, doodlist = [], [], [], []
    arrend = {}
    nodelevel = [1] * MAXDEPTH
    numdood = 0


    for line in lines[1:]:
        if re.search(r"\t(:|\|)\s*fname", line):
            jpgname = ParseFnameLine("fname", line)
            jpgname = jpgname.strip()

            if re.search("otlname", line):
                title = ParseOtlname("otlname", line) + '  -  ' + title

        if lines.index(line) < len(lines) - 1:
            nextline = lines[lines.index(line) + 1]
        else:
            nextline = lines[lines.index(line)]

        if re.search(r"(\t#) (.*)", line):
            level = line[:line.find("#")].count("\t") - tabnum

            m = re.search(r'(\t|#) (.*)', line)
            label = m.group(2)

            ntype = ""
            vrbt, draw, textleft = ResolveNodeRenderFlags(nextline)

            try:
                labelhtml, ntype, label = BuildNodeLabelHtml(
                    label,
                    vrbt,
                    draw,
                    html_larrow1,
                    html_rarrow1,
                    html_larrow2,
                    html_rarrow2,
                    GenImgPath,
                )
            except (IndexError, KeyError) as e:
                print(e, label)

            state = NodePrepState(ntype=ntype)

            fromnode, tonode, tabs = BuildNodeRefs(rootnodename, nodelevel, level)

            if nextline.find("#") == -1 and state.ntype != "img":
                nextline = TokenizeNodeAttributeLine(nextline)
                numdood += ApplyNodeAttributeTokens(
                    nextline,
                    tonode,
                    state,
                    labelhtml,
                    arrlines,
                    arrend,
                    lambda token: ResolveColorNodeTypeToken(token, nodetype),
                    ResolveSymbolNames,
                    GenImgPath,
                    fontawesome.symb,
                    tmpdir,
                    tempfile,
                    subprocess,
                    bgcolor,
                )

            InsertSymbolRows(labelhtml, state.symblist, state.symbcolor, state.symbsize, fontawesome.symb, fontcolor)

            ntype = state.ntype
            PreAttrProcLabel(labelhtml, ntype, ResolveBaseNodeTypeToken, fontawesome.symb, fontcolor)

            if vrbt or draw:
                wordskip = len(line.split("<BR/>", 1)[0].split()) - 1
                SkipUnscopedWords(state.wordfsize, s=wordskip)
                SkipUnscopedWords(state.wordcolor, s=wordskip)
                SkipUnscopedWords(state.wordfstyle, s=wordskip)

            if state.symblist:
                SkipUnscopedWords(state.wordfsize, s=len(state.symblist))
                SkipUnscopedWords(state.wordcolor, s=len(state.symblist))
                SkipUnscopedWords(state.wordfstyle, s=len(state.symblist))

            if ntype == "term" or ntype == "link":
                SkipUnscopedWords(state.wordfsize, s=2)
                SkipUnscopedWords(state.wordcolor, s=2)
                SkipUnscopedWords(state.wordfstyle, s=2)

            if ntype in set(["title", "quest", "date", "impor", "impog", "impob"]) or\
                    (ntype != "img" and "FontAwesome" in labelhtml[1]):
                if state.wordcolor: SkipPositiveLineScopedWords(state.wordcolor, lsinw=1)
                if state.wordfsize: SkipPositiveLineScopedWords(state.wordfsize, lsinw=1)
                if state.wordfstyle: SkipPositiveLineScopedWords(state.wordfstyle, lsinw=1)
                if state.linedate: SkipPositive(state.linedate, s=1)
                if state.linecolor and not state.linecolor[0][0] == 0:
                    SkipPositive(state.linecolor, s=1)
                if state.linefsize and not state.linefsize[0][0] == 0:
                    SkipPositive(state.linefsize, s=1)
                if state.linefstyle and not state.linefstyle[0][0] == 0:
                    SkipPositive(state.linefstyle, s=1)

            if ntype == "term" or ntype == "link":
                if state.linecolor and not state.linecolor[0][0] == 0:
                    SkipPositive(state.linecolor, s=1)
                if state.linefsize and not state.linefsize[0][0] == 0:
                    SkipPositive(state.linefsize, s=1)
                if state.linefstyle and not state.linefstyle[0][0] == 0:
                    SkipPositive(state.linefstyle, s=1)

            if not ntype:
                ntype = "def"

            edgeattrs = state.edgeattrs()
            AppendNodeEdge(edge, tabs, fromnode, tonode, ntype, edgeattrs, edgetype)

            parentlist[level] = tree.addchild_rev(tonode, tabs, ntype, labelhtml,\
                    parentlist[level - 1], state.wordcolor, state.linecolor, state.wordfsize, \
                    state.linefsize, state.wordfstyle, state.linefstyle, state.linedate, \
                    state.sgcolor_value(), \
                    state.sgtitle_value(), \
                    state.sgstyle_value(), \
                    vrbt, draw, textleft)

            nodelevel[level - 1] += 1

            for i in range(level, len(nodelevel) - 1):
                nodelevel[i] = 1

    dotbuf += EmitTreeNodes(tree, nodetype, fontsize)

    dotbuf += "\n\n"

    dotbuf += "".join(FinalizeEdges(edge, arrlines, arrend))

    dotbuf += "\t}\n}"

    if argholder.dotname and argholder.dotname == "specified":
        argholder.dotname = dotname

    if not argholder.jpgname:
        argholder.jpgname = jpgname

    if argholder.dotname:
        WriteDot(argholder.dotname)

    elif argholder.jpgname and argholder.mtg:
        argholder.jpgname = argholder.jpgname.strip()
        WriteImg(argholder)
        WriteMontage(argholder)

        if argholder.sock:
            SendRestartMSG(argholder.sock, "pixsock")

    elif argholder.sock:
        SendRestartMSG(argholder.sock, "pixsock")

    else:
        WriteImg(argholder)


def main():
    argholder = ArgHolder()

    linesall = []

    parser = argparse.ArgumentParser()
    parser.add_argument('-r', dest='sock', nargs='+')
    parser.add_argument('-f', dest='files', nargs='+', help='mindmap outliner files')
    parser.add_argument('-m', '--mtg', action='store_true', help='build montage with montage.py')
    parser.add_argument('-p', dest='preview', action='store_true', help='preview with galaview.sh')
    parser.add_argument('-s', dest='scale', nargs='?', const="specified", help='scale image for specified percentage')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', dest='dotname', nargs='?', const="specified", help='generate .dot file instead of image')
    group.add_argument('-i', dest='jpgname', nargs='?', const="specified", help='override image filename')
    parser.parse_args(namespace=argholder)

    if argholder.files:
        for fil in argholder.files:
            fo = open(fil)
            for line in fo:
                linesall.append(line.rstrip())
    else:
        linesall = sys.stdin.read().splitlines()

    for linesbymm in ExtractMindmapBlocks(linesall, ApplyInlineBacktickBold):
        GenDot(linesbymm, argholder, parser)

main()
