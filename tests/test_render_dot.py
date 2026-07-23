import unittest

from graphviz_mindmaps import fontawesome
from graphviz_mindmaps.constants import (
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
from graphviz_mindmaps.model.graph import Tree
from graphviz_mindmaps.parser.outline import ExtractMindmapBlocks
from graphviz_mindmaps.render.label_html import BuildNodeLabelHtml
from graphviz_mindmaps.render.label_html import ApplyInlineBacktickBold
from graphviz_mindmaps.render.label_html import PostAttrProcLabel


class RenderDotNodeAttributeTests(unittest.TestCase):
    def _tree(self, post_attr_proc_label=None):
        return Tree(
            nodetype,
            vrbtcolors,
            fontcolor,
            font,
            fontsize,
            fontawesome.symb,
            lambda token, colors: colors.get(token),
            post_attr_proc_label or (lambda label, ntype, vrbt, draw, textleft: None),
        )

    def _label(self, text):
        return ["<TABLE><TR><TD>%s</TD></TR></TABLE>" % text]

    def test_border_color_does_not_replace_check_fontcolor(self):
        tree = self._tree()
        node = tree.Node(
            tree,
            "node101",
            self._label("check node with custom border"),
            "\t\t",
            "check",
            bordercolor="forestgreen",
            borderwidth="3",
        )

        rendered = node.element()

        self.assertIn('fontcolor="%s"' % fontcolor["def"], rendered)
        self.assertIn('color="forestgreen"', rendered)
        self.assertIn('penwidth="3"', rendered)
        self.assertNotIn('fontcolor="forestgreen"', rendered)

    def test_visual_node_attributes_override_existing_attrs(self):
        tree = self._tree()
        node = tree.Node(
            tree,
            "node101",
            self._label("custom fill text border and font"),
            "\t\t",
            "node",
            fontname="Dejavu Serif",
            bgcolor="#f6fff6",
            fgcolor="#245c2d",
            bordercolor="#45A135",
            borderwidth="2",
            borderstyle="dashed",
        )

        rendered = node.element()

        self.assertIn('fontname="Dejavu Serif"', rendered)
        self.assertIn('fillcolor="#f6fff6"', rendered)
        self.assertIn('fontcolor="#245c2d"', rendered)
        self.assertIn('color="#45A135"', rendered)
        self.assertIn('penwidth="2"', rendered)
        self.assertIn('style="rounded,radial,dashed"', rendered)

    def test_bg_attribute_adds_filled_style_when_base_type_has_no_fill(self):
        tree = self._tree()
        node = tree.Node(
            tree,
            "node101",
            self._label("underlined node with custom fill"),
            "\t\t",
            "def",
            bgcolor="#fff8cc",
        )

        rendered = node.element()

        self.assertIn('style="filled"', rendered)
        self.assertIn('fillcolor="#fff8cc"', rendered)

    def test_border_style_preserves_non_border_styles(self):
        tree = self._tree()
        node = tree.Node(
            tree,
            "node101",
            self._label("todo node with dotted border"),
            "\t\t",
            "todo",
            borderstyle="dotted",
        )

        rendered = node.element()

        self.assertIn('style="filled,diagonals,dotted"', rendered)

    def test_tree_default_border_attributes_apply_to_nodes(self):
        tree = self._tree()
        tree.default_bordercolor = "#446688"
        tree.default_borderwidth = "5"
        tree.default_borderstyle = "dashed"
        node = tree.Node(
            tree,
            "node101",
            self._label("node using default border settings"),
            "\t\t",
            "node",
        )

        rendered = node.element()

        self.assertIn('color="#446688"', rendered)
        self.assertIn('penwidth="5"', rendered)
        self.assertIn('style="rounded,radial,dashed"', rendered)

    def test_explicit_border_attributes_override_tree_defaults(self):
        tree = self._tree()
        tree.default_bordercolor = "#446688"
        tree.default_borderwidth = "5"
        tree.default_borderstyle = "dashed"
        node = tree.Node(
            tree,
            "node101",
            self._label("node using explicit border settings"),
            "\t\t",
            "node",
            bordercolor="#884422",
            borderwidth="2",
            borderstyle="dotted",
        )

        rendered = node.element()

        self.assertIn('color="#884422"', rendered)
        self.assertIn('penwidth="2"', rendered)
        self.assertIn('style="rounded,radial,dotted"', rendered)
        self.assertNotIn('color="#446688"', rendered)
        self.assertNotIn('penwidth="5"', rendered)

    def test_textleft_attribute_aligns_label_cells_left(self):
        tree = self._tree(PostAttrProcLabel)
        root = tree.addroot("node1")

        node = tree.addchild_rev(
            "node101",
            "\t\t",
            "node",
            self._label("left aligned operational note"),
            root,
            textleft=True,
        )

        self.assertIn('<TD ALIGN="left">left aligned operational note', "".join(node._label))

    def test_child_subgraph_attribute_disables_descendant_subgraphs(self):
        tree = self._tree()
        root = tree.addroot("node1")
        parent = tree.addchild_rev(
            "node101",
            "\t\t",
            "node",
            self._label("section without child subgraphs"),
            root,
            child_subgraphs=False,
        )

        child = tree.addchild_rev(
            "node10101",
            "\t\t\t",
            "node",
            self._label("plain descendant node"),
            parent,
        )

        self.assertIs(child.parent(), parent)
        self.assertEqual([child], parent.childs())
        self.assertFalse(child._child_subgraphs)

    def test_sgmargin_attribute_controls_generated_subgraph_margin(self):
        tree = self._tree()
        root = tree.addroot("node1")

        tree.addchild_rev(
            "node101",
            "\t\t",
            "node",
            self._label("section with custom subgraph margin"),
            root,
            sgmargin="18",
        )

        rendered = "\n".join(node.element() for node in root.childs())

        self.assertIn('margin = "18";', rendered)

    def test_attached_image_row_is_ignored_by_line_selectors(self):
        tree = self._tree()
        node = tree.Node(
            tree,
            "node101",
            [
                '<TABLE><TR><TD>lorem ipsum foobar</TD></TR><TR><TD>Thu 23-07-2026</TD></TR><TR><TD COLSPAN="1" CELLPADDING="0" BORDER="1"><IMG SRC="wkcp-pi-260723-122029.png"/></TD></TR></TABLE>',
            ],
            "\t\t",
            "imgil",
            linecolor=[[1, fontcolor["r"], True]],
            linedate=[[-1, True]],
        )

        node.colorifylines()
        node.linedate()
        rendered = "".join(node._label)

        self.assertIn(
            '<B><FONT COLOR="%s">lorem ipsum foobar</FONT></B>' % fontcolor["r"],
            rendered,
        )
        self.assertIn(fontawesome.symb["calendar"], rendered)
        self.assertIn("&nbsp;Thu 23-07-2026", rendered)
        self.assertIn('<IMG SRC="wkcp-pi-260723-122029.png"/>', rendered)
        self.assertNotIn(fontawesome.symb["calendar"] + '&nbsp;<IMG SRC=', rendered)

    def test_verbatim_header_attributes_target_header_lines(self):
        tree = self._tree(PostAttrProcLabel)
        root = tree.addroot("node1")
        labelhtml, _, _ = BuildNodeLabelHtml(
            "header word1, header word2 in line1; header word1 in line2<BR/> __GVMM_BODY_BOUNDARY__<BR/> body word1, word2 in line1<BR/> body word1 word2 word3 in line3",
            True,
            False,
            html_larrow1,
            html_rarrow1,
            html_larrow2,
            html_rarrow2,
            lambda image, image_key="img": image,
        )

        node = tree.addchild_rev(
            "node101",
            "\t\t",
            "cyello",
            labelhtml,
            root,
            wordcolor=[[2, fontcolor["b"], {"lineskip": -1, "header": True}]],
            linecolor=[
                [1, fontcolor["r"], True, {"header": True}],
                [1, fontcolor["r"], True],
            ],
            linefstyle=[[-1, "I", {"header": True}]],
            vrbt=True,
        )
        rendered = "".join(node._label)

        self.assertIn("header&nbsp;word1,&nbsp;header&nbsp;word2&nbsp;in&nbsp;line1", rendered)
        self.assertIn("body&nbsp;word1,&nbsp;word2&nbsp;in&nbsp;line1", rendered)
        self.assertNotIn("__GVMM_BODY_BOUNDARY__", rendered)
        self.assertIn(
            '<B><FONT COLOR="%s">header&nbsp;word1,&nbsp;header&nbsp;word2&nbsp;in&nbsp;line1</FONT></B>' % fontcolor["r"],
            rendered,
        )
        self.assertNotIn("<U><FONT>header", rendered)
        self.assertIn("<I>header&nbsp;", rendered)
        self.assertIn('<B><FONT COLOR="%s">word1</FONT></B>' % fontcolor["b"], rendered)
        self.assertIn(
            '<B><FONT COLOR="%s">body&nbsp;word1,&nbsp;word2&nbsp;in&nbsp;line1</FONT></B>' % fontcolor["r"],
            rendered,
        )

    def test_verbatim_header_gets_legacy_style_when_first_header_has_no_attrs(self):
        tree = self._tree(PostAttrProcLabel)
        root = tree.addroot("node1")
        labelhtml, _, _ = BuildNodeLabelHtml(
            "Emir<BR/> __GVMM_BODY_BOUNDARY__<BR/> mislim da ce to ivan odjebat<BR/> a mislim mozemo probat 6 mjeseci",
            True,
            False,
            html_larrow1,
            html_rarrow1,
            html_larrow2,
            html_rarrow2,
            lambda image, image_key="img": image,
        )

        node = tree.addchild_rev(
            "node101",
            "\t\t",
            "cyello",
            labelhtml,
            root,
            vrbt=True,
        )
        rendered = "".join(node._label)

        self.assertIn("<B><U><FONT>Emir</FONT></U></B>", rendered)
        self.assertIn("mislim&nbsp;da&nbsp;ce&nbsp;to&nbsp;ivan&nbsp;odjebat", rendered)

    def test_verbatim_header_legacy_style_is_suppressed_by_first_header_attr(self):
        tree = self._tree(PostAttrProcLabel)
        root = tree.addroot("node1")
        labelhtml, _, _ = BuildNodeLabelHtml(
            "Emir<BR/> __GVMM_BODY_BOUNDARY__<BR/> mislim da ce to ivan odjebat",
            True,
            False,
            html_larrow1,
            html_rarrow1,
            html_larrow2,
            html_rarrow2,
            lambda image, image_key="img": image,
        )

        node = tree.addchild_rev(
            "node101",
            "\t\t",
            "cyello",
            labelhtml,
            root,
            linecolor=[[1, fontcolor["r"], True, {"header": True}]],
            vrbt=True,
        )
        rendered = "".join(node._label)

        self.assertIn('<B><FONT COLOR="%s">Emir</FONT></B>' % fontcolor["r"], rendered)
        self.assertNotIn("<U><FONT>Emir", rendered)

    def test_verbatim_collection_preserves_multiple_header_lines_and_body_boundary(self):
        blocks = ExtractMindmapBlocks(
            [
                "# Root",
                "\t: fname=out.jpg",
                "\t# header word1, header word2 in line1",
                "\t# header word1 in line2",
                "\t\t: verbatim cyello hl1r Ehl1it Ehl1w2b l1r",
                "\t\t: ",
                "\t\t: body word1, word2 in line1",
                "\t\t: body word1 word2 word3 in line3",
                "\t\t: ",
            ],
            ApplyInlineBacktickBold,
        )

        self.assertEqual(1, len(blocks))
        self.assertIn("header word1, header word2 in line1; header word1 in line2", blocks[0][2])
        self.assertIn("__GVMM_BODY_BOUNDARY__", blocks[0][2])
        self.assertIn("body<WHITESP>word1,<WHITESP>word2", blocks[0][2])


if __name__ == "__main__":
    unittest.main()
