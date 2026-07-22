import unittest

from graphviz_mindmaps import fontawesome
from graphviz_mindmaps.constants import font, fontcolor, fontsize, nodetype, vrbtcolors
from graphviz_mindmaps.model.graph import Tree


class RenderDotNodeAttributeTests(unittest.TestCase):
    def test_border_color_does_not_replace_check_fontcolor(self):
        tree = Tree(
            nodetype,
            vrbtcolors,
            fontcolor,
            font,
            fontsize,
            fontawesome.symb,
            lambda token, colors: colors.get(token),
            lambda label, ntype, vrbt, draw, textleft: None,
        )
        node = tree.Node(
            tree,
            "node101",
            ["<TABLE><TR><TD>Child</TD></TR></TABLE>"],
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


if __name__ == "__main__":
    unittest.main()
