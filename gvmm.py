#!/home/daniel/.pyenv/versions/gvmm-py3/bin/python3

import sys, re, subprocess, argparse, os, fnmatch, fontawesome, tempfile
import socket, configparser
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
from graphviz_mindmaps.model.graph import (
    AppendNodeEdge,
    BuildNodeRefs,
    EmitTreeNodes,
    FinalizeEdges,
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


class Tree:
    class Node:
        def __init__(self, nodename, label=[], tabs="", ntype=None, parent=None, wordcolor=[], linecolor=[], wordfsize=[], linefsize=[], wordfstyle=[], linefstyle=[], linedate=[], verbatim=False, draw=False):
            self._ntype = ntype
            self._nodename = nodename
            self._label = label
            self._tabs = tabs
            self._parent = parent
            self._child = []
            self._wordcolor = wordcolor
            self._linecolor = linecolor
            self._linefsize = linefsize
            self._linefstyle = linefstyle
            self._wordfsize = wordfsize
            self._wordfstyle = wordfstyle
            self._linedate = linedate
            self._verbatim = verbatim
            self._draw = draw

        def element(self):
            if "sgwrap" in self._ntype:
                return self._tabs + "".join(self._label)
            elif self._verbatim:
                if self._ntype == "def":
                    return "\t" + self._tabs + self._nodename + "[%s label=<%s>];" % (nodetype["verbatim"], "".join(self._label))
                else:
                    fillcolor = ResolveVerbatimFillColorToken(self._ntype, vrbtcolors)
                    if not fillcolor:
                        fillcolor = vrbtcolors['def']
                    return "\t" + self._tabs + self._nodename + "[%s label=<%s>];" % (nodetype["verbatim"].replace(vrbtcolors['def'], fillcolor), "".join(self._label))
            elif self._draw:
                if self._ntype == "def":
                    return "\t" + self._tabs + self._nodename + "[%s label=<%s>];" % (nodetype["draw"], "".join(self._label))
                else:
                    fillcolor = ResolveVerbatimFillColorToken(self._ntype, vrbtcolors)
                    if not fillcolor:
                        fillcolor = vrbtcolors['cwhite']
                    return "\t" + self._tabs + self._nodename + "[%s label=<%s>];" % (nodetype["draw"].replace(vrbtcolors['cwhite'], fillcolor), "".join(self._label))
            else:
                return "\t" + self._tabs + self._nodename + "[%s label=<%s>];" % (nodetype[self._ntype], "".join(self._label))

        def parent(self):
            return self._parent

        def childs(self):
            return self._child

        def setype(self, ntype):
            self._ntype = ntype

        def getype(self):
            return self._ntype

        def numchilds(self):
            return len(self._child)

        def reverse(self):
            cursor = len(self._child) - 1
            while cursor >= 0:
                yield self._child[cursor].element()
                cursor -= 1

        def is_leaf(self):
            if self.numchilds() == 0:
                return True
            else:
                return False

        def colorifywords(self):
            if not self._draw:
                self._wordattr(self._wordcolor, "<B><FONT COLOR=", "</FONT></B>")
            else:
                self._wordattr(self._wordcolor, "<FONT COLOR=", "</FONT>")

        def wordfstyle(self):
            self._wordattr(self._wordfstyle, "<")

        def wordfsize(self):
            self._wordattr(self._wordfsize, "<FONT POINT-SIZE=", "</FONT>")

        def linefsize(self):
            self._lineattr("<TD>", "<TD><FONT POINT-SIZE=", self._linefsize, "</FONT>")

        def linefstyle(self):
            for i in self._linefstyle:
                self._lineattr("<TD>", "<TD><", [i], "</%s>" % (i[1]))

        def colorifylines(self):
            for i in self._linecolor:
                if i[2]:
                    self._lineattr("<TD>", "<TD><B><FONT COLOR=", [i], "</FONT></B>")
                else:
                    self._lineattr("<TD>", "<TD BGCOLOR=", [i])

        def linedate(self):
            if len(self._linedate) == 0:
                return

            self._label = "<SEP>".join(self._label)
            self._label = self._label.split("</TD></TR><TR>")

            for i in self._linedate:
                if self._verbatim or self._draw:
                    _, scoped_indexes = self._scoped_line_fragment_indexes(self._label)
                    if not scoped_indexes:
                        continue
                    li = self._resolve_line_sel(int(i[0]), len(scoped_indexes))
                    if li < 1 or li > len(scoped_indexes):
                        continue
                    target_idx = scoped_indexes[li - 1]
                else:
                    li = self._resolve_line_sel(int(i[0]), len(self._label))
                    if li < 1 or li > len(self._label):
                        continue
                    target_idx = li - 1

                deco = "<TD><FONT COLOR=\"%s\"><I><FONT FACE=\"FontAwesome\" POINT-SIZE=\"18\">%s</FONT>&nbsp;" % (fontcolor['b'], fontawesome.symb["calendar"])
                self._label[target_idx] = self._label[target_idx].replace("<TD>", deco, 1)
                if "</TD>" in self._label[target_idx]:
                    self._label[target_idx] = self._label[target_idx].replace("</TD>", "</I></FONT></TD>", 1)
                else:
                    self._label[target_idx] = self._label[target_idx] + "</I></FONT>"

            for j in range(len(self._label) - 1):
                self._label[j] = self._label[j] + "</TD></TR><TR>"

            self._label = "".join(self._label)
            self._label = self._label.split("<SEP>")

        def _resolve_line_sel(self, li, total_lines):
            if total_lines < 1:
                return 1
            if li < 0:
                li = total_lines + li + 1
            if li < 1:
                return 1
            if li > total_lines:
                return total_lines
            return li

        def _label_line_word_indexes(self):
            def has_visible_content(fragment):
                text = re.sub(r"<[^>]+>", "", fragment)
                text = text.replace("&nbsp;", "").strip()
                text = text.replace("<", "").replace(">", "").strip()
                return bool(text)

            lines = [[]]
            rowsep = "</TD></TR><TR><TD>"

            for idx, token in enumerate(self._label):
                if token == "&nbsp;":
                    continue

                parts = token.split(rowsep)
                if has_visible_content(parts[0]):
                    lines[-1].append(idx)

                for part in parts[1:]:
                    lines.append([])
                    if has_visible_content(part):
                        lines[-1].append(idx)

            return lines

        def _scoped_line_word_indexes(self):
            line_indexes = self._label_line_word_indexes()

            while line_indexes and not line_indexes[0]:
                del(line_indexes[0])

            if self._verbatim or self._draw:
                if line_indexes:
                    del(line_indexes[0])
                while line_indexes and not line_indexes[0]:
                    del(line_indexes[0])
                while line_indexes and not line_indexes[-1]:
                    del(line_indexes[-1])

            return line_indexes

        def _scoped_line_fragment_indexes(self, fragments=None):
            def has_visible_content(fragment):
                text = re.sub(r"<[^>]+>", "", fragment)
                text = text.replace("&nbsp;", "").strip()
                text = text.replace("<", "").replace(">", "").strip()
                return bool(text)

            if fragments is None:
                fragments = "<SEP>".join(self._label).split("</TD></TR><TR>")
            indexes = [idx for idx, fragment in enumerate(fragments) if has_visible_content(fragment)]

            if self._verbatim or self._draw:
                if indexes:
                    del(indexes[0])
                while indexes and not has_visible_content(fragments[indexes[0]]):
                    del(indexes[0])
                while indexes and not has_visible_content(fragments[indexes[-1]]):
                    indexes.pop()

            return fragments, indexes

        def _wordattr(self, value, sattr, eattr = None):
            if len(value) > 0:
                prevnbsp = [j for j in range(2, len(self._label)) if "nbsp" in self._label[j]]

                for i in self._label[2:]:
                    if "nbsp" in i:
                        self._label.remove(i)

                for i in value:
                    target_idx = int(i[0])
                    if type(i[2]) == dict and i[2]['lineskip']:
                        line_indexes = self._scoped_line_word_indexes()
                        if not line_indexes:
                            continue
                        lskip = self._resolve_line_sel(i[2]['lineskip'], len(line_indexes))
                        scoped_words = line_indexes[lskip - 1]
                        if not scoped_words:
                            continue

                        wsel = int(i[0])
                        if wsel < 0:
                            wsel = len(scoped_words) + wsel + 1
                        if wsel < 1:
                            wsel = 1
                        if wsel > len(scoped_words):
                            wsel = len(scoped_words)

                        target_idx = scoped_words[wsel - 1]

                    if target_idx < 0 or target_idx >= len(self._label):
                        continue

                    if i[1] in set(["U", "B", "S", "I"]):
                        self._label[target_idx] = sattr + "%s>" % i[1] + self._label[target_idx]
                        eattr = "</%s>" % (i[1])
                    else:
                        self._label[target_idx] = sattr + "\"%s\">" % i[1] + self._label[target_idx]

                    if "</TD></TR><TR>" in self._label[target_idx]:
                        self._label[target_idx] = self._label[target_idx].replace("</TD></TR><TR>", eattr + "</TD></TR><TR>")
                    else:
                        self._label[target_idx] = self._label[target_idx] + eattr


                for i in prevnbsp:
                    self._label.insert(i, "&nbsp;")

        def _lineattr(self, fsattr, tsattr, value, eattr = None):
            def is_separator_row(fragment):
                text = re.sub(r"<[^>]+>", "", fragment)
                text = text.replace("&nbsp;", "").strip()
                return text in set(["---", "----"])

            def replace_td(fragment, replacement):
                return re.sub(r"<TD(?: ALIGN=\"left\")?>", replacement, fragment, count=1)

            if len(value) > 0:
                if value[0][0] == 0:
                    if "FontAwesome" not in self._label[1]:
                        self._label = "<SEP>".join(self._label)
                        self._label = self._label.split("</TD></TR><TR>")
                        for i in range(len(self._label)):
                            if is_separator_row(self._label[i]):
                                continue
                            self._label[i] = replace_td(self._label[i], \
                                    "%s\"%s\">" % (tsattr, value[0][1]) \
                                    if value[0][1] not in set(['U', 'B', 'S', 'I'])\
                                    else "%s%s>" % (tsattr, value[0][1]) )
                            if eattr and i < len(self._label) - 1:
                                self._label[i] = self._label[i] + eattr
                            elif eattr and i == len(self._label) - 1:
                                self._label[i] = self._label[i].replace("</TD>", eattr + "</TD>")
                        for j in range(len(self._label) - 1):
                            self._label[j] = self._label[j] + "</TD></TR><TR>"
                        self._label = "".join(self._label)
                        self._label = self._label.split("<SEP>")
                    else:
                        first = self._label[0]
                        if eattr:
                            for i in range(2, len(self._label)):
                                self._label[i] = self._label[i].replace("</TD>", eattr + "</TD>")
                        self._label = "<SEP>".join(self._label[1:])
                        self._label = re.sub(r"<TD(?: ALIGN=\"left\")?>", \
                                "%s\"%s\">" % (tsattr, value[0][1]) \
                                if value[0][1] not in set(['U', 'B', 'S', 'I'])\
                                else "%s%s>" % (tsattr, value[0][1]), self._label)
                        self._label = self._label.split("<SEP>")
                        self._label.insert(0, first)
                else:
                    self._label = "<SEP>".join(self._label)
                    self._label = self._label.split("</TD></TR><TR>")
                    for i in value:
                        if self._verbatim or self._draw:
                            _, scoped_indexes = self._scoped_line_fragment_indexes(self._label)
                            if not scoped_indexes:
                                continue
                            li = self._resolve_line_sel(int(i[0]), len(scoped_indexes))
                            if li < 1 or li > len(scoped_indexes):
                                continue
                            target_idx = scoped_indexes[li - 1]
                        else:
                            li = self._resolve_line_sel(int(i[0]), len(self._label))
                            if li < 1 or li > len(self._label):
                                continue
                            target_idx = li - 1
                        self._label[target_idx] = \
                                replace_td(self._label[target_idx], \
                                "%s\"%s\">" % (tsattr, i[1]) if i[1] not in set(['U', 'B', 'S', 'I']) \
                                else "%s%s>" % (tsattr, i[1]))
                        if eattr and target_idx < len(self._label) - 1:
                            self._label[target_idx] = self._label[target_idx] + eattr
                        elif eattr and target_idx == len(self._label) - 1:
                            self._label[target_idx] = self._label[target_idx].replace("</TD>", eattr + "</TD>")
                    for j in range(len(self._label) - 1):
                        self._label[j] = self._label[j] + "</TD></TR><TR>"
                    self._label = "".join(self._label)
                    self._label = self._label.split("<SEP>")


    def __init__(self):
        self.root = None
        self.size = 0

    def addroot(self, e):
        self.root = self.Node(e, ntype="root")
        return self.root

    def _addchild(self, e, p):
        c = self.Node(e)
        c._parent = p
        p._child.append(c)
        return c

    def addchild(self, e, tabs, ntype, label, p):
        self._addchild(tabs + "subgraph cluster%s {" % e.replace("node", "") + tabs + "\t" + "style = invis;", p)
        c = self._addchild("\t" + tabs + e, p)
        self._addchild(tabs + "}", p)
        return c

    def _addchild_rev(self, nodename, label, tabs, ntype, p, wc=[], lc=[], ws=[], ls=[], wf=[], lf=[], ld=[], vrbt=False, draw=False):
        c = self.Node(nodename, label, tabs, ntype, p, wc, lc, ws, ls, wf, lf, ld, vrbt, draw)
        c._parent = p
        p._child.insert(0, c)
        return c

    def addchild_rev(self, nodename, tabs, ntype, label, p, wordcolor=[], linecolor=[], wordfsize=[], linefsize=[], wordfstyle=[], linefstyle=[], linedate=[], sgcolor=None, sgtitle=None, sgstyle=None, vrbt=False, draw=False, textleft=False):
        sgattr = ""
        if sgcolor and sgcolor[0] == "s":
            self._addchild_rev("", ["}"], tabs, "sgwrap", p)
        self._addchild_rev("", ["}"], tabs, "sgwrap", p)
        if sgtitle:
            self._addchild_rev("", ["label = <<TABLE CELLBORDER=\"0\" CELLPADDING=\"3\" CELLSPACING=\"3\" BORDER=\"0\"><TR><TD BGCOLOR=\"#E9ED5F\" COLOR=\"#000000\"><U>%s</U></TD></TR></TABLE>>" % (sgtitle)], tabs, "sgwrap", p)
        c = self._addchild_rev(nodename, label, tabs, ntype, p, wordcolor, linecolor, wordfsize, linefsize, wordfstyle, linefstyle, linedate, vrbt, draw)
        c.wordfsize()
        c.wordfstyle()
        c.linefsize()
        c.colorifywords()
        c.linefstyle()
        c.colorifylines()
        c.linedate()

        PostAttrProcLabel(c._label, ntype, vrbt, draw, textleft)

        if sgcolor and sgcolor[0] == "#":
            sgattr = "style = \"%s rounded\";\n" % (sgstyle + "," if sgstyle else "") + tabs + "\t" + "color = \"%s\";\n" % (sgcolor if not sgstyle else "#000000") + tabs + "\t" + "bgcolor = \"%s\"" % (sgcolor)
        else:
            sgattr = "style = invis;"

        if sgtitle:
            self._addchild_rev("", ["fontname = \"%s\";\n" % (font['balsamiq']) + tabs + "\t" + "fontsize = \"%s\";\n" % (fontsize['xxl'])], tabs, "sgwrap", p)
        self._addchild_rev("", ["subgraph cluster%s {\n" % nodename.replace("node", "") + tabs + "\t" + sgattr], tabs, "sgwrap", p)
        if sgcolor and sgcolor[0] == "e":
            sgattr = "style = \"%s rounded\";\n" % (sgstyle + "," if sgstyle else "") + tabs + "\t" + "color = \"%s\";\n" % (sgcolor[1:] if not sgstyle else "#000000") + tabs + "\t" + "bgcolor = \"%s\";" % (sgcolor[1:])
            self._addchild_rev("", ["subgraph cluster%s {\n" % nodename.replace("node", "colored") + tabs + "\t" + sgattr], tabs, "sgwrap", p)

        return c

    def preorder(self):
        for p in self._subtree_preorder(self.root):
            yield p

    def _subtree_preorder(self, p):
        yield p
        for c in p.childs():
            if c.is_leaf():
                yield c
            else:
                for other in self._subtree_preorder(c):
                    yield other

    def postorder(self):
        for p in self._subtree_postorder(self.root):
            yield p

    def _subtree_postorder(self, p):
        for c in p.childs():
            if c.is_leaf():
                yield c
            else:
                for other in self._subtree_postorder(c):
                    yield other
        yield p

class ArgHolder(object):
    pass

def WriteDot(DotFile):
    outputfile = open(DotFile, 'w')
    outputfile.write(dotbuf)
    outputfile.close()


def SendRestartMSG(sockwildcard, sockcfg=None):
    config = configparser.ConfigParser()
    config.read(cfg)

    sockp = config.defaults().get(sockcfg)

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(sockp)
    except socket.error as m:
        print(sockcfg)
        print(m)
    else:
        sock.send(("%s restart" % (sockwildcard[0])).encode(), 64)
        sock.close()


def ScaleImg(argholder):
    cmd = "gm convert -scale %s%% '%s' '%s'" % (argholder.scale, gvroot + argholder.jpgname, gvroot + argholder.jpgname)
    subprocess.call(cmd, shell=True)


def WriteImg(argholder):
    global gvroot
    global dotbuf
    global tmpdir
    global notitle

    if argholder.jpgname.startswith("~") or argholder.jpgname.startswith("/"):
        gvroot = ""
        argholder.jpgname = argholder.jpgname.replace("~", os.environ['HOME'])
    elif "/" not in argholder.jpgname and "~" not in argholder.jpgname:
        gvroot = os.environ['PWD'] + "/"
    proc = subprocess.Popen(['dot', '-Tjpg', '-o', gvroot + argholder.jpgname], stdin = subprocess.PIPE)
    proc.communicate(dotbuf.encode())

    subprocess.call("gm convert -shave 2x2 '%s' '%s'" % (gvroot + argholder.jpgname, gvroot + argholder.jpgname), shell=True)

    if not notitle:
        subprocess.call("montit.py -s s -t '%s' '%s'" % (title, gvroot + argholder.jpgname), shell=True)

    if argholder.scale:
        ScaleImg(argholder)

    if argholder.preview:
        # subprocess.Popen(['feh','-g', '1600x900', gvroot + argholder.jpgname])
        subprocess.call("FvwmCommand 'All (galapix:*%s*) Close'" % \
                argholder.jpgname.split("/")[1] if "/" in argholder.jpgname else argholder.jpgname, shell=True)
        subprocess.Popen(['galaview.sh', gvroot + argholder.jpgname])

    if len(tmpdir) > 0:
        for t in tmpdir:
            os.remove("%s/doodle.png" % (t))
            os.removedirs(t)
            tmpdir = []

    dotbuf = ""
    notitle = False
    if not argholder.mtg:
        argholder.jpgname = None


def CheckCM(img):
    cmfile = None

    # FIX
    # returns only one file with a match
    # mindmap could be in several .cm files
    for fil in os.listdir('.'):
        if fnmatch.fnmatch(fil, '*.cm'):
            fo = open(fil)
            lines = fo.readlines()
            for line in lines:
                if img in line:
                    cmfile = fil
            fo.close()
    return cmfile


def WriteMontage(argholder):
    imgarg = []
    cmfile = ""
    global gvroot
    global montagetitle

    imgarg = argholder.jpgname.split("/")
    if argholder.jpgname.startswith("gv/"):
        os.chdir(gvroot + '/'.join(imgarg[0:2]))
        cmfile = CheckCM(imgarg[2])
    else:
        print("montage building should be in %s/gv/" % (gvroot[0:-1]))
        raise SystemExit(1)


    if cmfile:
        subprocess.call(["montage.py", cmfile])
        SendRestartMSG("rsync call", "inotsock")
    else:
        print("%s not found in any %s/*.cm" % (imgarg[2], gvroot + '/'.join(imgarg[0:2])))
        raise SystemExit(1)


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
    tree = Tree()
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
