from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

from PIL import Image

from graphviz_mindmaps.render.svgbob import FindSvgbob, RenderSvgbobImage


SOURCE = '+---------+     +----------+\n| outline |---->| renderer |\n+---------+     +----------+\n'
HAS_SVGBOB = bool(FindSvgbob() and shutil.which('rsvg-convert'))


class SvgbobTests(unittest.TestCase):
    def test_missing_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('graphviz_mindmaps.render.svgbob.FindSvgbob', return_value=None):
                with self.assertRaisesRegex(ValueError, 'Svgbob is not installed'):
                    RenderSvgbobImage(SOURCE, directory)
            with patch('graphviz_mindmaps.render.svgbob.FindSvgbob', return_value='/bin/tool'), \
                    patch('graphviz_mindmaps.render.svgbob.shutil.which', return_value=None):
                with self.assertRaisesRegex(ValueError, 'rsvg-convert'):
                    RenderSvgbobImage(SOURCE, directory)

    def test_errors_timeouts_and_invalid_svg(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory, 'fake-cli')
            executable.touch()
            failures = (
                (subprocess.CompletedProcess([], 1, '', 'bad input'), 'Svgbob rendering failed: bad input'),
                (subprocess.CompletedProcess([], 0, 'invalid', ''), 'invalid SVG'),
                (subprocess.CompletedProcess([], 0, '<html/>', ''), 'missing SVG root'),
                (subprocess.TimeoutExpired('svgbob', 30), 'timed out'),
            )
            for result, message in failures:
                with self.subTest(message=message), patch(
                    'graphviz_mindmaps.render.svgbob.FindSvgbob', return_value=str(executable),
                ), patch('graphviz_mindmaps.render.svgbob.shutil.which', return_value='/bin/tool'), patch(
                    'graphviz_mindmaps.render.svgbob.subprocess.run',
                    **({'side_effect': result} if isinstance(result, Exception) else {'return_value': result}),
                ), self.assertRaisesRegex(ValueError, message):
                    RenderSvgbobImage(SOURCE, directory)
            self.assertFalse(list(Path(directory).rglob('*.png')))

    @unittest.skipUnless(HAS_SVGBOB, 'optional Svgbob CLI and rsvg-convert required')
    def test_real_diagram_transparency_labels_colors_and_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            outputs = []
            for foreground in ('#2e3440', '#eceff4'):
                output = RenderSvgbobImage(SOURCE, directory, foreground)
                outputs.append(output)
                root = ElementTree.fromstring(output.with_suffix('.svg').read_text())
                text = ''.join(root.itertext())
                self.assertIn('outline', text)
                self.assertIn('renderer', text)
                self.assertIn('stroke: ' + foreground, text)
                self.assertIn('fill: ' + foreground, text)
                with Image.open(output) as image:
                    rgba = image.convert('RGBA')
                    self.assertEqual((0, 255), rgba.getchannel('A').getextrema())
                    self.assertEqual(round(float(root.get('width'))), image.width)
                    self.assertEqual(round(float(root.get('height'))), image.height)
                with patch('graphviz_mindmaps.render.svgbob.subprocess.run') as run:
                    self.assertEqual(output, RenderSvgbobImage(SOURCE, directory, foreground))
                    run.assert_not_called()
            self.assertNotEqual(*outputs)

    @unittest.skipUnless(HAS_SVGBOB, 'optional Svgbob CLI and rsvg-convert required')
    def test_real_stroke_width_defaults_fractional_values_and_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            default = RenderSvgbobImage(SOURCE, directory)
            outputs, sizes = [], []
            for width in (0, 0.5, 2, 4):
                output = RenderSvgbobImage(SOURCE, directory, stroke_width=width)
                outputs.append(output)
                svg = output.with_suffix('.svg').read_text()
                self.assertIn(f'stroke-width: {width};', svg)
                with Image.open(output) as image:
                    sizes.append(image.size)
                if width == 2:
                    self.assertEqual(default, output)
            self.assertEqual(4, len(set(outputs)))
            self.assertEqual(1, len(set(sizes)))
            with patch('graphviz_mindmaps.render.svgbob.subprocess.run') as run:
                self.assertEqual(outputs[1], RenderSvgbobImage(SOURCE, directory, stroke_width='0.5'))
                run.assert_not_called()

    @unittest.skipUnless(HAS_SVGBOB, 'optional Svgbob CLI and rsvg-convert required')
    def test_real_spacing_unicode_and_literal_xml_characters(self):
        source = '┌───────────────┐\n│ a < b & c > d │\n└───────────────┘\n'
        with tempfile.TemporaryDirectory() as directory:
            output = RenderSvgbobImage(source, directory)
            root = ElementTree.fromstring(output.with_suffix('.svg').read_text())
            text = ''.join(element.text or '' for element in root.iter()
                           if element.tag.endswith('}text'))
            # Svgbob positions separate text fragments on the character grid.
            self.assertIn('a<b&c>d', text.replace(' ', ''))


if __name__ == '__main__':
    unittest.main()
