import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

from graphviz_mindmaps.model.document import RenderRuntime, RenderSession
from graphviz_mindmaps.parser.outline import ExtractMindmapBlocks
from graphviz_mindmaps.render.dot import GenDot, ResolveRootHrSpacing, ResolveRootHrStyle
from graphviz_mindmaps.render.label_html import ApplyInlineBacktickBold, SpaceHorizontalRules


class HorizontalRuleSpacingTests(unittest.TestCase):
    def test_root_style_default_override_and_validation(self):
        self.assertEqual('solid', ResolveRootHrStyle(['# Root']))
        for style in ('solid', 'dashed', 'dotted'):
            self.assertEqual(style, ResolveRootHrStyle(['# Root', '\t: hr_style=' + style]))
        self.assertEqual('solid', ResolveRootHrStyle(['# Root', '\t# Child', '\t\t: hr_style=dashed']))
        with self.assertRaisesRegex(ValueError, 'hr_style'):
            ResolveRootHrStyle(['# Root', '\t: hr_style=unknown'])

    @unittest.skipUnless(shutil.which('dot'), 'Graphviz is required')
    def test_styled_rules_render_full_width_with_spacing_in_nodes_and_blocks(self):
        for style, dasharray in (('dashed', '5,2'), ('dotted', '1,5')):
            for body in (
                ['\t# before; ---; after', '\t\t: node'],
                ['\t# Block', '\t\t: block', '\t\t:', '\t\t: before', '\t\t: ---', '\t\t: after', '\t\t:'],
            ):
                with self.subTest(style=style, body=body), tempfile.TemporaryDirectory() as tmp:
                    heights = {}
                    widths = {}
                    for spacing in (0, 2, 6):
                        blocks = ExtractMindmapBlocks(
                            ['# Root', '\t: fname=out.jpg hr_style=%s hr_spacing=%d' % (style, spacing)] + body,
                            ApplyInlineBacktickBold,
                        )
                        path = str(Path(tmp) / 'out.dot')
                        GenDot(blocks[0], SimpleNamespace(dotname=path, jpgname=None),
                               RenderSession(tmpdir=[tmp]), RenderRuntime({}, '#ffffff'))
                        svg = subprocess.run(['dot', '-Tsvg', path], check=True, capture_output=True, text=True)
                        self.assertEqual('', svg.stderr)
                        namespace = {'s': 'http://www.w3.org/2000/svg'}
                        node = next(group for group in ET.fromstring(svg.stdout).findall('.//s:g', namespace)
                                    if group.findtext('s:title', namespaces=namespace) == 'node101')
                        rules = [line for line in node.findall('s:polyline', namespace)
                                 if line.get('stroke-dasharray')]
                        self.assertEqual(1, len(rules))
                        self.assertEqual(dasharray, rules[0].get('stroke-dasharray'))
                        points = [tuple(map(float, p.split(','))) for p in rules[0].get('points').split()]
                        widths[spacing] = abs(points[-1][0] - points[0][0])
                        self.assertGreater(widths[spacing], 10)
                        plain = subprocess.run(['dot', '-Tplain', path], check=True, capture_output=True, text=True)
                        heights[spacing] = next(float(line.split()[5]) for line in plain.stdout.splitlines()
                                                if line.startswith('node node101 '))
                        png = subprocess.run(['dot', '-Tpng', path], check=True, capture_output=True)
                        self.assertTrue(png.stdout.startswith(b'\x89PNG'))
                    for spacing in (2, 6):
                        self.assertAlmostEqual(widths[0], widths[spacing], places=2)
                        self.assertAlmostEqual(2 * spacing, (heights[spacing] - heights[0]) * 72, places=2)

    def test_root_setting_default_zero_and_validation(self):
        self.assertEqual(2, ResolveRootHrSpacing(['# Root', '\t: fname=out.jpg']))
        self.assertEqual(0, ResolveRootHrSpacing(['# Root', '\t: hr_spacing=0']))
        self.assertEqual(6, ResolveRootHrSpacing(['# Root', '\t: hr_spacing=6']))
        self.assertEqual(2, ResolveRootHrSpacing(['# Root', '\t# Child', '\t\t: hr_spacing=6']))
        for value in ('-1', '1.5', 'wide'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ResolveRootHrSpacing(['# Root', '\t: hr_spacing=' + value])

    def test_spacing_spans_all_image_columns(self):
        label = '<TABLE><TR><TD COLSPAN="2">before</TD></TR><HR/><TR><TD>one</TD><TD>two</TD></TR></TABLE>'
        result = SpaceHorizontalRules(label, 2)
        self.assertEqual(2, result.count('COLSPAN="2" HEIGHT="2"'))
        self.assertEqual(label, SpaceHorizontalRules(label, 0))

    @unittest.skipUnless(shutil.which('dot'), 'Graphviz is required')
    def test_rendered_spacing_adds_requested_height_for_nodes_and_blocks(self):
        for body in (
            ['\t# before; ---; after', '\t\t: node'],
            ['\t# Block', '\t\t: block', '\t\t:', '\t\t: before', '\t\t: ---', '\t\t: after', '\t\t:'],
        ):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as tmp:
                heights = {}
                ruler_widths = {}
                for spacing in (0, 2, 6):
                    blocks = ExtractMindmapBlocks(
                        ['# Root', '\t: fname=out.jpg hr_spacing=%d' % spacing] + body,
                        ApplyInlineBacktickBold,
                    )
                    path = str(Path(tmp) / 'out.dot')
                    GenDot(blocks[0], SimpleNamespace(dotname=path, jpgname=None),
                           RenderSession(tmpdir=[tmp]), RenderRuntime({}, '#ffffff'))
                    result = subprocess.run(['dot', '-Tplain', path], check=True, capture_output=True, text=True)
                    self.assertEqual('', result.stderr)
                    heights[spacing] = next(float(line.split()[5]) for line in result.stdout.splitlines()
                                            if line.startswith('node node101 '))
                    svg = subprocess.run(['dot', '-Tsvg', path], check=True, capture_output=True, text=True)
                    namespace = {'s': 'http://www.w3.org/2000/svg'}
                    node = next(group for group in ET.fromstring(svg.stdout).findall('.//s:g', namespace)
                                if group.findtext('s:title', namespaces=namespace) == 'node101')
                    rules = []
                    for polygon in node.findall('s:polygon', namespace):
                        points = [tuple(map(float, point.split(','))) for point in polygon.get('points').split()]
                        if len({y for _, y in points}) == 1:
                            rules.append(max(x for x, _ in points) - min(x for x, _ in points))
                    self.assertEqual(1, len(rules))
                    self.assertGreater(rules[0], 10)
                    ruler_widths[spacing] = rules[0]
                for spacing in (2, 6):
                    self.assertAlmostEqual(2 * spacing, (heights[spacing] - heights[0]) * 72, places=2)
                    self.assertAlmostEqual(ruler_widths[0], ruler_widths[spacing], places=2)
