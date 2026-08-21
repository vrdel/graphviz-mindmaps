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
