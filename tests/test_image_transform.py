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
    SaturateImageOverlayColor,
    TransformImage,
)
from graphviz_mindmaps.render.label_html import BuildNodeLabelHtml


class ImageTransformTests(unittest.TestCase):
    def test_color_overlay_composes_with_existing_transforms(self):
        self.assertEqual(
            {
                "negate": True,
                "sketch": True,
                "overlay_token": "cgreen10",
            },
            ParseImageTransformKey("img_neg_sk_cgreen10"),
        )
        self.assertTrue(IsImageTransformKey("img_neg_sk_cgreen10"))

    def test_color_without_offset_uses_base_theme_color(self):
        self.assertEqual(
            {"overlay_token": "cblue"},
            ParseImageTransformKey("img_cblue"),
        )

    def test_color_supports_negative_brightness_offset(self):
        self.assertEqual(
            {"sketch": True, "overlay_token": "cgreen-10"},
            ParseImageTransformKey("img_sk_cgreen-10"),
        )

    def test_image_overlay_color_is_more_saturated(self):
        self.assertEqual("#c8fdd5", SaturateImageOverlayColor("#dffde6"))
        self.assertEqual("#fdfdfd", SaturateImageOverlayColor("#fdfdfd"))

    def test_colored_transform_is_recognized_as_an_image_node(self):
        resolved = []

        label, node_type, _ = BuildNodeLabelHtml(
            "img_neg_sk_cgreen-10=photo.png",
            False,
            False,
            html_larrow1,
            html_rarrow1,
            html_larrow2,
            html_rarrow2,
            lambda image, key: resolved.append((image, key)) or "/tmp/transformed.png",
        )

        self.assertEqual([("photo.png", "img_neg_sk_cgreen-10")], resolved)
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
