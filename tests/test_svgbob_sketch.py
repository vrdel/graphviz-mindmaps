from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET

from graphviz_mindmaps.render.svgbob import FindSvgbob, RenderSvgbobImage
from graphviz_mindmaps.render.svgbob_sketch import ApplySvgbobSketch, ParseSvgbobSketch, SVG

HAS_RENDERER = bool(FindSvgbob() and shutil.which('rsvg-convert') and shutil.which('node'))
SOURCE = ''' .------------.     +------------+
 | input      +---->| output {s} |
 '------------'     +------------+

# Legend:
s = {fill: linear-gradient(ccyan,cblue); stroke: cred;}
'''


class SvgbobSketchTests(unittest.TestCase):
    def test_option_defaults_and_validation(self):
        self.assertEqual((False, 1), ParseSvgbobSketch())
        self.assertEqual((True, .5), ParseSvgbobSketch('on', '.5'))
        self.assertEqual((False, 2), ParseSvgbobSketch('off', '2'))
        for value in ('yes','1','bad'):
            with self.assertRaisesRegex(ValueError, 'svgbob_sketch'):
                ParseSvgbobSketch(value)
        for value in ('nan','inf',-1,6,'bad'):
            with self.assertRaisesRegex(ValueError, 'svgbob_roughness'):
                ParseSvgbobSketch('on', value)

    @unittest.skipUnless(HAS_RENDERER, 'Svgbob, librsvg and Node.js required')
    def test_sketch_preserves_text_fills_arrowheads_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            plain = RenderSvgbobImage(SOURCE, directory, fill='ccyan')
            sketch = RenderSvgbobImage(SOURCE, directory, fill='ccyan', sketch=True)
            before = ET.parse(plain.with_suffix('.svg')).getroot()
            after = ET.parse(sketch.with_suffix('.svg')).getroot()
            self.assertEqual([ET.tostring(e) for e in before.iter(SVG+'text')],
                             [ET.tostring(e) for e in after.iter(SVG+'text')])
            self.assertEqual(ET.tostring(before.find(SVG+'defs')), ET.tostring(after.find(SVG+'defs')))
            self.assertEqual([e.attrib for e in before.iter(SVG+'polygon')],
                             [e.attrib for e in after.iter(SVG+'polygon')])
            self.assertTrue(any('C' in e.get('d','') for e in after.iter(SVG+'path')))
            for old in before.iter(SVG+'rect'):
                if 'backdrop' in old.get('class',''):
                    continue
                new = next(e for e in after.iter(SVG+'rect') if e.get('x') == old.get('x'))
                self.assertEqual(old.get('fill'), new.get('fill'))
                self.assertIn('stroke:none !important', new.get('style'))
            self.assertNotEqual(plain.read_bytes(), sketch.read_bytes())
            # Force a new render, rather than testing only the PNG cache hit.
            original_svg = sketch.with_suffix('.svg').read_bytes()
            sketch.unlink()
            self.assertEqual(sketch, RenderSvgbobImage(SOURCE, directory, fill='ccyan', sketch=True))
            self.assertEqual(original_svg, sketch.with_suffix('.svg').read_bytes())
            with patch('graphviz_mindmaps.render.svgbob.subprocess.run') as run:
                self.assertEqual(sketch, RenderSvgbobImage(SOURCE, directory, fill='ccyan', sketch=True))
                run.assert_not_called()
            strong = RenderSvgbobImage(SOURCE, directory, fill='ccyan', sketch=True, roughness=2)
            self.assertNotEqual(sketch, strong)
            self.assertNotEqual(original_svg, strong.with_suffix('.svg').read_bytes())

    @unittest.skipUnless(HAS_RENDERER, 'Svgbob, librsvg and Node.js required')
    def test_node_is_optional_unless_sketching_is_enabled(self):
        which = shutil.which
        with tempfile.TemporaryDirectory() as directory, patch(
            'shutil.which', side_effect=lambda name: None if name == 'node' else which(name),
        ):
            self.assertTrue(RenderSvgbobImage(SOURCE, directory).is_file())
            with self.assertRaisesRegex(ValueError, 'requires Node.js'):
                RenderSvgbobImage(SOURCE, directory, sketch=True)

    def test_zero_stroke_does_not_create_visible_sketches(self):
        root = ET.fromstring('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><line x1="1" y1="1" x2="10" y2="10"/></svg>')
        original = ET.tostring(root)
        with patch('graphviz_mindmaps.render.svgbob_sketch.subprocess.run') as run:
            ApplySvgbobSketch(root, stroke_width=0)
            run.assert_not_called()
        self.assertEqual(original, ET.tostring(root))

    def test_helper_failure_is_reported(self):
        from types import SimpleNamespace
        root = ET.fromstring('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><line x1="1" y1="1" x2="10" y2="10"/></svg>')
        with patch('graphviz_mindmaps.render.svgbob_sketch.subprocess.run',
                   return_value=SimpleNamespace(returncode=1, stderr='Rough.js is not installed')):
            with self.assertRaisesRegex(ValueError, 'Rough.js is not installed'):
                ApplySvgbobSketch(root)
