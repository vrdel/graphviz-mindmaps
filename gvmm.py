#!/home/daniel/.pyenv/versions/gvmm-py3/bin/python3

import sys, re, subprocess, argparse, os, fnmatch, fontawesome, tempfile, unicodedata
import socket, configparser, math


MAXDEPTH = 32
gvroot = "/home/daniel/my_notes/"
dotbuf = ""
tmpdir = []
title = ""
montagetitle = None
notitle = False

fontcolor = {"def" : "#000000", "r" : "#B30000", "g" : "#027b10", "b" : "#151e94", "y" : "#ebec50", "c" : "#00948c", "p" : "#94008b", "k" : "#000000", "t" : "#ffffff"}
linecolors = {"r" : "#FF8080", "g" : "#8BFF80", "b" : "#80CAFF", "y" : "#FFF180", "c" : "#80FFFB", "p" : "#FF80E7", "k" : "#000000"}
subgraphcolors = {"r" : "#FF000020", "g" : "#00FF0020", "b" : "#0000FF20", "y" : "#FFF40020", "c" : "#00FFD204", "p" : "#FF00EA20", "w" : "#FFFFFF20", "k" : "#00000020", "t" : ""}
vrbtcolors = {"cgreen" : "#dffde6", "cred" : "#fde0df", "cblue" : "#e1dffd", "ccyan" : "#dffdfa", "cyello" : "#fcfddf", "corang" : "#fdecdf", "cpink" : "#fddff3", "cwhite": "#ffffff", "def" : "#dfeafd"}
fontstyle = {"ul" : "U", "ld" : "B", "st" : "S", "it" : "I"}
bgcolor = "#efefef"
font = {"comic" : "Comic Sans MS", "mono" : "Dejavu Sans Mono", "comicb" : "Comic Sans MS Bold", "balsamiq" : "Balsamiq Sans", "balsamiqb" : "Balsamiq Sans Bold"}
fontsize = {"s" : "12", "m" : "14", "l" : "16", "xl" : "20", "xxl" : "24"}
nodetype = {"root" : "fontsize=\"%s\" margin=\"0.5\" shape=cds style=radial color=\"#000000\" fillcolor=\"#dfdfdf\" gradientangle=\"90\"" % (fontsize['xxl']),
        "quest" : "shape=oval fontname=\"%s\" fontsize=\"%s\" margin=\"0,0\" style=\"radial\" fillcolor=\"#fffbab\" color=\"#8a8a8a\"" % (font['comic'], fontsize['l']),
        "impor" : "shape=signature fontsize=\"%s\" margin=\"0.25\" style=\"radial\" fillcolor=\"#ffb6c1\" color=\"#8a8a8a\"" % (fontsize['l']),
        "impog" : "shape=signature fontsize=\"%s\" margin=\"0.25\" style=\"radial\" fillcolor=\"#b6ffb7\" color=\"#8a8a8a\"" % (fontsize['l']),
        "impob" : "shape=signature fontsize=\"%s\" margin=\"0.25\" style=\"radial\" fillcolor=\"#b6e4ff\" color=\"#8a8a8a\"" % (fontsize['l']),
        "img" : "shape=box style=\"radial\" fillcolor=\"#fbfbfb\" color=\"#8a8a8a\"",
        "imgil" : "shape=box style=\"radial\" fillcolor=\"#fbfbfb\" color=\"#8a8a8a\"",
        "dood" : "shape=underline fontcolor=\"%s\" color=\"#b8b8b8\"" % (fontcolor['def']),
        "def" : "shape=underline fontcolor=\"%s\" color=\"#b8b8b8\"" % (fontcolor['def']),
        "underl" : "color=\"#b8b8b8\" fontcolor=\"%s\" shape=underline " % (fontcolor['def']),
        "node" : "shape=box style=\"rounded,radial\" fontsize=\"%s\" fillcolor=\"#f4f4f4\" color=\"#6a6a6a\"" % (fontsize['l']),
        "list" : "shape=rect style=\"radial\" fontsize=\"%s\" fillcolor=\"#d3f6ff\" color=\"#6a6a6a\"" % (fontsize['l']),
        "data" : "shape=cylinder style=\"radial\" margin=\"0.1,0.3\" fontsize=\"%s\" fillcolor=\"#ffffff\" color=\"#6a6a6a\"" % (fontsize['l']),
        "answer" : "shape=cds style=\"radial\" fontsize=\"%s\" margin=\"0.2\" fillcolor=\"#BAFFAF\" color=\"#6a6a6a\"" % (fontsize['l']),
        "title" : "shape=doubleoctagon fontname=\"%s\" margin=\"0,0\" fontsize=\"%s\" style=\"radial\" fillcolor=\"#abffff\" color=\"#8a8a8a\"" % (font['comicb'], fontsize['l']),
        "date" : "shape=component gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15,0.15\" fillcolor=\"#fbfbfb;0.93:#B30E0E\" color=\"#8a8a8a\"",
        "link" : "shape=component gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15,0.15\" fillcolor=\"#edf1ff;0.93:#3283c9\" color=\"#8a8a8a\"",
        "example" : "shape=note fontname=\"%s\" gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15\" fillcolor=\"#18A828;0.15:#fbfbfb\" color=\"#8a8a8a\"" % (font['mono']),
        "draw" : "shape=component fontname=\"%s\" style=\"radial\" margin=\"0.15,0.15\" fillcolor=\"%s\" color=\"#8a8a8a\"" % (font['mono'], vrbtcolors['cwhite']),
        "verbatim" : "shape=component fontname=\"%s\" style=\"radial\" margin=\"0.15,0.15\" fillcolor=\"%s\" color=\"#8a8a8a\"" % (font['mono'], vrbtcolors['def']),
        "commen" : "shape=note fontname=\"%s\" fontsize=\"%s\" margin=\"0.2\" style=\"radial\" fillcolor=\"#FFF09A\" color=\"#8a8a8a\"" % (font['comic'], fontsize['l']),
        "term" : "shape=note fontname=\"%s\" gradientangle=\"270\" style=\"filled\" margin=\"0.15,0.15\" fillcolor=\"#fbfbfb\" color=\"#8a8a8a\"" % (font['mono']),
        "check" : "shape=rarrow fontcolor=\"%s\" margin=\"0.20\" style=\"filled\" fillcolor=\"#4A90D9\" fontcolor=\"#ffffff\" color=\"#4A90D9\"" % (fontcolor['def']),
        "todo" : "shape=box fontcolor=\"%s\" margin=\"0.20\" style=\"filled, diagonals\" fillcolor=\"#FFF09A\" fontcolor=\"#404040\" color=\"#404040\"" % (fontcolor['def']),
        "decisi" : "shape=diamond style=\"rounded,radial\" fontsize=\"%s\" fillcolor=\"#ffc990\" color=\"#8a8a8a\"" % (fontsize['l']),
        "saying" : "shape=egg style=\"radial\" margin=\"0.0,0.15\" fontsize=\"%s\" fillcolor=\"#A9FFFF\" color=\"#8a8a8a\"" % (fontsize['l']),
        "cgreen" : "shape=box style=\"rounded,radial\" fillcolor=\"#bcffc2\" color=\"#8a8a8a\"",
        "ccyan" : "shape=box style=\"rounded,radial\" fillcolor=\"#b9ffff\" color=\"#8a8a8a\"",
        "cblue" : "shape=box style=\"rounded,radial\" fillcolor=\"#b2d5fb\" color=\"#8a8a8a\"",
        "cpink" : "shape=box style=\"rounded,radial\" fillcolor=\"#ffb8fe\" color=\"#8a8a8a\"",
        "cred" : "shape=box style=\"rounded,radial\" fillcolor=\"#fbc1bf\" color=\"#8a8a8a\"",
        "cyello" : "shape=box style=\"rounded,radial\" fillcolor=\"#fefb88\" color=\"#8a8a8a\"",
        "corang" : "shape=box style=\"rounded,radial\" fillcolor=\"#ffc990\" color=\"#8a8a8a\"",
        "cgrey" : "shape=box style=\"rounded,radial\" fillcolor=\"#9e9e9e\" color=\"#8a8a8a\"",
        "cblack" : "shape=box style=\"rounded,radial\" fillcolor=\"#2b2b2b\" color=\"#8a8a8a\""}
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


def ResolveColorNodeTypeToken(token):
    if token in nodetype:
        return token

    aliases = {"nodes": "node"}
    m = re.match(
        r"^(c(?:green|cyan|blue|pink|red|yello|orang|black|grey)|impor|impog|impob|quest|commen|check|todo|title|node|nodes)(-?[0-9]+)$",
        token
    )
    if not m:
        return None

    base = m.group(1)
    if base in aliases:
        base = aliases[base]
    if base not in nodetype:
        return None

    delta = int(m.group(2))

    fm = re.search(r'fillcolor="(#?[0-9A-Fa-f]{6})"', nodetype[base])
    if not fm:
        return None

    rgb = fm.group(1).lstrip("#")
    channels = [int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)]
    shifted = [min(255, max(0, c + delta)) for c in channels]
    newfill = "#%02x%02x%02x" % (shifted[0], shifted[1], shifted[2])

    nodetype[token] = nodetype[base].replace(fm.group(1), newfill, 1)
    return token

def ResolveVerbatimFillColorToken(token):
    if token in vrbtcolors:
        return vrbtcolors[token]

    m = re.match(
        r"^(c(?:green|cyan|blue|pink|red|yello|orang|white))(-?[0-9]+)$",
        token
    )
    if not m:
        return None

    base = m.group(1)
    if base not in vrbtcolors:
        return None

    delta = int(m.group(2))
    rgb = vrbtcolors[base].lstrip("#")
    channels = [int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)]
    shifted = [min(255, max(0, c + delta)) for c in channels]
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
    m = re.match(r"^(impor|impog|impob|quest|date|title|link|saying)(-?[0-9]+)$", token)
    if m:
        return m.group(1)
    return token


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
                    fillcolor = ResolveVerbatimFillColorToken(self._ntype)
                    if not fillcolor:
                        fillcolor = vrbtcolors['def']
                    return "\t" + self._tabs + self._nodename + "[%s label=<%s>];" % (nodetype["verbatim"].replace(vrbtcolors['def'], fillcolor), "".join(self._label))
            elif self._draw:
                if self._ntype == "def":
                    return "\t" + self._tabs + self._nodename + "[%s label=<%s>];" % (nodetype["draw"], "".join(self._label))
                else:
                    fillcolor = ResolveVerbatimFillColorToken(self._ntype)
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
                li = self._resolve_line_sel(int(i[0]), len(self._label))
                if li < 1 or li > len(self._label):
                    continue

                deco = "<TD><FONT COLOR=\"%s\"><I><FONT FACE=\"FontAwesome\" POINT-SIZE=\"18\">%s</FONT>&nbsp;" % (fontcolor['b'], fontawesome.symb["calendar"])
                self._label[li - 1] = self._label[li - 1].replace("<TD>", deco, 1)
                if "</TD>" in self._label[li - 1]:
                    self._label[li - 1] = self._label[li - 1].replace("</TD>", "</I></FONT></TD>", 1)
                else:
                    self._label[li - 1] = self._label[li - 1] + "</I></FONT>"

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
                        li = self._resolve_line_sel(int(i[0]), len(self._label))
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

def ApplyInlineBacktickBold(text, allow_linebreak=False):
    patterns = [
        r'`([^`]+?)`' if allow_linebreak else r'`([^`;]+?)`',
        r'\*([^*]+?)\*' if allow_linebreak else r'\*([^*;]+?)\*',
    ]

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

def ResolveSymbolNames(spec):
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
        if name in fontawesome.symb:
            resolved.append(name)
            continue
        if name in aliases and aliases[name] in fontawesome.symb:
            resolved.append(aliases[name])
    return resolved

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


def ParseAttributeLine(k, tonode, *args):
    wordcolor, wordfsize, wordfstyle, \
            linecolor, linefsize, linefstyle, \
            arrlines, arrend, \
            sgcolor, sgtitle, sgstyle, \
            edgecolor, edgestyle, edgend, edgethick, edglabel, \
            symbcolor, symbsize, linedate = args

    def ParseIdxSpec(spec, prefix):
        idx = []
        if not spec:
            return idx
        end_mode = prefix.startswith("E")

        def ParseSingleIdx(part):
            part = part.strip()
            if not part:
                return None
            nm = re.match(r"^([0-9]+)$", part)
            if nm:
                n = int(nm.group(1))
                return -n if end_mode else n
            return None

        body = spec[len(prefix):]
        if body.startswith("[") and body.endswith("]"):
            body = body[1:-1]
            for part in body.split(","):
                part = part.strip()
                if not part:
                    continue
                if "-" in part:
                    nm = re.match(r"([0-9]+)-([0-9]+)", part)
                    if nm:
                        s = int(nm.group(1))
                        e = int(nm.group(2))
                        if s <= e:
                            for i in range(s, e + 1):
                                idx.append(-i if end_mode else i)
                        else:
                            for i in range(s, e - 1, -1):
                                idx.append(-i if end_mode else i)
                else:
                    parsed = ParseSingleIdx(part)
                    if parsed is not None:
                        idx.append(parsed)
        else:
            parsed = ParseSingleIdx(body)
            if parsed is not None:
                idx.append(parsed)

        return idx

    m = re.search('(m?[rgbycpkt])?(f[0-9]+)?((?:ld|ul|st|it)+)?', k)
    if m.group(1):
        if m.group(1)[0] == "m":
            linecolor.insert(0, [0, linecolors[m.group(1)[1:]], False])
        else:
            linecolor.insert(0, [0, fontcolor[m.group(1)], True])
        if m.group(2):
            linefsize.append([0, m.group(2)[1:]])
        if m.group(3):
            for si in range(0, len(m.group(3)), 2):
                linefstyle.append([0, fontstyle[m.group(3)[si:si+2]]])
    elif m.group(2):
        linefsize.append([0, m.group(2)[1:]])
        if m.group(3):
            for si in range(0, len(m.group(3)), 2):
                linefstyle.append([0, fontstyle[m.group(3)[si:si+2]]])
    elif m.group(3):
        for si in range(0, len(m.group(3)), 2):
            linefstyle.append([0, fontstyle[m.group(3)[si:si+2]]])

    m = re.search(r'((?:E?l)(?:[0-9]+|\[[0-9,\-]+\]))?(m?[rgbycpkt])?(f[0-9]+)?((?:ld|ul|st|it)+)?', k)
    if m.group(1):
        lprefix = "El" if m.group(1).startswith("El") else "l"
        lineidx = ParseIdxSpec(m.group(1), lprefix)
        for li in lineidx:
            if m.group(4):
                for si in range(0, len(m.group(4)), 2):
                    linefstyle.append([li, fontstyle[m.group(4)[si:si+2]]])
            if m.group(3):
                linefsize.append([li, m.group(3)[1:]])
            if m.group(2):
                if m.group(2)[0] == "m":
                    linecolor.append([li, linecolors[m.group(2)[1:]], False])
                else:
                    linecolor.append([li, fontcolor[m.group(2)], True])

    m = re.search(r'((?:E?l)(?:[0-9]+|\[[0-9,\-]+\]))date', k)
    if m and m.group(1):
        lprefix = "El" if m.group(1).startswith("El") else "l"
        lineidx = ParseIdxSpec(m.group(1), lprefix)
        for li in lineidx:
            linedate.append([li, True])

    m = re.search(r'((?:E?l)(?:[0-9]+|\[[0-9,\-]+\]))?((?:E?w)(?:[0-9]+)|(?:E?w)(?:\[[0-9,\-]+\]))?([rgbycpkt])?(f[0-9]+)?((?:ld|ul|st|it)+)?', k)
    if m.group(2):
        if m.group(1):
            lprefix = "El" if m.group(1).startswith("El") else "l"
            lineidx = ParseIdxSpec(m.group(1), lprefix)
        else:
            lineidx = [None]
        wprefix = "Ew" if m.group(2).startswith("Ew") else "w"
        wordidx = ParseIdxSpec(m.group(2), wprefix)
        for li in lineidx:
            lmeta = {'lineskip': li} if li else None
            for wi in wordidx:
                if m.group(3):
                    wordcolor.append([wi, fontcolor[m.group(3)], lmeta])
                if m.group(4):
                    wordfsize.append([wi, m.group(4)[1:], lmeta])
                if m.group(5):
                    for si in range(0, len(m.group(5)), 2):
                        wordfstyle.append([wi, fontstyle[m.group(5)[si:si+2]], lmeta])

    m = re.search(r'(sym(?:[0-9]+)|sym(?:\[[0-9,]+\]))?([rgbycpkt])?(f[0-9]+)?', k)
    if m.group(1):
        if m.group(1).count("[") == 1 and m.group(1).count("]"):
            nm = re.findall('([0-9]+)(?:,?)', m.group(1))
            for i in nm:
                if m.group(2): symbcolor.append([int(i), fontcolor[m.group(2)]])
                if m.group(3): symbsize.append([int(i), m.group(3)[1:]])
        else:
            if m.group(2): symbcolor.append([int(m.group(1)[3:]), fontcolor[m.group(2)]])
            if m.group(3): symbsize.append([int(m.group(1)[3:]), m.group(3)[1:]])

    m = re.search(r'(sg([rgbycpwkt])(-?[0-9]+)?([sdtl](?!tart))?(start|end)?([\'\"](.*)[\'\"])?)?', k)
    if m.group(1):
        ckey = m.group(2)
        cval = subgraphcolors[ckey]

        if m.group(3) and cval:
            delta = int(m.group(3))
            mhex = re.match(r"^#([0-9A-Fa-f]{6})([0-9A-Fa-f]{2})?$", cval)
            if mhex:
                rgb = mhex.group(1)
                alpha = mhex.group(2) if mhex.group(2) else ""
                channels = [int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)]
                shifted = [min(255, max(0, ch + delta)) for ch in channels]
                cval = "#%02x%02x%02x%s" % (shifted[0], shifted[1], shifted[2], alpha)

        sgcolor.append(cval)
        if m.group(5) == "start":
            sgcolor[0] = "s" + sgcolor[0]
        elif m.group(5) == "end":
            sgcolor[0] = "e" + sgcolor[0]
        if m.group(4):
            sgstyle.append(edgestyles[m.group(4)])
            if not sgcolor[0]:
                sgcolor[0] = bgcolor
        if m.group(7):
            sgtitle.append(m.group(7))

    m = re.search('((arr[0-9]+)?([rgbycp])?(t[0-9]+)?(start|end)([\'\"].*[\'\"])?)?', k)
    if m.group(1):
        if m.group(5) == "start":
            penwidth = 5 if not m.group(4) else int(m.group(4)[1:])
            arrcolor = arrcolors["d"] if not m.group(3) else arrcolors[m.group(3)]
            arrlabel = "label=<<FONT COLOR=\"%s\">%s</FONT>> " % (fontcolor['r'], m.group(6).strip().strip("\'\"")) if m.group(6) else ""
            arrlines.append([m.group(2)[3:], [tonode], "[minlen=\"0.1\" maxlen=\"0.1\" dir=\"forward\" arrowtail=\"none\" arrowhead=\"vee\" arrowsize=\"2\" style=\"dashed\" constraint=\"false\" color=\"%s\" arrowsize=\"%f\" penwidth=\"%i\" %s]" % (arrcolor, math.sqrt(penwidth/2), penwidth, arrlabel.replace(';', '<BR/>'))])
        elif m.group(5) == "end":
            arrend.update({m.group(2)[3:] : tonode})

    m = re.search('(edg)?([rgbycp])?(t[0-9]+)?([sdtl])?([amovx])?([\'\"].*[\'\"])?([he])?', k)
    if m.group(1):
        if m.group(2): edgecolor.append("%s" % (edgecolors[m.group(2)]))
        if m.group(3): edgethick.append("arrowsize=\"%f\" penwidth=\"%i\"" \
                % (math.sqrt(int(m.group(3)[1:])/2), int(m.group(3)[1:])))
        elif not m.group(3): edgethick.append("arrowsize=\"%f\" penwidth=\"%i\"" \
                % (math.sqrt(5/2), 5))
        if m.group(4): edgestyle.append("style=\"%s\"" % (edgestyles[m.group(4)]))
        if m.group(5): edgend.append("arrowhead=\"%s\"" % (edgeends[m.group(5)]))
        if m.group(7) and m.group(6):
            edgelabeltype = m.group(7)
            if edgelabeltype == 'h':
                edglabel.append("labelfloat=\"true\" labeldistance=\"6\" headlabel=<<FONT COLOR=\"%s\">%s</FONT>>" % (fontcolor['r'], m.group(6).strip().strip("\"").replace(';', '<BR/>')))
            elif edgelabeltype == 'e':
                edglabel.append("labelfloat=\"true\" labeldistance=\"6\" taillabel=<<FONT COLOR=\"%s\">%s</FONT>>" % (fontcolor['r'], m.group(6).strip().strip("\"").replace(';', '<BR/>')))
        elif m.group(6): edglabel.append("label=<<FONT COLOR=\"%s\">%s</FONT>>" % (fontcolor['r'], m.group(6).strip().strip("\"").replace(';', '<BR/>')))


def ParseOtlname(keyword, line):
    m = re.search("(%s[ ]*=[ ]*)(\".*\")[ ]*" % (keyword), line)
    if m is None:
        m = re.search(r"(%s[ ]*=[ ]*)([\w/.\-~_]*)[ ]*" % (keyword), line)

    return m.group(2)

def ParseFnameLine(keyword, line):
    global notitle

    m = re.search("(%s[ ]*=[ ]*)(\".*\")[ ]*(notitle)?" % (keyword), line)
    if m is None:
        m = re.search(r"(%s[ ]*=[ ]*)([\w/.\-~_]*)[ ]*(notitle)?" % (keyword), line)
        if m.group(3):
            notitle = True
    else:
        if m.group(3):
            notitle = True

    return m.group(2)

def ParseInlineAttrLine(keyword, line):
    m = re.search(r"%s[ ]*=[ ]*(\"[^\"]*\"|'[^']*'|[^\s]+)" % (keyword), line)
    if not m:
        return None
    return m.group(1).strip().strip("\"'")


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

    global dotbuf, title, notitle, montagetitle, bgcolor
    jpgname, dotname = "", ""

    tabnum = lines[0].count("\t")

    m = re.search(r'(\t|#) (.*)', lines[0])
    title = m.group(2)

    # bgcolor can be specified on the same line as fname. Reset per map.
    bgcolor = "#efefef"
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
            vrbt = False
            draw = False

            if "verbatim" in nextline or "verbat" in nextline:
                vrbt = True

            if "draw" in nextline:
                draw = True

            if "textleft" in nextline:
                textleft = True
            else:
                textleft = False

            if not vrbt and not draw and ("`" in label or "*" in label):
                label = ApplyInlineBacktickBold(label)

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
                    if i.find(";") > 0:
                        labelhtml[j] = ConvertLinebreakMarkers(i)

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

            if ntype != "img":
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
                    print(e, labelhtml[i])

            wordcolor, wordfsize, wordfstyle = [], [], []
            linecolor, linefsize, linefstyle = [], [], []
            linedate = []
            sgcolor, sgtitle, sgstyle = [], [], []
            edgecolor, edgestyle, edgend, edgethick, edglabel = [], [], [], [], []
            symbcolor, symbsize, symblist = [], [], []

            fromnode = rootnodename
            for i in range(0, level - 1):
                fromnode += "%s" % ("{:=02}".format(nodelevel[i] - 1))
            tonode = fromnode + "%s" % ("{:=02}".format(nodelevel[level - 1]))

            if nextline.find("#") == -1 and ntype != "img":
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
                    if k == "textleft":
                        continue
                    resolved_ntype = ResolveColorNodeTypeToken(k)
                    if resolved_ntype and resolved_ntype not in set(["verbatim", "verbat", "draw"]):
                        ntype = resolved_ntype
                    else:
                        ParseAttributeLine(k, tonode, \
                                wordcolor, wordfsize, wordfstyle, \
                                linecolor, linefsize, linefstyle, \
                                arrlines, arrend,\
                                sgcolor, sgtitle, sgstyle, \
                                edgecolor, edgestyle, edgend, edgethick, edglabel,\
                                symbcolor, symbsize, linedate)

                    if k.find("=") > 0:
                        m = re.match(r"([\W\w]*)(?:=)(.*)", k)
                        tokval = [m.group(1), m.group(2)]
                        if tokval[0] == "img":
                            labelhtml.insert(len(labelhtml) - 1, "</TD></TR><TR><TD COLSPAN=\"1\" CELLPADDING=\"0\" BORDER=\"1\"><IMG SRC=\"" + GenImgPath(tokval[1].strip()) + "\"/>")
                            ntype = "imgil"
                        elif tokval[0] == "symb" and ntype != "imgil":
                            symblist = ResolveSymbolNames(tokval[1])
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
                SkipUnscopedWords(wordfsize, s=wordskip)
                SkipUnscopedWords(wordcolor, s=wordskip)
                SkipUnscopedWords(wordfstyle, s=wordskip)
                if linecolor and not linecolor[0][0] == 0:
                    SkipPositive(linecolor, s=1)
                if linefsize and not linefsize[0][0] == 0:
                    SkipPositive(linefsize, s=1)
                if linefstyle and not linefstyle[0][0] == 0:
                    SkipPositive(linefstyle, s=1)

            if symblist:
                SkipUnscopedWords(wordfsize, s=len(symblist))
                SkipUnscopedWords(wordcolor, s=len(symblist))
                SkipUnscopedWords(wordfstyle, s=len(symblist))

            if ntype == "term" or ntype == "link":
                SkipUnscopedWords(wordfsize, s=2)
                SkipUnscopedWords(wordcolor, s=2)
                SkipUnscopedWords(wordfstyle, s=2)

            if ntype in set(["title", "quest", "date", "impor", "impog", "impob"]) or\
                    (ntype != "img" and "FontAwesome" in labelhtml[1]):
                if wordcolor: SkipPositiveLineScopedWords(wordcolor, lsinw=1)
                if wordfsize: SkipPositiveLineScopedWords(wordfsize, lsinw=1)
                if wordfstyle: SkipPositiveLineScopedWords(wordfstyle, lsinw=1)
                if linedate: SkipPositive(linedate, s=1)
                if linecolor and not linecolor[0][0] == 0:
                    SkipPositive(linecolor, s=1)
                if linefsize and not linefsize[0][0] == 0:
                    SkipPositive(linefsize, s=1)
                if linefstyle and not linefstyle[0][0] == 0:
                    SkipPositive(linefstyle, s=1)

            if ntype == "term" or ntype == "link":
                if linecolor and not linecolor[0][0] == 0:
                    SkipPositive(linecolor, s=1)
                if linefsize and not linefsize[0][0] == 0:
                    SkipPositive(linefsize, s=1)
                if linefstyle and not linefstyle[0][0] == 0:
                    SkipPositive(linefstyle, s=1)

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
                    linefsize, wordfstyle, linefstyle, linedate, \
                    sgcolor[0] if sgcolor else None, \
                    sgtitle[0] if sgtitle else None, \
                    sgstyle[0] if sgstyle else None, \
                    vrbt, draw, textleft)

            nodelevel[level - 1] += 1

            for i in range(level, len(nodelevel) - 1):
                nodelevel[i] = 1

    for p in tree.postorder():
        t = p.getype()
        if p.getype() != "root":
            if p.is_leaf() is not True:
                if t in set(["cred", "cgreen", "ccyan", "cblue", "cpink", "cyello", "corang", "cblack", "cgrey"]):
                    s = p.element().replace("shape=box", "margin=\"0.2,0.3\" shape=box fontsize=\"%s\"" % (fontsize['l']) + "\n")
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


def PostAttrProcLabel(label, ntype, vrbt, draw, textleft=False):
    if ntype == "saying":
        label.insert(0, "<I>")
        label.insert(len(label), "</I>")
    if ntype == "check" or ntype == "todo":
        label.insert(0, "<B>")
        label.insert(len(label), "</B>")
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
    if ntype == "list" or textleft:
        for i in range(len(label)):
            label[i] = label[i].replace("<TD", "<TD ALIGN=\"left\"")
    if not vrbt and not draw:
        merged = "".join(label)
        merged = re.sub(r"<TR><TD(?: ALIGN=\"left\")?>----(?:&nbsp;)?</TD></TR>", "<HR/>", merged)
        merged = re.sub(r"<TR><TD(?: ALIGN=\"left\")?>---(?:&nbsp;)?</TD></TR>", "<HR/>", merged)
        merged = re.sub(r";?&nbsp;----</TD></TR>", "</TD></TR><HR/>", merged)
        merged = re.sub(r";?&nbsp;---</TD></TR>", "</TD></TR><HR/>", merged)
        merged = re.sub(r";?&nbsp;<HR/><TR><TD></TD></TR>", "</TD></TR><HR/>", merged)
        label[:] = [merged]


def PreAttrProcLabel(label, ntype):
    btype = ResolveBaseNodeTypeToken(ntype)

    if btype == "title":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"25\">" + fontawesome.symb["info-circle"] + "</FONT></TD></TR><TR><TD>")
    elif btype == "date":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"25\">" + fontawesome.symb["clock-o"] + "</FONT></TD></TR><TR><TD>")
    elif btype == "quest":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"25\">" + fontawesome.symb["question-circle"] + "</FONT></TD></TR><TR><TD>")
    elif btype == "answer":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"25\">" + fontawesome.symb["reply"] + "</FONT></TD></TR><TR><TD>")
    elif btype == "saying":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"15\">" + fontawesome.symb["quote-left"] + "  " + fontawesome.symb["quote-right"] + "</FONT></TD></TR><TR><TD>")
    elif btype == "impor" or btype == "impog" or btype == "impob":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"25\">" + fontawesome.symb["warning"] + "</FONT></TD></TR><TR><TD>")
    elif btype == "todo":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"25\">" + fontawesome.symb["tasks"] + "</FONT></TD></TR><TR><TD>")
    elif btype == "term":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"%s\" POINT-SIZE=\"1\">" % (fontcolor['k']) + fontawesome.symb["terminal"] + "</FONT></TD></TR><TR><TD>")
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"%s\" POINT-SIZE=\"15\">" % (fontcolor['k'])+ fontawesome.symb["desktop"] + "</FONT>&nbsp;<FONT FACE=\"FontAwesome\" COLOR=\"%s\" POINT-SIZE=\"20\">" % (fontcolor['k']) + fontawesome.symb["terminal"] + "</FONT></TD></TR><TR><TD>")
    elif btype == "link":
        label.insert(1, "<FONT FACE=\"FontAwesome\" COLOR=\"#B32727\" POINT-SIZE=\"25\">" + fontawesome.symb["link"] + "</FONT></TD></TR><TR><TD>")


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

    j = 0
    while j < len(linesall) - 1:
        nextline = linesall[j + 1]
        level = linesall[j][:ParLoc(linesall[j])].count("\t")

        if re.search(r"\t(:|;|\|)\s*fname", nextline):
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
                                    and not re.search(r"\t\s*[a-zA-Z0-9]\s*", linesall[j]):
                                if "\t:" in linesall[j]:
                                    v.append(linesall[j].lstrip("\t:").rstrip())
                                elif "\t|" in linesall[j]:
                                    v.append(linesall[j].lstrip("\t|").rstrip())
                                elif "\t;" in linesall[j]:
                                    v.append(linesall[j].lstrip("\t;").rstrip())
                                v[-1] = NormalizeVerbatimWhitespace(v[-1])
                                v[-1] = v[-1].replace("&", "&amp;")
                                v[-1] = v[-1].replace("<", "&lt;")
                                v[-1] = v[-1].replace(">", "&gt;")
                                if "`" in v[-1] or "*" in v[-1]:
                                    v[-1] = ApplyInlineBacktickBold(v[-1], allow_linebreak=True)
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
