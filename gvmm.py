#!/usr/bin/python

import sys, re, subprocess, argparse, os, fnmatch, fontawesome, tempfile
import socket, ConfigParser, math


MAXDEPTH = 32
gvroot = "/home/daniel/my_notes/"
dotbuf = ""
tmpdir = []
title = ""
montagetitle = None
notitle = False

fontcolor = {"def" : "#000000", "r" : "#B30000", "g" : "#027b10", "b" : "#151e94", "y" : "#ebec50", "c" : "#00948c", "p" : "#94008b", "k" : "#000000"}
linecolors = {"r" : "#FF8080", "g" : "#8BFF80", "b" : "#80CAFF", "y" : "#FFF180", "c" : "#80FFFB", "p" : "#FF80E7"}
subgraphcolors = {"r" : "#FF000016", "g" : "#00FF0016", "b" : "#0000FF16", "y" : "#FFF40016", "c" : "#00FFD416", "p" : "#FF00EA16", "w" : "#FFFFFFFF", "k" : "#00000016", "t" : ""}
vrbtcolors = {"cgreen" : "#dffde6", "cred" : "#fde0df", "cblue" : "#e1dffd", "ccyan" : "#dffdfa", "cyello" : "#fcfddf", "corang" : "#fdecdf", "cpink" : "#fddff3", "cwhite": "#ffffff", "def" : "#dfeafd"}
fontstyle = {"ul" : "U", "ld" : "B", "st" : "S", "it" : "I"}
bgcolor = "#efefef"
font = {"comic" : "Comic Sans MS", "mono" : "Dejavu Sans Mono", "comicb" : "Comic Sans MS Bold", "balsamiq" : "Balsamiq Sans", "balsamiqb" : "Balsamiq Sans Bold"}
fontsize = {"s" : "12", "m" : 14, "l" : "16", "xl" : "20", "xxl" : "24"}
nodetype = {"root" : "fontsize=\"%s\" margin=\"0.5\" shape=cds style=radial color=\"#000000\" fillcolor=\"#dfdfdf\" gradientangle=\"90\"" % (fontsize['xxl']),
        "quest" : "shape=oval fontname=\"%s\" fontsize=\"%s\" margin=\"0.1\" style=\"radial\" fillcolor=\"#fffbab\" color=\"#8a8a8a\"" % (font['comic'], fontsize['l']),
        "impor" : "shape=signature fontsize=\"%s\" margin=\"0.25\" style=\"radial\" fillcolor=\"#ffb6c1\" color=\"#8a8a8a\"" % (fontsize['l']),
        "impog" : "shape=signature fontsize=\"%s\" margin=\"0.25\" style=\"radial\" fillcolor=\"#b6ffb7\" color=\"#8a8a8a\"" % (fontsize['l']),
        "impob" : "shape=signature fontsize=\"%s\" margin=\"0.25\" style=\"radial\" fillcolor=\"#b6e4ff\" color=\"#8a8a8a\"" % (fontsize['l']),
        "img" : "shape=box style=\"radial\" fillcolor=\"#fbfbfb\" color=\"#8a8a8a\"",
        "imgil" : "shape=box style=\"radial\" fillcolor=\"#fbfbfb\" color=\"#8a8a8a\"",
        "dood" : "shape=underline fontcolor=\"%s\" color=\"#b8b8b8\"" % (fontcolor['def']),
        "def" : "shape=underline fontcolor=\"%s\" color=\"#b8b8b8\"" % (fontcolor['def']),
        "underl" : "color=\"#b8b8b8\" fontcolor=\"%s\" shape=underline " % (fontcolor['def']),
        "node" : "shape=box style=\"rounded,radial\" fontsize=\"%s\" fillcolor=\"#f4f4f4\" color=\"#6a6a6a\"" % (fontsize['l']),
        "title" : "shape=doubleoctagon fontname=\"%s\" fontsize=\"%s\" style=\"radial\" fillcolor=\"#abffff\" color=\"#8a8a8a\"" % (font['comicb'], fontsize['l']),
        "date" : "shape=component gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15,0.15\" fillcolor=\"#fbfbfb;0.93:#B30E0E\" color=\"#8a8a8a\"",
        "example" : "shape=note fontname=\"%s\" gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15\" fillcolor=\"#18A828;0.15:#fbfbfb\" color=\"#8a8a8a\"" % (font['mono']),
        "draw" : "shape=component fontname=\"%s\" style=\"radial\" margin=\"0.15,0.15\" fillcolor=\"%s\" color=\"#8a8a8a\"" % (font['mono'], vrbtcolors['cwhite']),
        "verbatim" : "shape=component fontname=\"%s\" style=\"radial\" margin=\"0.15,0.15\" fillcolor=\"%s\" color=\"#8a8a8a\"" % (font['mono'], vrbtcolors['def']),
        "commen" : "shape=oval fontname=\"%s\" fontsize=\"%s\" margin=\"0.1\" style=\"radial\" fillcolor=\"%s\" color=\"#8a8a8a\"" % (font['comic'], fontsize['l'], vrbtcolors['def']),
        "term" : "shape=note fontname=\"%s\" gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15\" fillcolor=\"#fbfbfb\" color=\"#8a8a8a\"" % (font['mono']),
        "cgreen" : "shape=box style=\"rounded,radial\" fillcolor=\"#bcffc2\" color=\"#8a8a8a\"",
        "ccyan" : "shape=box style=\"rounded,radial\" fillcolor=\"#b9ffff\" color=\"#8a8a8a\"",
        "cblue" : "shape=box style=\"rounded,radial\" fillcolor=\"#b2d5fb\" color=\"#8a8a8a\"",
        "cpink" : "shape=box style=\"rounded,radial\" fillcolor=\"#ffb8fe\" color=\"#8a8a8a\"",
        "cred" : "shape=box style=\"rounded,radial\" fillcolor=\"#fbc1bf\" color=\"#8a8a8a\"",
        "cyello" : "shape=box style=\"rounded,radial\" fillcolor=\"#fefb88\" color=\"#8a8a8a\"",
        "corang" : "shape=box style=\"rounded,radial\" fillcolor=\"#ffc990\" color=\"#8a8a8a\""}
edgetype = {"impor" : "style=\"bold\" color=\"#AD5459\"", "impog" : "style=\"bold\" color=\"#64AD54\"",
        "impob" : "style=\"bold\" color=\"#547EAD\"", "cred" : "color=\"#AD3E39\"", "cgreen" : "color=\"#45A135\"",
        "cblue" : "color=\"#395BAD\"", "ccyan" : "color=\"#39ACAD\"", "cyello": "color=\"#A6A037\"",
        "cpink" : "color=\"#A837A0\"", "corang" : "color=\"#AD7339\""}
edgecolors = {"r" : "color=\"#AD3E39\"", "g" : "color=\"#45A135\"", "b" : "color=\"#395BAD\"", \
        "c" : "color=\"#39ACAD\"", "y": "color=\"#A6A037\"", "p" : "color=\"#A837A0\""}
edgestyles = {"s" : "solid", "d" : "dashed", "t" : "dotted", "l" : "bold"}
edgeends = {"a" : "empty", "m" : "odiamond", "o" : "odot", "v" : "open", "x" : "obox"}
arrcolors =  {"d" : "#5a5a5a", "r" : "#AD3E39", "g" : "#45A135", "b" : "#395BAD", "y" : "#A6A037", "c" : "#39ACAD", "p" : "#A837A0"}
html_rarrow1 = "<FONT FACE=\"FontAwesome\" POINT-SIZE=\"13\" COLOR=\"#6E1B31\">&#xf061;</FONT>"
html_larrow1 = "<FONT FACE=\"FontAwesome\" POINT-SIZE=\"13\" COLOR=\"#6E1B31\">&#xf060;</FONT>"
html_larrow2 = "<FONT FACE=\"FontAwesome\" POINT-SIZE=\"13\" COLOR=\"#6E1B31\">&#xf04a;</FONT>"
html_rarrow2 = "<FONT FACE=\"FontAwesome\" POINT-SIZE=\"13\" COLOR=\"#6E1B31\">&#xf04e;</FONT>"
html_equal = "<FONT POINT-SIZE=\"14\" COLOR=\"#155416\">&#9552;</FONT>"

cfg = os.environ['HOME'] + "/.galapix/galapix.cfg"


class Tree:
    class Node:
        def __init__(self, nodename, label=[], tabs="", ntype=None, parent=None, wordcolor=[], linecolor=[], wordfsize=[], linefsize=[], wordfstyle=[], linefstyle=[], verbatim=False, draw=False):
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
            self._verbatim = verbatim
            self._draw = draw

        def element(self):
            if "sgwrap" in self._ntype:
                return self._tabs + "".join(self._label)
            elif self._verbatim:
                if self._ntype == "def":
                    return "\t" + self._tabs + self._nodename + "[%s label=<%s>];" % (nodetype["verbatim"], "".join(self._label))
                else:
                    return "\t" + self._tabs + self._nodename + "[%s label=<%s>];" % (nodetype["verbatim"].replace(vrbtcolors['def'], vrbtcolors[self._ntype]), "".join(self._label))
            elif self._draw:
                if self._ntype == "def":
                    return "\t" + self._tabs + self._nodename + "[%s label=<%s>];" % (nodetype["draw"], "".join(self._label))
                else:
                    return "\t" + self._tabs + self._nodename + "[%s label=<%s>];" % (nodetype["draw"].replace(vrbtcolors['cwhite'], vrbtcolors[self._ntype]), "".join(self._label))
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

        def _wordattr(self, value, sattr, eattr = None):
            if len(value) > 0:
                prevnbsp = [j for j in range(2, len(self._label)) if "nbsp" in self._label[j]]

                for i in self._label[2:]:
                    if "nbsp" in i:
                        self._label.remove(i)

                for i in value:
                    if type(i[2]) == dict and i[2]['lineskip']:
                        wordskip = 0
                        ls, fl = 0, 0
                        if self._verbatim or self._draw:
                            for li in self._label:
                                if "</TD></TR><TR><TD>" not in li:
                                    fl += 1
                                else:
                                    break
                        while ls < i[2]['lineskip'] - 1:
                            while fl < len(self._label):
                                wordskip += 1
                                fl += 1
                                if "</TD></TR><TR><TD>" in self._label[fl]:
                                    break
                            ls += 1
                        if (self._verbatim or self._draw) and fl == len(self._label) - 1:
                            wordskip += 1
                        i[0] += wordskip

                    if i[1] in set(["U", "B", "S", "I"]):
                        self._label[int(i[0])] = sattr + "%s>" % i[1] + self._label[int(i[0])]
                        eattr = "</%s>" % (i[1])
                    else:
                        self._label[int(i[0])] = sattr + "\"%s\">" % i[1] + self._label[int(i[0])]

                    if "</TD></TR><TR>" in self._label[int(i[0])]:
                        self._label[int(i[0])] = self._label[int(i[0])].replace("</TD></TR><TR>", eattr + "</TD></TR><TR>")
                    else:
                        self._label[int(i[0])] = self._label[int(i[0])] + eattr


                for i in prevnbsp:
                    self._label.insert(i, "&nbsp;")

        def _lineattr(self, fsattr, tsattr, value, eattr = None):
            if len(value) > 0:
                if value[0][0] == 0:
                    if "FontAwesome" not in self._label[1]:
                        self._label = "<SEP>".join(self._label)
                        self._label = self._label.replace(fsattr, \
                                "%s\"%s\">" % (tsattr, value[0][1]) \
                                if value[0][1] not in set(['U', 'B', 'S', 'I'])\
                                else "%s%s>" % (tsattr, value[0][1]) )
                        if eattr:
                            self._label = self._label.replace("</TD>", eattr + "</TD>")
                        self._label = self._label.split("<SEP>")
                    else:
                        first = self._label[0]
                        if eattr:
                            for i in range(2, len(self._label)):
                                self._label[i] = self._label[i].replace("</TD>", eattr + "</TD>")
                        self._label = "<SEP>".join(self._label[1:])
                        self._label = self._label.replace(fsattr, \
                                "%s\"%s\">" % (tsattr, value[0][1]) \
                                if value[0][1] not in set(['U', 'B', 'S', 'I'])\
                                else "%s%s>" % (tsattr, value[0][1]) )
                        self._label = self._label.split("<SEP>")
                        self._label.insert(0, first)
                else:
                    self._label = "<SEP>".join(self._label)
                    self._label = self._label.split("</TD></TR><TR>")
                    for i in value:
                        li = int(i[0])
                        self._label[li - 1] = \
                                self._label[li - 1].replace(fsattr, \
                                "%s\"%s\">" % (tsattr, i[1]) if i[1] not in set(['U', 'B', 'S', 'I']) \
                                else "%s%s>" % (tsattr, i[1]))
                        if eattr and li - 1 < len(self._label) - 1:
                            self._label[li - 1] = self._label[li - 1] + eattr
                        elif eattr and li - 1 == len(self._label) - 1:
                            self._label[li - 1] = self._label[li - 1].replace("</TD>", eattr + "</TD>")
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

    def _addchild_rev(self, nodename, label, tabs, ntype, p, wc=[], lc=[], ws=[], ls=[], wf=[], lf=[], vrbt=False, draw=False):
        c = self.Node(nodename, label, tabs, ntype, p, wc, lc, ws, ls, wf, lf, vrbt, draw)
        c._parent = p
        p._child.insert(0, c)
        return c

    def addchild_rev(self, nodename, tabs, ntype, label, p, wordcolor=[], linecolor=[], wordfsize=[], linefsize=[], wordfstyle=[], linefstyle=[], sgcolor=None, sgtitle=None, sgstyle=None, vrbt=False, draw=False):
        sgattr = ""
        if sgcolor and sgcolor[0] == "s":
            self._addchild_rev("", ["}"], tabs, "sgwrap", p)
        self._addchild_rev("", ["}"], tabs, "sgwrap", p)
        if sgtitle:
            self._addchild_rev("", ["label = <<TABLE CELLBORDER=\"0\" CELLPADDING=\"3\" CELLSPACING=\"3\" BORDER=\"0\"><TR><TD BGCOLOR=\"#E9ED5F\" COLOR=\"#000000\"><U>%s</U></TD></TR></TABLE>>" % (sgtitle)], tabs, "sgwrap", p)
        c = self._addchild_rev(nodename, label, tabs, ntype, p, wordcolor, linecolor, wordfsize, linefsize, wordfstyle, linefstyle, vrbt, draw)
        c.wordfsize()
        c.wordfstyle()
        c.linefsize()
        c.colorifywords()
        c.linefstyle()
        c.colorifylines()

        PostAttrProcLabel(c._label, ntype, vrbt, draw)

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


def HtmlCompositeArrow(arrow, htmlcode, i, j, labelhtml):
    resf = i.find(arrow)

    if resf == -1:
        return

    if resf == 0 and len(i) == 2:
        labelhtml[j] = i.replace(arrow, htmlcode)
    elif resf == 0 and len(i) > 2:
        splitstr = i.split(arrow, 1)
        labelhtml[j] = htmlcode
        labelhtml.insert(j + 1, splitstr[1])
    elif resf > 0:
        splitstr = i.split(arrow, 1)
        labelhtml[j] = splitstr[0] + htmlcode + splitstr[1]
    return labelhtml[j]

def WriteDot(DotFile):
    outputfile = open(DotFile, 'w')
    outputfile.write(dotbuf)
    outputfile.close()


def SendRestartMSG(sockwildcard, sockcfg=None):
    config = ConfigParser.ConfigParser()
    config.read(cfg)

    sockp = config.defaults().get(sockcfg)

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(sockp)
    except socket.error as m:
        print sockcfg
        print m
    else:
        sock.send("%s restart" % (sockwildcard[0]), 64)
        sock.close()


def ScaleImg(argholder):
    subprocess.call("convert -scale %s %s %s" % (argholder.scale, gvroot + argholder.jpgname, gvroot + argholder.jpgname), shell=True)


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
    proc.communicate(dotbuf)

    subprocess.call("convert -shave 2x2 %s %s" % (gvroot + argholder.jpgname, gvroot + argholder.jpgname), shell=True)

    if not notitle:
        subprocess.call("montit.py -s s -t '%s' %s" % (title, gvroot + argholder.jpgname), shell=True)

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
        print "montage building should be in %s/gv/" % (gvroot[0:-1])
        raise SystemExit(1)


    if cmfile:
        subprocess.call(["montage.py", cmfile])
        SendRestartMSG("rsync call", "inotsock")
    else:
        print "%s not found in any %s/*.cm" % (imgarg[2], gvroot + '/'.join(imgarg[0:2]))
        raise SystemExit(1)


def Skip(maplist, s=None, lsinw=None):
    if maplist:
        j = 0
        while j < len(maplist):
            if lsinw and type(maplist[j][2]) == dict and maplist[j][2]['lineskip']:
                maplist[j][2]['lineskip'] += lsinw
            if s:
                maplist[j][0] += s
            j += 1


def ParseAttributeLine(k, tonode, *args):
    wordcolor, wordfsize, wordfstyle, \
            linecolor, linefsize, linefstyle, \
            arrlines, arrend, \
            sgcolor, sgtitle, sgstyle, \
            edgecolor, edgestyle, edgend, edgethick, edglabel, \
            symbcolor, symbsize = args

    m = re.search('(m?[rgbycp])?(f[0-9]+)?(ld|ul|st|it)?', k)
    if m.group(1):
        if m.group(1)[0] == "m":
            linecolor.insert(0, [0, linecolors[m.group(1)[1:]], False])
        else:
            linecolor.insert(0, [0, fontcolor[m.group(1)], True])
        if m.group(2):
            linefsize.append([0, m.group(2)[1:]])
        if m.group(3):
            linefstyle.append([0, fontstyle[m.group(3)]])
    elif m.group(2):
        linefsize.append([0, m.group(2)[1:]])
        if m.group(3):
            linefstyle.append([0, fontstyle[m.group(3)]])
    elif m.group(3):
        if m.group(3):
            linefstyle.append([0, fontstyle[m.group(3)]])

    m = re.search('(l[0-9]+)?(m?[rgbycp])?(f[0-9]+)?(ld|ul|st|it)?', k)
    if m.group(1):
        if m.group(4): linefstyle.append([int(m.group(1)[1:]), fontstyle[m.group(4)]])
        if m.group(3): linefsize.append([int(m.group(1)[1:]), m.group(3)[1:]])
        if m.group(2):
            if m.group(2)[0] == "m":
                linecolor.append([int(m.group(1)[1:]), linecolors[m.group(2)[1:]], False])
            else:
                linecolor.append([int(m.group(1)[1:]), fontcolor[m.group(2)], True])

    lineskip = None
    m = re.search('(l[0-9]+)?(w(?:[0-9]+)|w(?:\[[0-9,\-]+\]))?([rgbycpk])?(f[0-9]+)?(ld|ul|st|it)?', k)
    if m.group(1):
        lineskip = int(m.group(1)[1:])
    if m.group(2):
        if m.group(2).count("[") == 1 and m.group(2).count("]"):
            if "-" in m.group(2):
                nm = re.match('(?:w\[)([0-9]+)(?:-)([0-9]+)(?:\])', m.group(2))
                s = nm.group(1)
                e = nm.group(2)
                nm = []
                for i in range(int(s), int(e) + 1):
                    nm.append(i)
            else:
                nm = re.findall('([0-9]+)(?:,?)', m.group(2))
            for i in nm:
                if m.group(3): wordcolor.append([int(i), fontcolor[m.group(3)], {'lineskip': lineskip} if lineskip else None])
                if m.group(4): wordfsize.append([int(i), m.group(4)[1:], {'lineskip': lineskip} if lineskip else None])
                if m.group(5): wordfstyle.append([int(i), fontstyle[m.group(5)], {'lineskip': lineskip} if lineskip else None])
        else:
            if m.group(3): wordcolor.append([int(m.group(2)[1:]), fontcolor[m.group(3)], {'lineskip': lineskip} if lineskip else None])
            if m.group(4): wordfsize.append([int(m.group(2)[1:]), m.group(4)[1:], {'lineskip': lineskip} if lineskip else None])
            if m.group(5): wordfstyle.append([int(m.group(2)[1:]), fontstyle[m.group(5)], {'lineskip': lineskip} if lineskip else None])
    lineskip = None

    m = re.search('(sym(?:[0-9]+)|sym(?:\[[0-9,]+\]))?([rgbycpk])?(f[0-9]+)?', k)
    if m.group(1):
        if m.group(1).count("[") == 1 and m.group(1).count("]"):
            nm = re.findall('([0-9]+)(?:,?)', m.group(1))
            for i in nm:
                if m.group(2): symbcolor.append([int(i), fontcolor[m.group(2)]])
                if m.group(3): symbsize.append([int(i), m.group(3)[1:]])
        else:
            if m.group(2): symbcolor.append([int(m.group(1)[3:]), fontcolor[m.group(2)]])
            if m.group(3): symbsize.append([int(m.group(1)[3:]), m.group(3)[1:]])

    m = re.search('(sg[rgbycpwkt]([sdtl](?!tart))?(start|end)?([\'\"](.*)[\'\"])?)?', k)
    if m.group(1):
        sgcolor.append(subgraphcolors[m.group(1)[2:3]])
        if "start" in m.group(1): sgcolor[0] = "s" + sgcolor[0]
        elif "end" in m.group(1): sgcolor[0] = "e" + sgcolor[0]
        if m.group(2):
            sgstyle.append(edgestyles[m.group(2)])
            if not sgcolor[0]:
                sgcolor[0] = bgcolor
        if m.group(5): sgtitle.append(m.group(5))

    m = re.search('((arr[0-9]+)?([rgbycp])?(t[0-9]+)?(start|end)([\'\"].*[\'\"])?)?', k)
    if m.group(1):
        if m.group(5) == "start":
            penwidth = 5 if not m.group(4) else int(m.group(4)[1:])
            arrcolor = arrcolors["d"] if not m.group(3) else arrcolors[m.group(3)]
            arrlabel = "label=%s" % (m.group(6).strip()) if m.group(6) else ""
            arrlines.append([m.group(2)[3:], [tonode], "[minlen=\"0.1\" maxlen=\"0.1\" dir=\"forward\" arrowtail=\"none\" arrowhead=\"vee\" arrowsize=\"2\" style=\"dashed\" constraint=\"false\" color=\"%s\" arrowsize=\"%f\" penwidth=\"%i\" %s]" % (arrcolor, math.sqrt(penwidth/2), penwidth, arrlabel)])
        elif m.group(5) == "end":
            arrend.update({m.group(2)[3:] : tonode})

    m = re.search('(edg)?([rgbycp])?(t[0-9]+)?([sdtl])?([amovx])?([\'\"].*[\'\"])?', k)
    if m.group(1):
        if m.group(2): edgecolor.append("%s" % (edgecolors[m.group(2)]))
        if m.group(3): edgethick.append("arrowsize=\"%f\" penwidth=\"%i\"" \
                % (math.sqrt(int(m.group(3)[1:])/2), int(m.group(3)[1:])))
        elif not m.group(3): edgethick.append("arrowsize=\"%f\" penwidth=\"%i\"" \
                % (math.sqrt(5/2), 5))
        if m.group(4): edgestyle.append("style=\"%s\"" % (edgestyles[m.group(4)]))
        if m.group(5): edgend.append("arrowhead=\"%s\"" % (edgeends[m.group(5)]))
        if m.group(6): edglabel.append("label=%s" % m.group(6).strip())


def ParseOtlname(keyword, line):
    m = re.search("(%s[ ]*=[ ]*)(\".*\")[ ]*" % (keyword), line)
    if m is None:
        m = re.search("(%s[ ]*=[ ]*)([\w/.\-~_]*)[ ]*" % (keyword), line)

    return m.group(2)

def ParseFnameLine(keyword, line):
    global notitle

    m = re.search("(%s[ ]*=[ ]*)(\".*\")[ ]*(notitle)?" % (keyword), line)
    if m is None:
        m = re.search("(%s[ ]*=[ ]*)([\w/.\-~_]*)[ ]*(notitle)?" % (keyword), line)
        if m.group(3):
            notitle = True
    else:
        if m.group(3):
            notitle = True

    return m.group(2)


def JoinSepKeyValue(key, line):
    mi = None
    for (i, s) in enumerate(line):
        if key in s: mi = i
    if mi:
        i = int(mi)
        jnl = " ".join(line[i:])
        if re.match("%s = " %(key), jnl):
            line[i] = line[i] + line[i + 1] + line[i + 2]
            del(line[i + 1])
            del(line[i + 1])
        elif re.match("(%s =)|(%s= )" % (key, key), jnl):
            line[i] = line[i] + line[i + 1]
            del(line[i + 1])

def GenImgPath(imgpath):
    if imgpath.startswith('/'):
        imgpath = imgpath
    elif imgpath.startswith('~'):
        imgpath = imgpath.replace('~', os.environ['HOME'])
    else:
        imgpath = os.environ['PWD'] + '/' + imgpath
    return imgpath

def GenDot(lines, argholder, parser):
    tree = Tree()
    parentlist = [None] * MAXDEPTH

    rootnodename = "node1"
    root = tree.addroot(rootnodename)
    parentlist[0] = root

    global dotbuf, title, notitle, montagetitle
    jpgname, dotname = "", ""

    tabnum = lines[0].count("\t")

    m = re.search('(\t|\#) (.*)', lines[0])
    title = m.group(2)

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
        if re.search("\t(:|\|)\s*fname", line):
            jpgname = ParseFnameLine("fname", line)
            jpgname = jpgname.strip()

            if re.search("otlname", line):
                title = ParseOtlname("otlname", line) + '  -  ' + title

        if lines.index(line) < len(lines) - 1:
            nextline = lines[lines.index(line) + 1]
        else:
            nextline = lines[lines.index(line)]

        if re.search("(\t\#) (.*)", line):
            level = line[:line.find("#")].count("\t") - tabnum

            m = re.search('(\t|\#) (.*)', line)
            label = m.group(2)

            ntype = ""
            vrbt = False
            draw = False

            if "verbatim" in nextline or "verbat" in nextline:
                vrbt = True

            if "draw" in nextline:
                draw = True

            if re.match("img[ ]*=", label):
                m = re.match("(img)(?:[  ]*=[  ]*)(.*)", label)
                if m:
                    splittedstr = [m.group(1), m.group(2)]
                    if splittedstr[0] == "img":
                        labelhtml = ["<TABLE BORDER=\"0\" CELLBORDER=\"0\"><TR><TD CELLPADDING=\"0\" BORDER=\"1\"><IMG SRC=\"" + GenImgPath(splittedstr[1].strip()) + "\"/></TD></TR></TABLE>"]
                        ntype = "img"
            else:
                labelhtml = label.split()
                j = 0
                for i in labelhtml:
                    if i[0] != '<' and i.find(";") > 0:
                        labelhtml[j] = i.replace(";", "<BR/>")

                    r = i.find(">")
                    if r == 0 and len(i) == 1:
                        labelhtml[j] = i.replace(">", "&gt;")

                    r = i.find("<")
                    if r == 0 and len(i) == 1:
                        labelhtml[j] = i.replace("<", "&lt;")

                    if not vrbt and not draw:
                        HtmlCompositeArrow("<=", html_larrow1, i, j, labelhtml)
                        HtmlCompositeArrow("=>", html_rarrow1, i, j, labelhtml)

                        HtmlCompositeArrow("->", html_rarrow2, i, j, labelhtml)
                        HtmlCompositeArrow("<-", html_larrow2, i, j, labelhtml)
                    else:
                        HtmlCompositeArrow("<=", "&lt;&#9552;", i, j, labelhtml)
                        HtmlCompositeArrow("=>", "&#9552;&gt;", i, j, labelhtml)

                        #HtmlCompositeArrow("->", "&#8722;&gt;", i, j, labelhtml)
                        #HtmlCompositeArrow("<-", "&lt;&#8772;", i, j, labelhtml)

                        if '<-' in labelhtml[j]:
                            labelhtml[j] = re.sub("<-", "&lt;-", labelhtml[j])

                        if '->' in labelhtml[j]:
                            labelhtml[j] = re.sub("->", "-&gt;", labelhtml[j])

                        #if '<' in labelhtml[j]:
                        #    labelhtml[j] = re.sub("<", "&lt;", labelhtml[j])

                        #if '>' in labelhtml[j]:
                        #    labelhtml[j] = re.sub(">", "&gt;", labelhtml[j])

                        if "><<" in labelhtml[j] or ">><" in labelhtml[j]:
                            labelhtml[j] = re.sub("(?<=WHITESP>)<(<WHITESP>)", \
                                "&lt;<WHITESP>", labelhtml[j])
                            labelhtml[j] = re.sub("(?<=WHITESP>)>(<WHITESP>)", \
                                "&gt;<WHITESP>", labelhtml[j])

                    j += 1

            if ntype is not "img":
                labelhtml.insert(0, "<TABLE CELLBORDER=\"0\" CELLSPACING=\"0\" BORDER=\"0\"><TR><TD>")
                i = 1
                try:
                    while i < len(labelhtml):
                        if "<TAB>" in labelhtml[i]:
                            labelhtml[i] = labelhtml[i].replace("<TAB>", "&emsp;&emsp;")
                        if "<WHITESP>" in labelhtml[i]:
                            front = re.search("(<WHITESP>)*", labelhtml[i]).group(0)
                            rem = re.split("^(<WHITESP>)*", labelhtml[i])[2]
                            tl = rem.split("<WHITESP>")
                            del(labelhtml[i])
                            for el in reversed(tl):
                                if el: labelhtml.insert(i, el)
                                else: labelhtml[i] = " " + labelhtml[i]
                            labelhtml[i] =  " " * front.count("<WHITESP") + labelhtml[i]
                        if "<BR/>" in labelhtml[i]:
                            labelhtml[i] = labelhtml[i].replace("<BR/>", "</TD></TR><TR><TD>")
                        elif "<BR/>" not in labelhtml[i]:
                            labelhtml.insert(i + 1, "&nbsp;")
                            i += 1
                        i += 1
                    labelhtml.insert(len(labelhtml), "</TD></TR></TABLE>")
                except (IndexError, KeyError) as e:
                    print e, labelhtml[i]

            wordcolor, wordfsize, wordfstyle = [], [], []
            linecolor, linefsize, linefstyle = [], [], []
            sgcolor, sgtitle, sgstyle = [], [], []
            edgecolor, edgestyle, edgend, edgethick, edglabel = [], [], [], [], []
            symbcolor, symbsize, symblist = [], [], []

            fromnode = rootnodename
            for i in range(0, level - 1):
                fromnode += "%s" % ("{:=02}".format(nodelevel[i] - 1))
            tonode = fromnode + "%s" % ("{:=02}".format(nodelevel[level - 1]))

            if nextline.find("#") == -1 and ntype is not "img":
                nextline = nextline.split()
                spacesg = [[nextline[x], x] for x in range(len(nextline)) \
                        if nextline[x].count("\"") == 1 or nextline[x].count("\'") == 1]

                lens = len(spacesg)
                for i in range(0, lens, 2):
                    if (spacesg[i + 1][1] - spacesg[i][1]) >= 2:
                        spacesg[i][0] = spacesg[i][0] + " " + \
                                " ".join(nextline[spacesg[i][1] + 1 : spacesg[i + 1][1]])

                j = 0
                for i in range(0, lens, 2):
                    del(nextline[spacesg[i][1] - j : spacesg[i + 1][1] + 1 - j])
                    j += spacesg[i + 1][1] - spacesg[i][1] + 1

                nextline += [spacesg[i][0] + " " + spacesg[i + 1][0] for i in range(0, lens, 2)]

                JoinSepKeyValue("img", nextline)
                JoinSepKeyValue("symb", nextline)

                for k in nextline:
                    if k in nodetype and k not in set(["verbatim", "verbat", "draw"]):
                        ntype = k
                    else:
                        ParseAttributeLine(k, tonode, \
                                wordcolor, wordfsize, wordfstyle, \
                                linecolor, linefsize, linefstyle, \
                                arrlines, arrend,\
                                sgcolor, sgtitle, sgstyle, \
                                edgecolor, edgestyle, edgend, edgethick, edglabel,\
                                symbcolor, symbsize)

                    if k.find("=") > 0:
                        m = re.match("([\W\w]*)(?:=)(.*)", k)
                        tokval = [m.group(1), m.group(2)]
                        if tokval[0] == "img":
                            labelhtml.insert(len(labelhtml) - 1, "</TD></TR><TR><TD COLSPAN=\"1\" CELLPADDING=\"0\" BORDER=\"1\"><IMG SRC=\"" + GenImgPath(tokval[1].strip()) + "\"/>")
                            ntype = "imgil"
                        elif tokval[0] == "symb" and ntype != "imgil":
                            symblist = tokval[1].split(':')
                        elif tokval[0] == "dood":
                            doodlist = tokval[1].split(':')
                            if len(doodlist) > 1:
                                global tmpdir
                                tmpdir.append(tempfile.mkdtemp())
                                exestring = "montage %s -geometry +3+0 \
                                        -tile %dx -background Transparent %s/doodle.png" \
                                        % (' '.join(doodlist), len(doodlist), tmpdir[-1])
                                if subprocess.call(exestring, shell=True) == 0:
                                    labelhtml.insert(len(labelhtml) - 1, \
                                            "</TD></TR><TR><TD COLSPAN=\"1\" CELLPADDING=\"10\"\
                                            BORDER=\"0\"><IMG SRC=\"" + "%s/doodle.png" \
                                            % (tmpdir[-1]) + "\"/>")
                            else:
                                labelhtml.insert(len(labelhtml) - 1, \
                                        "</TD></TR><TR><TD COLSPAN=\"1\" CELLPADDING=\"10\"\
                                        BORDER=\"0\"><IMG SRC=\"" +  GenImgPath(tokval[1]) + "\"/>")
                            numdood += 1
                            ntype = "dood"

            if symblist:
                i = 0
                symbols = ""
                while i < len(symblist):
                    color, size = "COLOR=\"%s\"" % (fontcolor['r']), \
                            "POINT-SIZE=\"25\""
                    for j in symbcolor:
                        if j[0] - 1 == i:
                            color = "COLOR=\"%s\"" % (j[1])
                            break
                    for j in symbsize:
                        if j[0] - 1 == i:
                            size = "POINT-SIZE=\"%s\"" % (j[1])
                            break
                    symbols += "<FONT FACE=\"FontAwesome\" %s %s>" % \
                            (color, size) + fontawesome.symb[symblist[i]] \
                            + "</FONT>&nbsp;"
                    i += 1
                wasone = labelhtml[1]
                labelhtml[1] = symbols + "</TD></TR><TR><TD>"
                labelhtml.insert(2, wasone)

            PreAttrProcLabel(labelhtml, ntype)

            if vrbt or draw:
                wordskip = len(line.split("<BR/>", 1)[0].split()) - 1
                Skip(wordfsize, s=wordskip)
                Skip(wordcolor, s=wordskip)
                Skip(wordfstyle, s=wordskip)
                if linecolor and not linecolor[0][0] == 0:
                    Skip(linecolor, s=1)
                if linefsize and not linefsize[0][0] == 0:
                    Skip(linefsize, s=1)
                if linefstyle and not linefstyle[0][0] == 0:
                    Skip(linefstyle, s=1)

            if symblist:
                Skip(wordfsize, s=len(symblist))
                Skip(wordcolor, s=len(symblist))
                Skip(wordfstyle, s=len(symblist))

            if ntype == "term":
                Skip(wordfsize, s=2)
                Skip(wordcolor, s=2)
                Skip(wordfstyle, s=2)

            if ntype in set(["title", "quest", "date", "impor", "impog", "impob"]) or\
                    (ntype != "img" and "FontAwesome" in labelhtml[1]):
                if wordcolor: Skip(wordcolor, lsinw=1)
                if wordfsize: Skip(wordfsize, lsinw=1)
                if wordfstyle: Skip(wordfstyle, lsinw=1)
                if linecolor and not linecolor[0][0] == 0:
                    Skip(linecolor, s=1)
                if linefsize and not linefsize[0][0] == 0:
                    Skip(linefsize, s=1)
                if linefstyle and not linefstyle[0][0] == 0:
                    Skip(linefstyle, s=1)

            if ntype == "term":
                if linecolor and not linecolor[0][0] == 0:
                    Skip(linecolor, s=1)
                if linefsize and not linefsize[0][0] == 0:
                    Skip(linefsize, s=1)
                if linefstyle and not linefstyle[0][0] == 0:
                    Skip(linefstyle, s=1)

            if not ntype:
                ntype = "def"

            tabs = ""
            for i in range(0, level + 1):
                tabs += "\t"

            edgeattrs = ""
            for i in [edgecolor, edgestyle, edgethick, edgend, edglabel]:
                if i:
                    edgeattrs += " " + i[0]

            if ntype in edgetype and not edgeattrs:
                edge.append("%s%s:e -> %s:w[%s];\n" \
                        % (tabs, fromnode, tonode, edgetype[ntype]))
            elif edgeattrs:
                edge.append("%s%s:e -> %s:w[%s];\n" \
                        % (tabs, fromnode, tonode, edgeattrs))
            else:
                edge.append("%s%s:e -> %s:w;\n" \
                        % (tabs, fromnode, tonode))

            parentlist[level] = tree.addchild_rev(tonode, tabs, ntype, labelhtml,\
                    parentlist[level - 1], wordcolor, linecolor, wordfsize, \
                    linefsize, wordfstyle, linefstyle, \
                    sgcolor[0] if sgcolor else None, \
                    sgtitle[0] if sgtitle else None, \
                    sgstyle[0] if sgstyle else None, \
                    vrbt, draw)

            nodelevel[level - 1] += 1

            for i in range(level, len(nodelevel) - 1):
                nodelevel[i] = 1

    for p in tree.postorder():
        t = p.getype()
        if p.getype() != "root":
            if p.is_leaf() is not True:
                if t in set(["cred", "cgreen", "ccyan", "cblue", "cpink",  "cyello", "corang"]):
                    s = p.element().replace("shape=box", "margin=\"0.2,0.2\" shape=box fontsize=\"%s\"" % (fontsize['l']) + "\n")
                    dotbuf += s
                else:
                    s = p.element().replace(nodetype['def'], nodetype['node']) + "\n"
                    if t not in ["img", "imgil"]:
                        s = s.replace("shape=box", "shape=box margin=\"0.2,0.2\"")
                    dotbuf += s
            else:
                dotbuf += p.element() + "\n"

    dotbuf += "\n\n"

    for i in arrlines:
        i[1].append(arrend[i[0]])
        edge.append("%s -> %s %s;\n" % (i[1][0], i[1][1], i[2].replace("[", "[ltail=\"%s\" lhead=\"%s\" " % (i[1][0].replace("node", "cluster"), i[1][1].replace("node", "cluster")))))

    i = len(edge) - 1
    while i >= 0:
        dotbuf += edge[i]
        i -= 1

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


def PostAttrProcLabel(label, ntype, vrbt, draw):
    if ntype == "commen":
        label.insert(0, "<I>")
        label.insert(len(label), "</I>")
    if ntype == "example" or vrbt or draw:
        for i in range(len(label)):
            label[i] = label[i].replace("<TD", "<TD ALIGN=\"left\"")
    if ntype == "term":
        for i in range(len(label)):
            if i == 1:
                label[i] = label[i].replace("<TD", "<TD BGCOLOR=\"#18A828\"")
            elif i > 1:
                label[i] = label[i].replace("<TD", "<TD ALIGN=\"left\"")
    if vrbt or draw:
        label[1] = "<B><U><FONT>" + label[1]
        for i, v in enumerate(label):
            if i >= 1 and "</TD>" in label[i]:
                label[i] = label[i].replace("</TD>", "</FONT></U></B></TD>")
                break


def PreAttrProcLabel(label, ntype):
    if ntype == "title":
        label[1] = "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"25\">" + fontawesome.symb["info-circle"] + "</FONT></TD></TR><TR><TD>" + label[1]
    elif ntype == "date":
        label[1] = "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"25\">" + fontawesome.symb["clock-o"] + "</FONT></TD></TR><TR><TD>" + label[1]
    elif ntype == "quest":
        label[1] = "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"25\">" + fontawesome.symb["question-circle"] + "</FONT></TD></TR><TR><TD>" + label[1]
    elif ntype == "impor" or ntype == "impog" or ntype == "impob":
        label[1] = "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"25\">" + fontawesome.symb["warning"] + "</FONT></TD></TR><TR><TD>" + label[1]
    elif ntype == "term":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"%s\" POINT-SIZE=\"1\">" % (fontcolor['k']) + fontawesome.symb["terminal"] + "</FONT></TD></TR><TR><TD>")
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"%s\" POINT-SIZE=\"15\">" % (fontcolor['k'])+ fontawesome.symb["desktop"] + "</FONT>&nbsp;<FONT FACE=\"FontAwesome\" COLOR=\"%s\" POINT-SIZE=\"20\">" % (fontcolor['k']) + fontawesome.symb["terminal"] + "</FONT></TD></TR><TR><TD>")


def ParLoc(line):
    parloc = line.find("#")
    if parloc == -1:
        parloc = line.find(":")
    if parloc == -1:
        parloc = line.find(";")
    if parloc == -1:
        parloc = line.find("|")
    return parloc


def main():
    argholder = ArgHolder()

    j, level, tabroot = 0, 0, 0
    title = None
    linesbymm, linesall = [], []

    parser = argparse.ArgumentParser()
    parser.add_argument('-r', dest='sock', nargs='+')
    parser.add_argument('-f', dest='files', nargs='+')
    parser.add_argument('-m', '--mtg', action='store_true')
    parser.add_argument('-p', dest='preview', action='store_true')
    parser.add_argument('-s', dest='scale', nargs='?', const="specified")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', dest='dotname', nargs='?', const="specified")
    group.add_argument('-i', dest='jpgname', nargs='?', const="specified")
    parser.parse_args(namespace=argholder)

    if argholder.files:
        for fil in argholder.files:
            fo = open(fil)
            for line in fo:
                linesall.append(line.rstrip())
    else:
        linesall = sys.stdin.read().splitlines()

    j = 0
    while j < len(linesall) - 1:
        nextline = linesall[j + 1]
        level = linesall[j][:ParLoc(linesall[j])].count("\t")

        if re.search("\t(:|;|\|)\s*fname", nextline):
            title = linesall[j]
            tabroot = level
            level += 1

            i = j + 2
            while i < len(linesall) - 1 and level > tabroot:
                level = linesall[i][:ParLoc(linesall[i])].count("\t")
                if "# " in linesall[i] and level > tabroot:
                    linesbymm.append(linesall[i])
                    if "# " not in linesall[i + 1] and level > tabroot:
                        linesbymm.append(linesall[i + 1])
                        if "verbatim" in linesall[i + 1] or\
                            "verbat" in linesall[i + 1] or\
                            "draw" in linesall[i + 1]:
                            j = i + 2
                            v = []
                            while j < len(linesall) and '# ' not in linesall[j] \
                                    and not re.search("\t\s*[a-zA-Z0-9]\s*", linesall[j]):
                                if "\t:" in linesall[j]:
                                    v.append(linesall[j].lstrip("\t:").rstrip())
                                elif "\t|" in linesall[j]:
                                    v.append(linesall[j].lstrip("\t|").rstrip())
                                elif "\t;" in linesall[j]:
                                    v.append(linesall[j].lstrip("\t;").rstrip())
                                v[-1] = v[-1].replace(" ", "<WHITESP>")
                                v[-1] = v[-1].replace("\t", "<TAB>")
                                v[-1] = v[-1] + "<BR/> "
                                j += 1
                            else:
                                vrbtnode = "".join(v)
                                vrbtnode = vrbtnode.strip("<BR/>")
                                vrbtnode = linesall[i] + "<BR/>" + vrbtnode
                                linesbymm[-2] = vrbtnode
                    elif "# " in linesall[i + 1] and linesall[i + 1][:ParLoc(linesall[i + 1])].count("\t") == level:
                        j = i + 1
                        while level * "\t" + "# " in linesall[j]:
                            linesbymm[-1] = linesbymm[-1].rstrip() + linesall[j].replace("#", ";").strip()
                            del(linesall[j])
                        else:
                            if "# " not in linesall[j]:
                                linesbymm.append(linesall[j])
                i += 1
            else:
                j = i - 2
                linesbymm.insert(0, title)
                linesbymm.insert(1, nextline)
                GenDot(linesbymm, argholder, parser)
                linesbymm = []

        j += 1

main()
