def BuildNodeRefs(rootnodename, nodelevel, level):
    fromnode = rootnodename
    for index in range(0, level - 1):
        fromnode += "%s" % ("{:=02}".format(nodelevel[index] - 1))

    tonode = fromnode + "%s" % ("{:=02}".format(nodelevel[level - 1]))
    tabs = "\t" * (level + 1)
    return fromnode, tonode, tabs


def ResolveEdgeType(ntype, edgetype):
    if ntype in edgetype:
        return edgetype[ntype]

    match = re.match(r"^([a-z]+)-?[0-9]+$", ntype)
    if match:
        return edgetype.get(match.group(1))

    return None


def AppendNodeEdge(edge, tabs, fromnode, tonode, ntype, edgeattrs, edgetype):
    resolved_edgetype = ResolveEdgeType(ntype, edgetype)
    if resolved_edgetype and not edgeattrs:
        edge.append("%s%s:e -> %s:w[%s];\n" % (tabs, fromnode, tonode, resolved_edgetype))
    elif edgeattrs:
        edge.append("%s%s:e -> %s:w[%s];\n" % (tabs, fromnode, tonode, edgeattrs))
    else:
        edge.append("%s%s:e -> %s:w;\n" % (tabs, fromnode, tonode))


def EmitTreeNodes(tree, nodetype, fontsize):
    chunks = []

    for node in tree.postorder():
        ntype = node.getype()
        if ntype == "root":
            continue

        if not node.is_leaf():
            if ntype in {"cred", "cgreen", "ccyan", "cblue", "cpink", "cyello", "corang", "cblack", "cgrey"}:
                rendered = node.element().replace(
                    "shape=box",
                    "margin=\"0.2,0.3\" shape=box fontsize=\"%s\"" % (fontsize["l"]) + "\n",
                )
                chunks.append(rendered)
            else:
                original_ntype = ntype
                if ntype == "def":
                    node.setype("node")
                rendered = node.element() + "\n"
                node.setype(original_ntype)
                if ntype not in ["img", "imgil"]:
                    rendered = rendered.replace("shape=box", "shape=box margin=\"0.2,0.2\"")
                chunks.append(rendered)
        else:
            chunks.append(node.element() + "\n")

    return "".join(chunks)


def FinalizeEdges(edge, arrlines, arrend, subgraph_depth=None):
    finalized = list(edge)
    for arrline in arrlines:
        arrline[1].append(arrend[arrline[0]])
        attrs = arrline[2]
        if subgraph_depth is None:
            attrs = attrs.replace(
                "[",
                "[ltail=\"%s\" lhead=\"%s\" "
                % (arrline[1][0].replace("node", "cluster"), arrline[1][1].replace("node", "cluster")),
            )
        finalized.append(
            "%s -> %s %s;\n"
            % (
                arrline[1][0],
                arrline[1][1],
                attrs,
            )
        )
    return list(reversed(finalized))
import re


class Tree:
    class Node:
        def __init__(self, tree, nodename, label=None, tabs="", ntype=None, parent=None, wordcolor=None, linecolor=None, wordfsize=None, linefsize=None, wordfstyle=None, linefstyle=None, linefont=None, linedate=None, verbatim=False, draw=False, fontname=None, bgcolor=None, fgcolor=None, child_subgraphs=None, bordercolor=None, borderwidth=None, borderstyle=None):
            self._tree = tree
            self._ntype = ntype
            self._nodename = nodename
            self._label = label if label is not None else []
            self._tabs = tabs
            self._parent = parent
            self._child = []
            self._wordcolor = wordcolor if wordcolor is not None else []
            self._linecolor = linecolor if linecolor is not None else []
            self._linefsize = linefsize if linefsize is not None else []
            self._linefstyle = linefstyle if linefstyle is not None else []
            self._linefont = linefont if linefont is not None else []
            self._wordfsize = wordfsize if wordfsize is not None else []
            self._wordfstyle = wordfstyle if wordfstyle is not None else []
            self._linedate = linedate if linedate is not None else []
            self._verbatim = verbatim
            self._draw = draw
            self._fontname = fontname
            self._bgcolor = bgcolor
            self._fgcolor = fgcolor
            self._child_subgraphs = child_subgraphs
            self._bordercolor = bordercolor
            self._borderwidth = borderwidth
            self._borderstyle = borderstyle

        def _apply_fontname(self, attrs):
            if not self._fontname:
                return attrs
            if "fontname=" in attrs:
                return re.sub(r'fontname="[^"]*"', 'fontname="%s"' % self._fontname, attrs, count=1)
            return attrs + ' fontname="%s"' % self._fontname

        def _apply_bgcolor(self, attrs):
            if not self._bgcolor:
                return attrs
            if "fillcolor=" in attrs:
                return re.sub(r'fillcolor="[^"]*"', 'fillcolor="%s"' % self._bgcolor, attrs, count=1)
            if "style=" not in attrs:
                attrs += ' style="filled"'
            return attrs + ' fillcolor="%s"' % self._bgcolor

        def _apply_fgcolor(self, attrs):
            if not self._fgcolor:
                return attrs
            if "fontcolor=" in attrs:
                return re.sub(r'fontcolor="[^"]*"', 'fontcolor="%s"' % self._fgcolor, attrs, count=1)
            return attrs + ' fontcolor="%s"' % self._fgcolor

        def _apply_bordercolor(self, attrs):
            bordercolor = self._bordercolor or self._tree.default_bordercolor
            if not bordercolor:
                return attrs
            if re.search(r'(^|\s)color=', attrs):
                return re.sub(r'(^|\s)color="?[^"\s]*"?', r'\1color="%s"' % bordercolor, attrs, count=1)
            return attrs + ' color="%s"' % bordercolor

        def _apply_borderwidth(self, attrs):
            borderwidth = self._borderwidth or self._tree.default_borderwidth
            if not borderwidth:
                return attrs
            if "penwidth=" in attrs:
                return re.sub(r'penwidth="?[^"\s]*"?', 'penwidth="%s"' % borderwidth, attrs, count=1)
            return attrs + ' penwidth="%s"' % borderwidth

        def _apply_borderstyle(self, attrs):
            borderstyle = self._borderstyle or self._tree.default_borderstyle
            if not borderstyle:
                return attrs
            if "style=" in attrs:
                match = re.search(r'style="([^"]*)"', attrs)
                if match:
                    styles = [style.strip() for style in match.group(1).split(",") if style.strip()]
                    styles = [style for style in styles if style not in {"solid", "dashed", "dotted"}]
                    styles.append(borderstyle)
                    return attrs[:match.start()] + 'style="%s"' % ",".join(styles) + attrs[match.end():]
            return attrs + ' style="%s"' % borderstyle

        def _apply_node_overrides(self, attrs):
            attrs = self._apply_fontname(attrs)
            attrs = self._apply_bgcolor(attrs)
            attrs = self._apply_fgcolor(attrs)
            attrs = self._apply_bordercolor(attrs)
            attrs = self._apply_borderwidth(attrs)
            return self._apply_borderstyle(attrs)

        def element(self):
            if "sgwrap" in self._ntype:
                return self._tabs + "".join(self._label)
            elif self._verbatim:
                if self._ntype == "def":
                    attrs = self._apply_node_overrides(self._tree.nodetype["verbatim"])
                    return "\t" + self._tabs + self._nodename + "[%s label=<%s>];" % (attrs, "".join(self._label))
                else:
                    fillcolor = self._tree.resolve_verbatim_fill_color_token(self._ntype, self._tree.vrbtcolors)
                    if not fillcolor:
                        fillcolor = self._tree.vrbtcolors["def"]
                    attrs = self._apply_node_overrides(self._tree.nodetype["verbatim"].replace(self._tree.vrbtcolors["def"], fillcolor))
                    return "\t" + self._tabs + self._nodename + "[%s label=<%s>];" % (attrs, "".join(self._label))
            elif self._draw:
                if self._ntype == "def":
                    attrs = self._apply_node_overrides(self._tree.nodetype["draw"])
                    return "\t" + self._tabs + self._nodename + "[%s label=<%s>];" % (attrs, "".join(self._label))
                else:
                    fillcolor = self._tree.resolve_verbatim_fill_color_token(self._ntype, self._tree.vrbtcolors)
                    if not fillcolor:
                        fillcolor = self._tree.vrbtcolors["cwhite"]
                    attrs = self._apply_node_overrides(self._tree.nodetype["draw"].replace(self._tree.vrbtcolors["cwhite"], fillcolor))
                    return "\t" + self._tabs + self._nodename + "[%s label=<%s>];" % (attrs, "".join(self._label))
            else:
                attrs = self._apply_node_overrides(self._tree.nodetype[self._ntype])
                return "\t" + self._tabs + self._nodename + "[%s label=<%s>];" % (attrs, "".join(self._label))

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
            return self.numchilds() == 0

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
            for value in self._linefstyle:
                self._lineattr("<TD>", "<TD><", [value], "</%s>" % (value[1]))

        def linefont(self):
            self._lineattr("<TD>", "<TD><FONT FACE=", self._linefont, "</FONT>")

        def colorifylines(self):
            for value in self._linecolor:
                if value[2]:
                    self._lineattr("<TD>", "<TD><B><FONT COLOR=", [value], "</FONT></B>")
                else:
                    self._lineattr("<TD>", "<TD BGCOLOR=", [value])

        def linedate(self):
            if len(self._linedate) == 0:
                return

            self._label = "<SEP>".join(self._label)
            self._label = self._label.split("</TD></TR><TR>")

            for value in self._linedate:
                _, scoped_indexes = self._line_fragment_indexes_for_attr(value, self._label)
                if not scoped_indexes:
                    continue
                li = self._resolve_line_sel(int(value[0]), len(scoped_indexes))
                if li < 1 or li > len(scoped_indexes):
                    continue
                target_idx = scoped_indexes[li - 1]

                deco = "<TD><FONT COLOR=\"%s\"><I><FONT FACE=\"FontAwesome\" POINT-SIZE=\"18\">%s</FONT>&nbsp;" % (self._tree.fontcolor["b"], self._tree.fontawesome_symb["calendar"])
                self._label[target_idx] = self._label[target_idx].replace("<TD>", deco, 1)
                if "</TD>" in self._label[target_idx]:
                    self._label[target_idx] = self._label[target_idx].replace("</TD>", "</I></FONT></TD>", 1)
                else:
                    self._label[target_idx] = self._label[target_idx] + "</I></FONT>"

            for index in range(len(self._label) - 1):
                self._label[index] = self._label[index] + "</TD></TR><TR>"

            self._label = "".join(self._label)
            self._label = self._label.split("<SEP>")

        def _attr_meta(self, item):
            for part in reversed(item):
                if isinstance(part, dict):
                    return part
            return {}

        def _is_header_attr(self, item):
            return bool(self._attr_meta(item).get("header"))

        def _line_fragment_indexes_for_attr(self, item, fragments=None):
            if self._is_header_attr(item):
                return self._header_line_fragment_indexes(fragments)
            return self._scoped_line_fragment_indexes(fragments)

        def _line_word_indexes_for_attr(self, item):
            lmeta = item[2] if len(item) > 2 and isinstance(item[2], dict) else {}
            if lmeta.get("header"):
                return self._header_line_word_indexes()
            return self._scoped_line_word_indexes()

        def _remove_verbatim_body_boundary(self):
            if "__GVMM_BODY_BOUNDARY__" not in "".join(self._label):
                return
            fragments = "<SEP>".join(self._label).split("</TD></TR><TR>")
            fragments = [
                fragment
                for fragment in fragments
                if "__GVMM_BODY_BOUNDARY__" not in fragment
            ]
            for index in range(len(fragments) - 1):
                fragments[index] = fragments[index] + "</TD></TR><TR>"
            self._label = "".join(fragments).split("<SEP>")

        def _first_header_line_has_attr(self, attrlists):
            for attrlist in attrlists:
                for item in attrlist or []:
                    if not self._is_header_attr(item):
                        continue
                    fragments, indexes = self._header_line_fragment_indexes()
                    if not indexes:
                        continue
                    li = self._resolve_line_sel(int(item[0]), len(indexes))
                    if li == 1:
                        return True
            return False

        def _apply_default_verbatim_header_style(self, attrlists):
            if not (self._verbatim or self._draw):
                return
            if self._first_header_line_has_attr(attrlists):
                return

            fragments, indexes = self._header_line_fragment_indexes()
            if not indexes:
                return

            self._label = "<SEP>".join(self._label)
            self._label = self._label.split("</TD></TR><TR>")
            target_idx = indexes[0]
            self._label[target_idx] = self._label[target_idx].replace("<TD>", "<TD><B><U><FONT>", 1)
            if "</TD>" in self._label[target_idx]:
                self._label[target_idx] = self._label[target_idx].replace("</TD>", "</FONT></U></B></TD>", 1)
            else:
                self._label[target_idx] += "</FONT></U></B>"
            for index in range(len(self._label) - 1):
                self._label[index] = self._label[index] + "</TD></TR><TR>"
            self._label = "".join(self._label).split("<SEP>")

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
                del line_indexes[0]

            if self._verbatim or self._draw:
                boundary_index = self._body_boundary_line_index()
                if boundary_index is not None:
                    line_indexes = line_indexes[boundary_index + 1:]
                elif line_indexes:
                    del line_indexes[0]
                while line_indexes and not line_indexes[0]:
                    del line_indexes[0]
                while line_indexes and not line_indexes[-1]:
                    del line_indexes[-1]

            return line_indexes

        def _header_line_word_indexes(self):
            line_indexes = self._label_line_word_indexes()

            while line_indexes and not line_indexes[0]:
                del line_indexes[0]

            if not (self._verbatim or self._draw):
                return []

            boundary_index = self._body_boundary_line_index()
            if boundary_index is not None:
                line_indexes = line_indexes[:boundary_index]
            else:
                line_indexes = line_indexes[:1]

            while line_indexes and not line_indexes[0]:
                del line_indexes[0]
            while line_indexes and not line_indexes[-1]:
                line_indexes.pop()
            return line_indexes

        def _scoped_line_fragment_indexes(self, fragments=None):
            def has_visible_content(fragment):
                text = re.sub(r"<[^>]+>", "", fragment)
                text = text.replace("&nbsp;", "").strip()
                text = text.replace("<", "").replace(">", "").strip()
                return bool(text)

            if fragments is None:
                fragments = "<SEP>".join(self._label).split("</TD></TR><TR>")

            if self._verbatim or self._draw:
                indexes = list(range(len(fragments)))
                boundary_index = self._body_boundary_fragment_index(fragments)
                if boundary_index is not None:
                    indexes = [index for index in indexes if index > boundary_index]
                elif indexes:
                    del indexes[0]
                while indexes and not has_visible_content(fragments[indexes[0]]):
                    del indexes[0]
                while indexes and not has_visible_content(fragments[indexes[-1]]):
                    indexes.pop()
            else:
                indexes = [idx for idx, fragment in enumerate(fragments) if has_visible_content(fragment)]

            return fragments, indexes

        def _header_line_fragment_indexes(self, fragments=None):
            def has_visible_content(fragment):
                text = re.sub(r"<[^>]+>", "", fragment)
                text = text.replace("&nbsp;", "").strip()
                text = text.replace("<", "").replace(">", "").strip()
                return bool(text)

            if fragments is None:
                fragments = "<SEP>".join(self._label).split("</TD></TR><TR>")

            if not (self._verbatim or self._draw):
                return fragments, []

            boundary_index = self._body_boundary_fragment_index(fragments)
            if boundary_index is not None:
                indexes = list(range(boundary_index))
            else:
                indexes = list(range(1))

            indexes = [idx for idx in indexes if idx < len(fragments) and has_visible_content(fragments[idx])]
            return fragments, indexes

        def _body_boundary_fragment_index(self, fragments):
            for index, fragment in enumerate(fragments):
                if "__GVMM_BODY_BOUNDARY__" in fragment:
                    return index
            return None

        def _body_boundary_line_index(self):
            for index, row in enumerate(self._label_line_word_indexes()):
                for token_index in row:
                    if "__GVMM_BODY_BOUNDARY__" in self._label[token_index]:
                        return index
            return None

        def _wordattr(self, value, sattr, eattr=None):
            if len(value) > 0:
                prevnbsp = [j for j in range(2, len(self._label)) if "nbsp" in self._label[j]]

                for token in self._label[2:]:
                    if "nbsp" in token:
                        self._label.remove(token)

                for item in value:
                    target_idx = int(item[0])
                    if type(item[2]) == dict and item[2]["lineskip"]:
                        line_indexes = self._line_word_indexes_for_attr(item)
                        if not line_indexes:
                            continue
                        lskip = self._resolve_line_sel(item[2]["lineskip"], len(line_indexes))
                        scoped_words = line_indexes[lskip - 1]
                        if not scoped_words:
                            continue

                        wsel = int(item[0])
                        if wsel < 0:
                            wsel = len(scoped_words) + wsel + 1
                        if wsel < 1:
                            wsel = 1
                        if wsel > len(scoped_words):
                            wsel = len(scoped_words)

                        target_idx = scoped_words[wsel - 1]

                    if target_idx < 0 or target_idx >= len(self._label):
                        continue

                    if item[1] in {"U", "B", "S", "I"}:
                        self._label[target_idx] = sattr + "%s>" % item[1] + self._label[target_idx]
                        eattr = "</%s>" % (item[1])
                    else:
                        self._label[target_idx] = sattr + "\"%s\">" % item[1] + self._label[target_idx]

                    if "</TD></TR><TR>" in self._label[target_idx]:
                        self._label[target_idx] = self._label[target_idx].replace("</TD></TR><TR>", eattr + "</TD></TR><TR>")
                    else:
                        self._label[target_idx] = self._label[target_idx] + eattr

                for item in prevnbsp:
                    self._label.insert(item, "&nbsp;")

        def _lineattr(self, fsattr, tsattr, value, eattr=None):
            def is_separator_row(fragment):
                text = re.sub(r"<[^>]+>", "", fragment)
                text = text.replace("&nbsp;", "").strip()
                return text in {"---", "----"}

            def replace_td(fragment, replacement):
                return re.sub(r"<TD(?: ALIGN=\"left\")?>", replacement, fragment, count=1)

            if len(value) > 0:
                if value[0][0] == 0:
                    if "FontAwesome" not in self._label[1]:
                        self._label = "<SEP>".join(self._label)
                        self._label = self._label.split("</TD></TR><TR>")
                        for index in range(len(self._label)):
                            if is_separator_row(self._label[index]):
                                continue
                            self._label[index] = replace_td(
                                self._label[index],
                                "%s\"%s\">" % (tsattr, value[0][1]) if value[0][1] not in {"U", "B", "S", "I"} else "%s%s>" % (tsattr, value[0][1]),
                            )
                            if eattr and index < len(self._label) - 1:
                                self._label[index] = self._label[index] + eattr
                            elif eattr and index == len(self._label) - 1:
                                self._label[index] = self._label[index].replace("</TD>", eattr + "</TD>")
                        for index in range(len(self._label) - 1):
                            self._label[index] = self._label[index] + "</TD></TR><TR>"
                        self._label = "".join(self._label)
                        self._label = self._label.split("<SEP>")
                    else:
                        first = self._label[0]
                        if eattr:
                            for index in range(2, len(self._label)):
                                self._label[index] = self._label[index].replace("</TD>", eattr + "</TD>")
                        self._label = "<SEP>".join(self._label[1:])
                        self._label = re.sub(
                            r"<TD(?: ALIGN=\"left\")?>",
                            "%s\"%s\">" % (tsattr, value[0][1]) if value[0][1] not in {"U", "B", "S", "I"} else "%s%s>" % (tsattr, value[0][1]),
                            self._label,
                        )
                        self._label = self._label.split("<SEP>")
                        self._label.insert(0, first)
                else:
                    self._label = "<SEP>".join(self._label)
                    self._label = self._label.split("</TD></TR><TR>")
                    for item in value:
                        _, scoped_indexes = self._line_fragment_indexes_for_attr(item, self._label)
                        if not scoped_indexes:
                            continue
                        li = self._resolve_line_sel(int(item[0]), len(scoped_indexes))
                        if li < 1 or li > len(scoped_indexes):
                            continue
                        target_idx = scoped_indexes[li - 1]
                        self._label[target_idx] = replace_td(
                            self._label[target_idx],
                            "%s\"%s\">" % (tsattr, item[1]) if item[1] not in {"U", "B", "S", "I"} else "%s%s>" % (tsattr, item[1]),
                        )
                        if eattr and target_idx < len(self._label) - 1:
                            self._label[target_idx] = self._label[target_idx] + eattr
                        elif eattr and target_idx == len(self._label) - 1:
                            self._label[target_idx] = self._label[target_idx].replace("</TD>", eattr + "</TD>")
                    for index in range(len(self._label) - 1):
                        self._label[index] = self._label[index] + "</TD></TR><TR>"
                    self._label = "".join(self._label)
                    self._label = self._label.split("<SEP>")

    def __init__(self, nodetype, vrbtcolors, fontcolor, font, fontsize, fontawesome_symb, resolve_verbatim_fill_color_token, post_attr_proc_label, subgraph_depth=None, default_sgmargin="8"):
        self.root = None
        self.size = 0
        self.nodetype = nodetype
        self.vrbtcolors = vrbtcolors
        self.fontcolor = fontcolor
        self.font = font
        self.fontsize = fontsize
        self.fontawesome_symb = fontawesome_symb
        self.resolve_verbatim_fill_color_token = resolve_verbatim_fill_color_token
        self.post_attr_proc_label = post_attr_proc_label
        self.subgraph_depth = subgraph_depth
        self.default_sgmargin = default_sgmargin
        self.default_bordercolor = None
        self.default_borderwidth = None
        self.default_borderstyle = None

    def _subgraphs_enabled_for_tabs(self, tabs, parent=None):
        if parent is not None and getattr(parent, "_child_subgraphs", None) is False:
            return False
        if self.subgraph_depth is None:
            return True
        node_depth = max(0, tabs.count("\t") - 1)
        return node_depth <= self.subgraph_depth

    def addroot(self, e):
        self.root = self.Node(self, e, ntype="root")
        return self.root

    def _addchild(self, e, p):
        c = self.Node(self, e)
        c._parent = p
        p._child.append(c)
        return c

    def addchild(self, e, tabs, ntype, label, p):
        self._addchild(tabs + "subgraph cluster%s {" % e.replace("node", "") + tabs + "\t" + "style = invis;", p)
        c = self._addchild("\t" + tabs + e, p)
        self._addchild(tabs + "}", p)
        return c

    def _addchild_rev(self, nodename, label, tabs, ntype, p, wc=None, lc=None, ws=None, ls=None, wf=None, lf=None, lfont=None, ld=None, vrbt=False, draw=False, fontname=None, bgcolor=None, fgcolor=None, child_subgraphs=None, bordercolor=None, borderwidth=None, borderstyle=None):
        if child_subgraphs is None and getattr(p, "_child_subgraphs", None) is False:
            child_subgraphs = False
        c = self.Node(self, nodename, label, tabs, ntype, p, wc, lc, ws, ls, wf, lf, lfont, ld, vrbt, draw, fontname, bgcolor, fgcolor, child_subgraphs, bordercolor, borderwidth, borderstyle)
        c._parent = p
        p._child.insert(0, c)
        return c

    def addchild_rev(self, nodename, tabs, ntype, label, p, wordcolor=None, linecolor=None, wordfsize=None, linefsize=None, wordfstyle=None, linefstyle=None, linefont=None, linedate=None, sgcolor=None, sgtitle=None, sgstyle=None, vrbt=False, draw=False, textleft=False, fontname=None, bgcolor=None, fgcolor=None, child_subgraphs=None, sgmargin=None, bordercolor=None, borderwidth=None, borderstyle=None):
        sgattr = ""
        enable_subgraphs = self._subgraphs_enabled_for_tabs(tabs, p)
        sgmargin = sgmargin if sgmargin is not None else self.default_sgmargin
        margin_attr = tabs + "\t" + "margin = \"%s\";\n" % sgmargin if sgmargin else ""
        if enable_subgraphs and sgcolor and sgcolor[0] == "s":
            self._addchild_rev("", ["}"], tabs, "sgwrap", p)
        if enable_subgraphs:
            self._addchild_rev("", ["}"], tabs, "sgwrap", p)
        if enable_subgraphs and sgtitle:
            self._addchild_rev("", ["label = <<TABLE CELLBORDER=\"0\" CELLPADDING=\"3\" CELLSPACING=\"3\" BORDER=\"0\"><TR><TD BGCOLOR=\"#E9ED5F\" COLOR=\"#000000\"><U>%s</U></TD></TR></TABLE>>" % (sgtitle)], tabs, "sgwrap", p)
        c = self._addchild_rev(nodename, label, tabs, ntype, p, wordcolor, linecolor, wordfsize, linefsize, wordfstyle, linefstyle, linefont, linedate, vrbt, draw, fontname, bgcolor, fgcolor, child_subgraphs, bordercolor, borderwidth, borderstyle)
        c.wordfsize()
        c.wordfstyle()
        c.linefsize()
        c.colorifywords()
        c.linefstyle()
        c.linefont()
        c.colorifylines()
        c.linedate()
        c._apply_default_verbatim_header_style((wordcolor, wordfsize, wordfstyle, linecolor, linefsize, linefstyle, linefont, linedate))
        c._remove_verbatim_body_boundary()

        self.post_attr_proc_label(c._label, ntype, vrbt, draw, textleft)

        if enable_subgraphs and sgcolor and sgcolor[0] == "#":
            sgattr = margin_attr + "style = \"%s rounded\";\n" % (sgstyle + "," if sgstyle else "") + tabs + "\t" + "color = \"%s\";\n" % (sgcolor if not sgstyle else "#000000") + tabs + "\t" + "bgcolor = \"%s\"" % (sgcolor)
        else:
            sgattr = margin_attr + "style = invis;"

        if enable_subgraphs and sgtitle:
            self._addchild_rev("", ["fontname = \"%s\";\n" % (self.font["balsamiq"]) + tabs + "\t" + "fontsize = \"%s\";\n" % (self.fontsize["xxl"])], tabs, "sgwrap", p)
        if enable_subgraphs:
            self._addchild_rev("", ["subgraph cluster%s {\n" % nodename.replace("node", "") + tabs + "\t" + sgattr], tabs, "sgwrap", p)
        if enable_subgraphs and sgcolor and sgcolor[0] == "e":
            sgattr = margin_attr + "style = \"%s rounded\";\n" % (sgstyle + "," if sgstyle else "") + tabs + "\t" + "color = \"%s\";\n" % (sgcolor[1:] if not sgstyle else "#000000") + tabs + "\t" + "bgcolor = \"%s\";" % (sgcolor[1:])
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
