import tempfile
import unittest
from pathlib import Path

from PIL import Image

from graphviz_mindmaps.constants import (
    html_larrow1,
    html_larrow2,
    html_rarrow1,
    html_rarrow2,
)
from graphviz_mindmaps.render.image_transform import (
    IsImageTransformKey,
    ParseImageTransformKey,
    TransformImage,
)
from graphviz_mindmaps.render.label_html import BuildNodeLabelHtml


class ImageTransformTests(unittest.TestCase):
    def test_plain_image_scale_suffix_resizes_attached_and_image_only_nodes(self):
        import re
        import shutil
        import subprocess
        from types import SimpleNamespace
        from unittest.mock import patch
        from graphviz_mindmaps.cli import build_runtime
        from graphviz_mindmaps.model.document import RenderSession
        from graphviz_mindmaps.parser.outline import ExtractMindmapBlocks
        from graphviz_mindmaps.render.dot import GenDot
        from graphviz_mindmaps.render.label_html import ApplyInlineBacktickBold
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, 'source.png')
            Image.new('RGBA', (100, 80), (20, 40, 60, 77)).save(source)
            original = source.read_bytes()
            for separator in ('=', ':'):
                for mode in ('attached', 'image'):
                    for percent, expected in (('70', (70, 56)), ('125', (125, 100)), ('2.5', (2, 2))):
                        spec = 'img' + separator + str(source) + '|' + percent
                        lines = ['# Root', '\t: fname=out.jpg',
                                 '\t# ' + (spec if mode == 'image' else 'Caption'),
                                 '\t\t: ' + (spec if mode == 'attached' else '')]
                        with self.subTest(separator=separator, mode=mode, percent=percent):
                            session = RenderSession(tmpdir=[directory])
                            with patch('graphviz_mindmaps.render.dot.WriteDot'):
                                GenDot(ExtractMindmapBlocks(lines, ApplyInlineBacktickBold)[0],
                                       SimpleNamespace(dotname='out.dot', jpgname=None), session, build_runtime('default'))
                            path, = re.findall(r'<IMG SRC="([^"]+)"', session.dotbuf)
                            self.assertNotEqual(str(source), path)
                            self.assertNotIn('|', path)
                            with Image.open(path) as image:
                                self.assertEqual(expected, image.size)
                                self.assertEqual((20, 40, 60, 77), image.convert('RGBA').getpixel((0, 0)))
                            self.assertEqual(original, source.read_bytes())
                            if shutil.which('dot'):
                                result = subprocess.run(['dot', '-Tsvg'], input=session.dotbuf,
                                                        capture_output=True, text=True, timeout=30)
                                self.assertEqual(0, result.returncode, result.stderr)
                                self.assertNotIn('Warning:', result.stderr)
            # Unscaled plain images continue to use the original file directly.
            lines = ['# Root', '\t: fname=out.jpg', '\t# Caption', '\t\t: img=' + str(source)]
            session = RenderSession(tmpdir=[directory])
            with patch('graphviz_mindmaps.render.dot.WriteDot'):
                GenDot(ExtractMindmapBlocks(lines, ApplyInlineBacktickBold)[0],
                       SimpleNamespace(dotname='out.dot', jpgname=None), session, build_runtime('default'))
            self.assertIn('<IMG SRC="' + str(source) + '"', session.dotbuf)

    def test_image_scale_must_be_positive_and_finite(self):
        from graphviz_mindmaps.render.image_transform import ParseImageTransformSpec
        for value in ('0', '-1', 'nan', 'inf', '-inf', 'bad'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'image scale'):
                ParseImageTransformSpec('source.png|' + value)

    def test_color_overlay_composes_with_existing_transforms(self):
        self.assertEqual(
            {
                "negate": True,
                "sketch": True,
                "overlay_token": "cgreen",
                "overlay_opacity": 0.1,
            },
            ParseImageTransformKey("img_neg_sk_cgreen10"),
        )
        self.assertTrue(IsImageTransformKey("img_neg_sk_cgreen10"))

    def test_color_without_opacity_uses_default_opacity(self):
        self.assertEqual(
            {"overlay_token": "cblue"},
            ParseImageTransformKey("img_cblue"),
        )

    def test_color_rejects_negative_opacity(self):
        self.assertIsNone(ParseImageTransformKey("img_sk_cgreen-10"))

    def test_color_rejects_opacity_over_one_hundred_percent(self):
        self.assertIsNone(ParseImageTransformKey("img_sk_cgreen101"))

    def test_colored_transform_is_recognized_as_an_image_node(self):
        resolved = []

        label, node_type, _ = BuildNodeLabelHtml(
            "img_sk_cgreen10=photo.png",
            False,
            False,
            html_larrow1,
            html_rarrow1,
            html_larrow2,
            html_rarrow2,
            lambda image, key: resolved.append((image, key)) or "/tmp/transformed.png",
        )

        self.assertEqual([("photo.png", "img_sk_cgreen10")], resolved)
        self.assertEqual("img", node_type)
        self.assertIn('/tmp/transformed.png', label[0])

    def test_transform_applies_overlay_and_preserves_alpha(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.png"
            output = Path(directory) / "output.png"
            Image.new("RGBA", (1, 1), (100, 100, 100, 77)).save(source)

            TransformImage(
                source,
                output,
                overlay_color="#00ff00",
                overlay_opacity=0.1,
            )

            with Image.open(output) as transformed:
                self.assertEqual((90, 115, 90, 77), transformed.convert("RGBA").getpixel((0, 0)))

    def test_transform_key_rejects_invalid_order(self):
        self.assertIsNone(ParseImageTransformKey("img_sk_neg_cgreen10"))


if __name__ == "__main__":
    unittest.main()
