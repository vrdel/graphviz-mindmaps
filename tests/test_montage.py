import os
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from graphviz_mindmaps.tools.montage import MontageRenderer, main, normalize_spec


@unittest.skipUnless(shutil.which('gm'), 'GraphicsMagick required')
class MontageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.previous = Path.cwd()
        os.chdir(self.temp.name)
        self.addCleanup(os.chdir, self.previous)
        quiet = patch('graphviz_mindmaps.tools.montage.run_command',
                      side_effect=lambda command: subprocess.run(command, check=True, capture_output=True))
        quiet.start()
        self.addCleanup(quiet.stop)
        Image.new('RGB', (8, 33000), 'red').save('red.png')
        Image.new('RGB', (8, 33000), 'blue').save('blue.png')

    def renderer(self, output='result.jpg', scale=None):
        renderer = MontageRenderer(Path('montage.yml'), output, scale=scale)
        self.addCleanup(renderer.cleanup)
        return renderer

    def test_scale_is_applied_before_jpeg_encoding(self):
        renderer = self.renderer(scale='50')
        spec = normalize_spec({'entries': ['red.png', {'new_row': True}, 'blue.png']})
        output = renderer.render_spec(spec)
        with Image.open(output) as image:
            self.assertEqual((4, 33000), image.size)
            self.assertGreater(image.getpixel((1, 10))[0], 200)
            self.assertGreater(image.getpixel((1, image.height - 10))[2], 200)

    def test_tall_nested_columns_and_titles_use_png_intermediates(self):
        renderer = self.renderer(scale='50')
        spec = normalize_spec({'title': 'Result', 'entries': [
            {'image_gray': 'red.png'}, {'new_row': True},
            {'submontage': {'title': 'Nested', 'entries': [{'column': ['red.png', 'blue.png']}]}}
        ]})
        output = renderer.render_spec(spec)
        with Image.open(output) as image:
            self.assertLess(image.height, 65500)
            self.assertGreater(image.height, 49000)
        self.assertTrue(Path('montage-m1.png').exists())
        renderer.cleanup()
        self.assertFalse(Path('montage-m1.png').exists())

    def test_oversized_jpeg_preserves_previous_output_and_png_remains_full_size(self):
        Image.new('RGB', (4, 4), 'green').save('result.jpg')
        original = Path('result.jpg').read_bytes()
        spec = normalize_spec({'entries': ['red.png', {'new_row': True}, 'blue.png']})
        with self.assertRaisesRegex(ValueError, 'smaller -s percentage or a .png'):
            self.renderer().render_spec(spec)
        self.assertEqual(original, Path('result.jpg').read_bytes())
        output = self.renderer(output='result.png').render_spec(spec)
        with Image.open(output) as image:
            self.assertEqual((8, 66000), image.size)

    def test_failed_conversion_preserves_previous_output(self):
        Path('result.png').write_bytes(b'previous output')
        renderer = self.renderer(output='result.png')
        with patch('graphviz_mindmaps.tools.montage.run_command',
                   side_effect=subprocess.CalledProcessError(1, ['gm', 'convert'])):
            with self.assertRaises(subprocess.CalledProcessError):
                renderer.write_output(Path('red.png'), Path('result.png'), '50')
        self.assertEqual(b'previous output', Path('result.png').read_bytes())
        self.assertFalse(list(Path('.').glob('.result-*')))

    def test_cli_reports_dimension_error_without_traceback(self):
        Path('montage.yml').write_text('entries:\n  - image: red.png\n  - new_row: true\n  - image: blue.png\n')
        with patch('sys.stderr', new_callable=io.StringIO) as stderr:
            self.assertEqual(1, main(['-o', 'too-tall.jpg', 'montage.yml']))
        self.assertIn('65500', stderr.getvalue())
        self.assertNotIn('Traceback', stderr.getvalue())
        self.assertFalse(Path('too-tall.jpg').exists())
