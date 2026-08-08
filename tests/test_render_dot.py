import base64
import re
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
from graphviz_mindmaps.parser.attributes import NormalizeAttributeTokens
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

    def _verbatim_label(self, label):
        labelhtml, _, _ = BuildNodeLabelHtml(
            label,
            True,
            False,
            html_larrow1,
            html_rarrow1,
            html_larrow2,
            html_rarrow2,
            lambda image, image_key="img": image,
        )
        return labelhtml

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

    def test_check_node_uses_default_border_color_and_width(self):
        tree = self._tree()
        node = tree.Node(
            tree,
            "node101",
            self._label("check node with default border"),
            "\t\t",
            "check",
        )

        rendered = node.element()

        self.assertIn('fontcolor="%s"' % fontcolor["def"], rendered)
        self.assertIn('color="royalblue"', rendered)
        self.assertIn('penwidth="2"', rendered)
        self.assertNotIn('fontcolor="royalblue"', rendered)

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

    def test_color_leaf_nodes_use_large_fontsize(self):
        tree = self._tree()

        for ntype in ("cgreen", "ccyan", "cblue", "cpink", "cred", "cyello", "corang", "cgrey", "cblack"):
            with self.subTest(ntype=ntype):
                node = tree.Node(
                    tree,
                    "node101",
                    self._label("%s leaf node" % ntype),
                    "\t\t",
                    ntype,
                )

                self.assertIn('fontsize="%s"' % fontsize["l"], node.element())

    def test_todo_node_uses_18_point_fontsize(self):
        tree = self._tree()
        node = tree.Node(
            tree,
            "node101",
            self._label("todo node with larger default font"),
            "\t\t",
            "todo",
        )

        self.assertIn('fontsize="18"', node.element())

    def test_fontsize_token_aliases_match_font_size_shorthand(self):
        self.assertEqual(
            ["f16", "f18", "l1fontsize20", "w1fontsize22", "l1fe", "f24"],
            NormalizeAttributeTokens(["fs16", "fontsize18", "l1fontsize20", "w1fontsize22", "l1fe", "fs24"]),
        )

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

    def test_header_line_attributes_target_non_verbatim_label_lines(self):
        tree = self._tree()
        labelhtml, _, _ = BuildNodeLabelHtml(
            "header1;header2",
            False,
            False,
            html_larrow1,
            html_rarrow1,
            html_larrow2,
            html_rarrow2,
            lambda image, image_key="img": image,
        )
        node = tree.Node(
            tree,
            "node101",
            labelhtml,
            "\t\t",
            "node",
            linecolor=[[1, fontcolor["r"], True, {"header": True}]],
        )

        node.colorifylines()
        rendered = "".join(node._label)

        self.assertIn(
            '<TD><B><FONT COLOR="%s">header1</FONT></B></TD>' % fontcolor["r"],
            rendered,
        )
        self.assertIn("<TD>header2</TD>", rendered)

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

    def test_verbatim_unscoped_font_size_targets_body_lines(self):
        tree = self._tree()
        node = tree.Node(
            tree,
            "node101",
            self._verbatim_label("Header<BR/> __GVMM_BODY_BOUNDARY__<BR/> body one<BR/> body two<BR/> "),
            "\t\t",
            "def",
            linefsize=[[0, "20"]],
            verbatim=True,
        )

        node.linefsize()
        rendered = "".join(node._label)

        self.assertIn("<TD>Header</TD>", rendered)
        self.assertIn("<TD>__GVMM_BODY_BOUNDARY__</TD>", rendered)
        self.assertIn('<TD><FONT POINT-SIZE="20">body&nbsp;one</FONT></TD>', rendered)
        self.assertIn('<TD><FONT POINT-SIZE="20">body&nbsp;two</FONT></TD>', rendered)

    def test_verbatim_unscoped_font_size_does_not_wrap_horizontal_rules(self):
        tree = self._tree()
        node = tree.Node(
            tree,
            "node101",
            self._verbatim_label("Header<BR/> __GVMM_BODY_BOUNDARY__<BR/> before<BR/> __GVMM_HR__<BR/> after<BR/> "),
            "\t\t",
            "def",
            linefsize=[[0, "16"]],
            verbatim=True,
        )

        node.linefsize()
        rendered = "".join(node._label)

        self.assertIn('<TD><FONT POINT-SIZE="16">before</FONT></TD></TR><HR/><TR>', rendered)
        self.assertIn('<TR><TD><FONT POINT-SIZE="16">after</FONT></TD>', rendered)
        self.assertNotIn("__GVMM_RENDERED_HR__", rendered)
        self.assertNotIn('<FONT POINT-SIZE="16"><HR/>', rendered)

    def test_verbatim_unscoped_font_size_preserves_callout_backgrounds(self):
        tree = self._tree()
        node = tree.Node(
            tree,
            "node101",
            self._verbatim_label("Header<BR/> __GVMM_BODY_BOUNDARY__<BR/> before<BR/> <WHITESP>•<WHITESP>__GVMM_CALLOUT_YELLOW__callout one<BR/> "),
            "\t\t",
            "def",
            linefsize=[[0, "16"]],
            verbatim=True,
        )

        node.linefsize()
        rendered = "".join(node._label)

        self.assertIn('<TD BGCOLOR="#F1E6A8"><FONT POINT-SIZE="16"> •&nbsp;callout&nbsp;one</FONT></TD>', rendered)
        self.assertNotIn('BGCOLOR="#F1E6A8"> •&nbsp;callout&nbsp;one</FONT>', rendered)

    def test_verbatim_header_font_size_targets_header_lines(self):
        tree = self._tree()
        node = tree.Node(
            tree,
            "node101",
            self._verbatim_label("Header<BR/> __GVMM_BODY_BOUNDARY__<BR/> body one<BR/> "),
            "\t\t",
            "def",
            linefsize=[[0, "20", {"header": True}]],
            verbatim=True,
        )

        node.linefsize()
        rendered = "".join(node._label)

        self.assertIn('<TD><FONT POINT-SIZE="20">Header</FONT></TD>', rendered)
        self.assertIn("<TD>body&nbsp;one</TD>", rendered)

    def test_block_collection_preserves_multiple_header_lines_and_body_boundary(self):
        blocks = ExtractMindmapBlocks(
            [
                "# Root",
                "\t: fname=out.jpg",
                "\t# header word1, header word2 in line1",
                "\t# header word1 in line2",
                "\t\t: block cyello hl1r Ehl1it Ehl1w2b l1r",
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

    def test_verbatim_collection_stays_supported(self):
        blocks = ExtractMindmapBlocks(
            [
                "# Root",
                "\t: fname=out.jpg",
                "\t# legacy header",
                "\t\t: verbatim",
                "\t\t: legacy body",
            ],
            ApplyInlineBacktickBold,
        )

        self.assertIn("__GVMM_BODY_BOUNDARY__", blocks[0][2])
        self.assertIn("legacy<WHITESP>body", blocks[0][2])

    def test_code_collection_preserves_multiple_header_lines_and_code_body(self):
        blocks = ExtractMindmapBlocks(
            [
                "# Root",
                "\t: fname=out.jpg",
                "\t# test funkcija s",
                "\t# assertovima",
                "\t# ---",
                "\t# kod",
                "\t\t: code python",
                "\t\t: ",
                "\t\t: def test_connector_init(mocker):",
                "\t\t:     assert mocker.call_count == 1",
                "\t\t: ",
            ],
            ApplyInlineBacktickBold,
        )

        self.assertEqual(1, len(blocks))
        self.assertIn("test funkcija s; assertovima; ---; kod", blocks[0][2])
        match = re.search(r'<CODEBLOCK lang="python" data="([^"]*)"/>', blocks[0][2])
        self.assertIsNotNone(match)
        source = base64.b64decode(match.group(1)).decode("utf-8")
        self.assertIn("def test_connector_init(mocker):", source)
        self.assertIn("    assert mocker.call_count == 1", source)

    def test_verbatim_body_replaces_only_line_start_markers(self):
        blocks = ExtractMindmapBlocks(
            [
                "# Root",
                "\t: fname=out.jpg",
                "\t# Bullet markers",
                "\t\t: verbatim",
                "\t\t: * - valid",
                "\t\t:   - valid",
                "\t\t:     - valid",
                "\t\t:   * - valid",
                "\t\t: - valid",
                "\t\t: not valid - sign replacement",
                "\t\t: ",
            ],
            ApplyInlineBacktickBold,
        )

        body = blocks[0][2]

        self.assertIn("•<WHITESP>-<WHITESP>valid", body)
        self.assertIn("<WHITESP><WHITESP>–<WHITESP>valid", body)
        self.assertIn("<WHITESP><WHITESP><WHITESP><WHITESP>–<WHITESP>valid", body)
        self.assertIn("<WHITESP><WHITESP>•<WHITESP>-<WHITESP>valid", body)
        self.assertIn("not<WHITESP>valid<WHITESP>-<WHITESP>sign<WHITESP>replacement", body)

    def test_verbatim_rawmarkers_preserves_line_start_markers(self):
        blocks = ExtractMindmapBlocks(
            [
                "# Root",
                "\t: fname=out.jpg",
                "\t# Raw marker text",
                "\t\t: verbatim rawmarkers",
                "\t\t: * ! no callout",
                "\t\t: * - valid",
                "\t\t:   - valid",
                "\t\t: ---",
                "\t\t: not valid - sign replacement",
                "\t\t: ",
            ],
            ApplyInlineBacktickBold,
        )

        body = blocks[0][2]

        self.assertIn("*<WHITESP>!<WHITESP>no<WHITESP>callout", body)
        self.assertIn("*<WHITESP>-<WHITESP>valid", body)
        self.assertIn("<WHITESP><WHITESP>-<WHITESP>valid", body)
        self.assertIn("---", body)
        self.assertIn("not<WHITESP>valid<WHITESP>-<WHITESP>sign<WHITESP>replacement", body)
        self.assertNotIn("__GVMM_CALLOUT_", body)
        self.assertNotIn("•<WHITESP>-<WHITESP>valid", body)
        self.assertNotIn("<WHITESP><WHITESP>–<WHITESP>valid", body)
        self.assertNotIn("__GVMM_HR__", body)

        label = body.split("# ", 1)[1]
        labelhtml, _, _ = BuildNodeLabelHtml(
            label,
            True,
            False,
            html_larrow1,
            html_rarrow1,
            html_larrow2,
            html_rarrow2,
            lambda image, image_key="img": image,
        )
        self.assertNotIn("BGCOLOR", "".join(labelhtml))

    def test_verbatim_bolds_asterisk_wrapped_text_when_markers_are_normalized(self):
        blocks = ExtractMindmapBlocks(
            [
                "# Root",
                "\t: fname=out.jpg",
                "\t# Bold verbatim",
                "\t\t: verbatim",
                "\t\t: i want *bolded text* here",
                "\t\t: ",
            ],
            ApplyInlineBacktickBold,
        )

        self.assertIn("i<WHITESP>want<WHITESP><B>bolded<WHITESP>text</B><WHITESP>here", blocks[0][2])

    def test_verbatim_rawmarkers_keeps_asterisk_wrapped_text_literal(self):
        blocks = ExtractMindmapBlocks(
            [
                "# Root",
                "\t: fname=out.jpg",
                "\t# Raw bold verbatim",
                "\t\t: verbatim rawmarkers",
                "\t\t: i want *bolded text* here",
                "\t\t: ",
            ],
            ApplyInlineBacktickBold,
        )

        self.assertIn("i<WHITESP>want<WHITESP>*bolded<WHITESP>text*<WHITESP>here", blocks[0][2])
        self.assertNotIn("<B>bolded", blocks[0][2])

    def test_verbatim_uses_composite_arrows_when_markers_are_normalized(self):
        blocks = ExtractMindmapBlocks(
            [
                "# Root",
                "\t: fname=out.jpg",
                "\t# Arrow verbatim",
                "\t\t: verbatim",
                "\t\t: left => right",
                "\t\t: from -> to",
                "\t\t: right <= left",
                "\t\t: to <- from",
                "\t\t: ",
            ],
            ApplyInlineBacktickBold,
        )
        label = blocks[0][2].split("# ", 1)[1]
        labelhtml, _, _ = BuildNodeLabelHtml(
            label,
            True,
            False,
            html_larrow1,
            html_rarrow1,
            html_larrow2,
            html_rarrow2,
            lambda image, image_key="img": image,
        )

        rendered = "".join(labelhtml)

        self.assertIn("left&nbsp;%s&nbsp;right" % html_rarrow2, rendered)
        self.assertIn("from&nbsp;%s&nbsp;to" % html_rarrow1, rendered)
        self.assertIn("right&nbsp;%s&nbsp;left" % html_larrow2, rendered)
        self.assertIn("to&nbsp;%s&nbsp;from" % html_larrow1, rendered)
        self.assertNotIn("__GVMM_LARROW", rendered)
        self.assertNotIn("__GVMM_RARROW", rendered)

    def test_verbatim_rawmarkers_keeps_arrows_literal(self):
        blocks = ExtractMindmapBlocks(
            [
                "# Root",
                "\t: fname=out.jpg",
                "\t# Raw arrow verbatim",
                "\t\t: verbatim rawmarkers",
                "\t\t: left => right",
                "\t\t: from -> to",
                "\t\t: right <= left",
                "\t\t: to <- from",
                "\t\t: ",
            ],
            ApplyInlineBacktickBold,
        )
        label = blocks[0][2].split("# ", 1)[1]
        labelhtml, _, _ = BuildNodeLabelHtml(
            label,
            True,
            False,
            html_larrow1,
            html_rarrow1,
            html_larrow2,
            html_rarrow2,
            lambda image, image_key="img": image,
        )

        rendered = "".join(labelhtml)

        self.assertIn("left&nbsp;=&gt;&nbsp;right", rendered)
        self.assertIn("from&nbsp;-&gt;&nbsp;to", rendered)
        self.assertIn("right&nbsp;&lt;=&nbsp;left", rendered)
        self.assertIn("to&nbsp;&lt;-&nbsp;from", rendered)
        self.assertNotIn(html_larrow1, rendered)
        self.assertNotIn(html_larrow2, rendered)
        self.assertNotIn(html_rarrow1, rendered)
        self.assertNotIn(html_rarrow2, rendered)

    def test_draw_implies_rawmarkers_for_body_markers(self):
        blocks = ExtractMindmapBlocks(
            [
                "# Root",
                "\t: fname=out.jpg",
                "\t# Draw raw markers",
                "\t\t: draw",
                "\t\t: * ! no callout",
                "\t\t: * - valid",
                "\t\t:   - valid",
                "\t\t: ---",
                "\t\t: i want *literal text* here",
                "\t\t: ",
            ],
            ApplyInlineBacktickBold,
        )

        body = blocks[0][2]

        self.assertIn("*<WHITESP>!<WHITESP>no<WHITESP>callout", body)
        self.assertIn("*<WHITESP>-<WHITESP>valid", body)
        self.assertIn("<WHITESP><WHITESP>-<WHITESP>valid", body)
        self.assertIn("---", body)
        self.assertIn("i<WHITESP>want<WHITESP>*literal<WHITESP>text*<WHITESP>here", body)
        self.assertNotIn("__GVMM_CALLOUT_", body)
        self.assertNotIn("__GVMM_HR__", body)
        self.assertNotIn("<B>literal", body)
        self.assertNotIn("•<WHITESP>-<WHITESP>valid", body)
        self.assertNotIn("<WHITESP><WHITESP>–<WHITESP>valid", body)

    def test_draw_implies_rawmarkers_for_arrows(self):
        blocks = ExtractMindmapBlocks(
            [
                "# Root",
                "\t: fname=out.jpg",
                "\t# Draw raw arrows",
                "\t\t: draw",
                "\t\t: left => right",
                "\t\t: from -> to",
                "\t\t: right <= left",
                "\t\t: to <- from",
                "\t\t: ",
            ],
            ApplyInlineBacktickBold,
        )
        label = blocks[0][2].split("# ", 1)[1]
        labelhtml, _, _ = BuildNodeLabelHtml(
            label,
            False,
            True,
            html_larrow1,
            html_rarrow1,
            html_larrow2,
            html_rarrow2,
            lambda image, image_key="img": image,
        )

        rendered = "".join(labelhtml)

        self.assertIn("left&nbsp;=&gt;&nbsp;right", rendered)
        self.assertIn("from&nbsp;-&gt;&nbsp;to", rendered)
        self.assertIn("right&nbsp;&lt;=&nbsp;left", rendered)
        self.assertIn("to&nbsp;&lt;-&nbsp;from", rendered)
        self.assertNotIn(html_larrow1, rendered)
        self.assertNotIn(html_larrow2, rendered)
        self.assertNotIn(html_rarrow1, rendered)
        self.assertNotIn(html_rarrow2, rendered)

    def test_verbatim_list_callouts_highlight_bullet_rows(self):
        blocks = ExtractMindmapBlocks(
            [
                "# Root",
                "\t: fname=out.jpg",
                "\t# List callouts",
                "\t\t: verbatim",
                "\t\t: * ! red item",
                "\t\t: * ? yellow item",
                "\t\t: * $ green item",
                "\t\t:   green continuation",
                "\t\t: * @ cyan item",
                "\t\t: not a list ! marker",
                "\t\t: ",
                "\t\t: plain after empty line",
                "\t\t: ",
            ],
            ApplyInlineBacktickBold,
        )
        label = blocks[0][2].split("# ", 1)[1]
        labelhtml, _, _ = BuildNodeLabelHtml(
            label,
            True,
            False,
            html_larrow1,
            html_rarrow1,
            html_larrow2,
            html_rarrow2,
            lambda image, image_key="img": image,
        )

        rendered = "".join(labelhtml)

        self.assertIn('BGCOLOR="#F2B8B8"', rendered)
        self.assertIn('BGCOLOR="#F1E6A8"', rendered)
        self.assertIn('BGCOLOR="#B8E3B4"', rendered)
        self.assertIn('BGCOLOR="#B4E4E3"', rendered)
        self.assertIn("•&nbsp;red&nbsp;item", rendered)
        self.assertIn("•&nbsp;yellow&nbsp;item", rendered)
        self.assertIn("•&nbsp;green&nbsp;item", rendered)
        self.assertIn('BGCOLOR="#B8E3B4">   green&nbsp;continuation', rendered)
        self.assertIn("•&nbsp;cyan&nbsp;item", rendered)
        self.assertIn("not&nbsp;a&nbsp;list&nbsp;!&nbsp;marker", rendered)
        self.assertIn("<TD> plain&nbsp;after&nbsp;empty&nbsp;line", rendered)
        self.assertNotIn("__GVMM_CALLOUT_", rendered)

    def test_verbatim_dash_only_line_renders_horizontal_rule(self):
        blocks = ExtractMindmapBlocks(
            [
                "# Root",
                "\t: fname=out.jpg",
                "\t# Horizontal rule",
                "\t\t: verbatim",
                "\t\t: before",
                "\t\t: ---",
                "\t\t: -----",
                "\t\t: after",
                "\t\t: ",
            ],
            ApplyInlineBacktickBold,
        )
        label = blocks[0][2].split("# ", 1)[1]
        labelhtml, _, _ = BuildNodeLabelHtml(
            label,
            True,
            False,
            html_larrow1,
            html_rarrow1,
            html_larrow2,
            html_rarrow2,
            lambda image, image_key="img": image,
        )

        rendered = "".join(labelhtml)

        self.assertEqual(2, rendered.count("<HR/>"))
        self.assertIn("before", rendered)
        self.assertIn("after", rendered)
        self.assertNotIn("__GVMM_HR__", rendered)


if __name__ == "__main__":
    unittest.main()
