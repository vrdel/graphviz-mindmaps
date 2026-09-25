import colorsys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image, ImageColor, ImageChops
from pygments.styles import get_style_by_name

from graphviz_mindmaps.render.code_image import ExtractCodeHighlights, RenderCodeImage
from graphviz_mindmaps.model.document import RenderRuntime, RenderSession
from graphviz_mindmaps.parser.outline import ExtractMindmapBlocks
from graphviz_mindmaps.render.dot import GenDot
from graphviz_mindmaps.render.label_html import ApplyInlineBacktickBold


class CodeHighlightTests(unittest.TestCase):
    def test_colored_ranges_and_end_relative_selectors(self):
        selected, remaining = ExtractCodeHighlights(
            ': code python l1r l[2-3]g El1b h1r l2f20'
        )
        self.assertEqual([(1, 'r'), (2, 'g'), (3, 'g'), (-1, 'b')], selected)
        self.assertEqual([':', 'code', 'python', 'h1r', 'l2f20'], remaining.split())
        base = ImageColor.getrgb(get_style_by_name('default').highlight_color)
        _, saturation, brightness = colorsys.rgb_to_hsv(*(c / 255 for c in base))
        with tempfile.TemporaryDirectory() as tmpdir:
            for style in ('default', 'monokai'):
                with self.subTest(style=style):
                    path = RenderCodeImage('\na = 1\nb = 2\nc = 3\n', 'python', [tmpdir], style, selected)
                    with Image.open(path) as image:
                        line_height = (image.height - 28) // 5
                        for row, hue in ((2, 0), (3, 1 / 3), (4, 2 / 3)):
                            rgb = image.getpixel((0, 14 + (row - 1) * line_height))
                            actual = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
                            for expected, value in zip((hue, saturation, brightness), actual):
                                self.assertAlmostEqual(expected, value, places=2)
                    reverse = RenderCodeImage('\na = 1\nb = 2\nc = 3\n', 'python', [tmpdir], style, list(reversed(selected)))
                    self.assertNotEqual(path, reverse)
                    with Image.open(reverse) as image:
                        rgb = image.getpixel((0, 14 + 3 * line_height))
                        self.assertGreater(rgb[1], rgb[2])

    def test_outline_passes_highlights_to_code_renderer(self):
        blocks = ExtractMindmapBlocks([
            '# Root',
            '\t: fname=out.jpg',
            '\t# Example',
            '\t\t: code python style=monokai l1 l12 l[2-5] El1 El[1-5]',
            '\t\t:',
            '\t\t: print(1)',
            '\t\t: print(2)',
            '\t\t:',
        ], ApplyInlineBacktickBold)
        with tempfile.TemporaryDirectory() as tmpdir:
            session = RenderSession(tmpdir=[tmpdir])
            with patch('graphviz_mindmaps.render.dot.RenderCodeImage', return_value='code.png') as render:
                with patch('graphviz_mindmaps.render.dot.WriteDot'):
                    GenDot(
                        blocks[0], SimpleNamespace(dotname='out.dot', jpgname=None),
                        session, RenderRuntime({}, '#ffffff'),
                    )
            render.assert_called_once()
            self.assertEqual(('python', [tmpdir], 'monokai', [(n, '') for n in (1, 12, 2, 3, 4, 5, -1, -1, -2, -3, -4, -5)]), render.call_args.args[1:])
            self.assertIn('Example', session.dotbuf)
            self.assertIn('<IMG SRC="code.png"', session.dotbuf)

    def test_selectors_combine_without_consuming_header_formatting(self):
        lines, remaining = ExtractCodeHighlights(
            ': code python style=monokai l1 l12 l[2-5] l[4,8-9] h1r l2f20'
        )
        self.assertEqual([(n, '') for n in (1, 12, 2, 3, 4, 5, 4, 8, 9)], lines)
        self.assertEqual(
            [':', 'code', 'python', 'style=monokai', 'h1r', 'l2f20'],
            remaining.split(),
        )

    def test_invalid_line_numbers_are_rejected(self):
        for selector in ('l0', 'l[0-2]', 'l[5-2]', 'El0', 'El[0-2]', 'El[5-2]'):
            with self.subTest(selector=selector), self.assertRaises(ValueError):
                ExtractCodeHighlights(': code python ' + selector)

    def test_forward_and_end_relative_selectors_ignore_surrounding_blank_lines(self):
        source = '\n  \npre_save.connect(callback)\n\npre_delete.connect(callback)\n  \n'
        cases = (
            ('l1', {3}),
            ('El1', {5}),
            ('El[1-5]', {3, 4, 5}),
            ('l1 El1', {3, 5}),
            ('l2 El2', {4}),
            ('l4 El4', set()),
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            for selector, expected in cases:
                with self.subTest(selector=selector):
                    selected, remaining = ExtractCodeHighlights(': code python ' + selector)
                    self.assertEqual([':', 'code', 'python'], remaining.split())
                    path = RenderCodeImage(source, 'python', [tmpdir], highlight_lines=selected)
                    with Image.open(path) as image:
                        line_height = (image.height - 28) // 7
                        color = ImageColor.getrgb(get_style_by_name('default').highlight_color)
                        actual = {
                            row for row in range(1, 8)
                            if image.getpixel((0, 14 + (row - 1) * line_height)) == color
                        }
                        self.assertEqual(expected, actual)

    def test_blank_code_has_no_highlights(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plain = RenderCodeImage('\n  \n', 'text', [tmpdir])
            highlighted = RenderCodeImage('\n  \n', 'text', [tmpdir], highlight_lines=[1, -1])
            with Image.open(plain) as before, Image.open(highlighted) as after:
                self.assertIsNone(ImageChops.difference(before, after).getbbox())

    def test_highlights_use_style_color_and_count_blank_lines(self):
        source = '\nvalue = 1\n\nprint(value)'
        with tempfile.TemporaryDirectory() as tmpdir:
            for style in ('default', 'monokai', 'nonexistent-style'):
                with self.subTest(style=style):
                    plain = RenderCodeImage(source, 'python', [tmpdir], style)
                    highlighted = RenderCodeImage(
                        source, 'python', [tmpdir], style, [1, 3, 12]
                    )
                    self.assertNotEqual(plain, highlighted)
                    self.assertEqual(highlighted, RenderCodeImage(
                        source, 'python', [tmpdir], style, [12, 3, 1, 1]
                    ))
                    resolved = 'default' if style == 'nonexistent-style' else style
                    color = ImageColor.getrgb(get_style_by_name(resolved).highlight_color)
                    with Image.open(plain) as before, Image.open(highlighted) as after:
                        self.assertEqual(before.size, after.size)
                        line_height = (after.height - 28) // 4
                        for number in range(1, 5):
                            y = 14 + (number - 1) * line_height
                            if number in (2, 4):
                                self.assertEqual(color, after.getpixel((0, y)))
                                self.assertEqual(color, after.getpixel((after.width - 1, y)))
                            else:
                                box = (0, y, after.width, y + line_height)
                                self.assertIsNone(ImageChops.difference(
                                    before.crop(box), after.crop(box)
                                ).getbbox())


if __name__ == '__main__':
    unittest.main()
