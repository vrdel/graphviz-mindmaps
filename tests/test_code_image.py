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
    def test_outline_passes_highlights_to_code_renderer(self):
        blocks = ExtractMindmapBlocks([
            '# Root',
            '\t: fname=out.jpg',
            '\t# Example',
            '\t\t: code python style=monokai l1 l12 l[2-5]',
            '\t\t: print(1)',
            '\t\t: print(2)',
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
            self.assertEqual(('python', [tmpdir], 'monokai', [1, 2, 3, 4, 5, 12]), render.call_args.args[1:])
            self.assertIn('Example', session.dotbuf)
            self.assertIn('<IMG SRC="code.png"', session.dotbuf)

    def test_selectors_combine_without_consuming_header_formatting(self):
        lines, remaining = ExtractCodeHighlights(
            ': code python style=monokai l1 l12 l[2-5] l[4,8-9] h1r l2f20'
        )
        self.assertEqual([1, 2, 3, 4, 5, 8, 9, 12], lines)
        self.assertEqual(
            [':', 'code', 'python', 'style=monokai', 'h1r', 'l2f20'],
            remaining.split(),
        )

    def test_invalid_line_numbers_are_rejected(self):
        for selector in ('l0', 'l[0-2]', 'l[5-2]'):
            with self.subTest(selector=selector), self.assertRaises(ValueError):
                ExtractCodeHighlights(': code python ' + selector)

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
                            if number in (1, 3):
                                self.assertEqual(color, after.getpixel((0, y)))
                                self.assertEqual(color, after.getpixel((after.width - 1, y)))
                            else:
                                box = (0, y, after.width, y + line_height)
                                self.assertIsNone(ImageChops.difference(
                                    before.crop(box), after.crop(box)
                                ).getbbox())


if __name__ == '__main__':
    unittest.main()
