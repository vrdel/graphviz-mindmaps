from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET

from PIL import Image

from graphviz_mindmaps.render.math import RenderMathImage

ROOT = Path(__file__).resolve().parents[1]
SVG = '{http://www.w3.org/2000/svg}'
HAS_MATHJAX = bool(shutil.which('node') and shutil.which('rsvg-convert') and
                   (ROOT / 'node_modules/@mathjax/src/package.json').exists())


class MathImageTests(unittest.TestCase):
    def test_missing_dependencies_and_invalid_sizes(self):
        with tempfile.TemporaryDirectory() as directory:
            for missing, message in (('node', 'Node.js'), ('rsvg-convert', 'rsvg-convert')):
                with patch('graphviz_mindmaps.render.math.shutil.which',
                           side_effect=lambda name: None if name == missing else '/bin/' + name):
                    with self.assertRaisesRegex(ValueError, message):
                        RenderMathImage('x', directory)
            for value in (0, -1, 'bad', float('nan'), float('inf')):
                with self.assertRaisesRegex(ValueError, 'positive and finite'):
                    RenderMathImage('x', directory, size=value)


    def test_dependency_failure_timeout_and_atomic_output(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            'graphviz_mindmaps.render.math.shutil.which', return_value='/bin/tool',
        ):
            with patch('graphviz_mindmaps.render.math.subprocess.run',
                       return_value=SimpleNamespace(returncode=1, stderr='MathJax is not installed')):
                with self.assertRaisesRegex(ValueError, 'MathJax is not installed'):
                    RenderMathImage('x', directory)
            with patch('graphviz_mindmaps.render.math.subprocess.run',
                       side_effect=subprocess.TimeoutExpired('node', 30)):
                with self.assertRaisesRegex(ValueError, 'timed out'):
                    RenderMathImage('x', directory)
            self.assertFalse(list(Path(directory).rglob('*.png')))


    @unittest.skipUnless(HAS_MATHJAX, 'MathJax, Node and librsvg required')
    def test_real_svg_contains_entire_expression_and_cache_separates_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            path = RenderMathImage('x+y=2', directory, size=18, color='#123456')
            root = ET.parse(path.with_suffix('.svg')).getroot()
            # MathJax 4 normally splits inline SVGs at operators. Check that no
            # part of the equation was lost when producing our standalone SVG.
            self.assertEqual({'x', '+', 'y', '=', '2'},
                             {e.get('data-latex') for e in root.iter() if e.get('data-mml-node') in {'mi', 'mo', 'mn'}})
            self.assertGreater(float(root.get('width')), 80)
            self.assertEqual('#123456', root.get('color'))
            self.assertTrue(list(root.iter(SVG+'path')))
            self.assertFalse(list(root.iter(SVG+'text')))
            with Image.open(path) as image:
                rgba = image.convert('RGBA')
                self.assertEqual(0, rgba.getpixel((0, 0))[3])
                self.assertIn((18, 52, 86, 255), rgba.getdata())
            with patch('graphviz_mindmaps.render.math.subprocess.run') as run:
                self.assertEqual(path, RenderMathImage('x+y=2', directory, size=18, color='#123456'))
                run.assert_not_called()
            for kwargs in ({'size': 24, 'color': '#123456'}, {'size': 18, 'color': '#abcdef'},
                           {'size': 18, 'color': '#123456', 'display': True}):
                self.assertNotEqual(path, RenderMathImage('x+y=2', directory, **kwargs))
            with self.assertRaisesRegex(ValueError, 'MathJax rendering failed'):
                RenderMathImage(r'\unknownmacro{x}', directory)
