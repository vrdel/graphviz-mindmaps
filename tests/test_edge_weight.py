import re
import shutil
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from graphviz_mindmaps.cli import build_runtime
from graphviz_mindmaps.model.document import RenderSession
from graphviz_mindmaps.parser.outline import ExtractMindmapBlocks
from graphviz_mindmaps.render.dot import GenDot
from graphviz_mindmaps.render.label_html import ApplyInlineBacktickBold
from graphviz_mindmaps.theme import ApplyTheme


class EdgeWeightTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(ApplyTheme, 'default')

    def render(self, attrs='', root_attrs=''):
        blocks = ExtractMindmapBlocks([
            '# Root', '\t: fname=out.jpg ' + root_attrs,
            '\t# Primary', '\t\t: cblue ' + attrs,
            '\t\t# Descendant', '\t\t\t: node',
            '\t# Sibling', '\t\t: node',
        ], ApplyInlineBacktickBold)
        session = RenderSession()
        with patch('graphviz_mindmaps.render.dot.WriteDot'):
            GenDot(blocks[0], SimpleNamespace(dotname='out.dot', jpgname=None),
                   session, build_runtime('default'))
        return session.dotbuf

    def edge(self, dot, target):
        return next(line for line in dot.splitlines() if re.search(r'-> ' + target + r':w\b', line))

    def graphviz(self, dot):
        if shutil.which('dot'):
            svg = subprocess.run(['dot', '-Tsvg'], input=dot, text=True, capture_output=True, timeout=30)
            self.assertEqual(0, svg.returncode, svg.stderr)
            self.assertNotIn('Warning:', svg.stderr)

    def test_local_weight_alias_and_zero_preserve_typed_edge_style(self):
        plain = self.render()
        for value in ('0', '1', '10'):
            with self.subTest(value=value):
                weighted = self.render('edge_weight=' + value)
                self.assertEqual(weighted, self.render('edgw=' + value))
                edge = self.edge(weighted, 'node101')
                self.assertIn(f'weight="{value}"', edge)
                self.assertEqual(self.edge(plain, 'node101'), edge.replace(f' weight="{value}"', ''))
                for target in ('node10101', 'node102'):
                    self.assertEqual(self.edge(plain, target), self.edge(weighted, target))
                self.graphviz(weighted)

    def test_weight_composes_with_explicit_color_thickness_and_arrow(self):
        style = 'edgrt3dv'
        plain = self.render(style)
        changed = self.render(style + ' edgw=8')
        edge = self.edge(changed, 'node101')
        self.assertIn('penwidth="3"', edge)
        self.assertIn('style="dashed"', edge)
        self.assertIn('arrowhead="open"', edge)
        self.assertEqual(self.edge(plain, 'node101'), edge.replace(' weight="8"', ''))
        self.graphviz(changed)

    def test_global_default_local_override_and_independent_maps(self):
        plain = self.render()
        self.assertNotIn('weight=', plain)
        for value in ('0', '3'):
            with self.subTest(value=value):
                dot = self.render('edgw=10', 'global_edge_weight=' + value)
                defaults = next(line for line in dot.splitlines() if line.strip().startswith('edge['))
                self.assertIn(f'weight="{value}"', defaults)
                self.assertIn('weight="10"', self.edge(dot, 'node101'))
                self.assertNotIn('weight=', self.edge(dot, 'node10101'))
                self.assertNotIn('weight=', self.edge(dot, 'node102'))
                self.graphviz(dot)
        self.assertEqual(plain, self.render())

    def test_weight_validation_rejects_non_dot_integers(self):
        for value in ('-1', '1.5', 'nan', 'inf', 'abc', '""'):
            for key in ('edge_weight', 'edgw', 'global_edge_weight'):
                with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, key + ' must be a nonnegative integer'):
                    if key == 'global_edge_weight':
                        self.render(root_attrs=key + '=' + value)
                    else:
                        self.render(key + '=' + value)
