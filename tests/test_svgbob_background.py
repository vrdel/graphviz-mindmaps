from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET

from PIL import Image, ImageColor

from graphviz_mindmaps.render.diagram_colors import DiagramColorTokens, ResolveDiagramColor
from graphviz_mindmaps.render.svgbob import ParseSvgbobBackground, RenderSvgbobImage
from tests.test_svgbob import HAS_SVGBOB

SVG = '{http://www.w3.org/2000/svg}'
SOURCE = '''+----------+    +----------+
| input    |--->| output   |
|          |    |      {s} |
+----------+    +----------+

# Legend:
s = { fill: cred; }
'''


class SvgbobBackgroundTests(unittest.TestCase):
    def test_background_validation(self):
        self.assertIsNone(ParseSvgbobBackground(None))
        for value in ('cblue-10', '#123456', 'ctrans', 'linear-gradient(ccyan, cblue)'):
            self.assertEqual(value, ParseSvgbobBackground(value))
        for value in ('not-a-color', 'linear-gradient(ccyan)'):
            with self.assertRaisesRegex(ValueError, 'svgbob_background'):
                ParseSvgbobBackground(value)

    @unittest.skipUnless(HAS_SVGBOB and shutil.which('node'), 'Svgbob, Node and librsvg required')
    def test_canvas_color_preserves_shapes_text_and_legends_with_and_without_sketch(self):
        with tempfile.TemporaryDirectory() as directory:
            for sketch in (False, True):
                with self.subTest(sketch=sketch):
                    plain = RenderSvgbobImage(SOURCE, directory, fill='cwhite', sketch=sketch, roughness=4)
                    colored = RenderSvgbobImage(SOURCE, directory, fill='cwhite', sketch=sketch,
                                               roughness=4, background='cblue')
                    before, after = [ET.parse(path.with_suffix('.svg')).getroot() for path in (plain, colored)]
                    self.assertEqual([ET.tostring(e) for e in before.iter(SVG+'text')],
                                     [ET.tostring(e) for e in after.iter(SVG+'text')])
                    shapes = lambda root: [ET.tostring(e) for e in root.iter(SVG+'rect')
                                           if 'backdrop' not in e.get('class', '').split()]
                    self.assertEqual(shapes(before), shapes(after))
                    # Legend CSS retains its explicit shape fill.
                    self.assertEqual([e.text for e in before.iter(SVG+'style')],
                                     [e.text for e in after.iter(SVG+'style')])
                    backdrop = next(e for e in after.iter(SVG+'rect') if 'backdrop' in e.get('class', '').split())
                    self.assertIn('fill:' + ResolveDiagramColor('cblue', DiagramColorTokens()), backdrop.get('style'))
                    if sketch:
                        self.assertEqual(list(map(float, after.get('viewBox').split())),
                                         [float(backdrop.get(key)) for key in ('x', 'y', 'width', 'height')])
                    with Image.open(plain) as image:
                        self.assertEqual(0, image.convert('RGBA').getpixel((0, 0))[3])
                    with Image.open(colored) as image:
                        rgb = ImageColor.getrgb(ResolveDiagramColor('cblue', DiagramColorTokens()))
                        self.assertEqual((*rgb, 255), image.convert('RGBA').getpixel((0, 0)))
                    with patch('graphviz_mindmaps.render.svgbob.subprocess.run') as run:
                        self.assertEqual(colored, RenderSvgbobImage(SOURCE, directory, fill='cwhite',
                            sketch=sketch, roughness=4, background='cblue'))
                        run.assert_not_called()
                    transparent = RenderSvgbobImage(SOURCE, directory, fill='cwhite', sketch=sketch,
                                                    roughness=4, background='ctrans')
                    with Image.open(transparent) as image:
                        self.assertEqual(0, image.convert('RGBA').getpixel((0, 0))[3])

    @unittest.skipUnless(HAS_SVGBOB, 'Svgbob and librsvg required')
    def test_gradient_background_is_rasterized(self):
        with tempfile.TemporaryDirectory() as directory:
            path = RenderSvgbobImage(SOURCE, directory, background='linear-gradient(to right, cblue, ccyan)')
            root = ET.parse(path.with_suffix('.svg')).getroot()
            self.assertIsNotNone(root.find('.//' + SVG+'linearGradient'))
            with Image.open(path) as image:
                self.assertNotEqual(image.getpixel((0, 0)), image.getpixel((image.width-1, 0)))
