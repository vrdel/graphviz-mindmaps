"""Pixel equivalence with the original title renderer and CLI compatibility."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

from graphviz_mindmaps.tools import montage_title as title


def original_title(source, text, size, background):
    """Retain the pre-optimization drawing path as a compatibility oracle."""
    with Image.open(source) as image:
        rgb = image.convert('RGB')
    point = {'xs': 35, 's': 80, 'm': 148, 'b': 232}[size]
    splice = point + {'xs': 30, 's': 50, 'm': 70, 'b': 100}[size]
    framed = ImageOps.expand(rgb, border=5, fill='#5d6576')
    canvas = Image.new('RGB', (rgb.width + 30, rgb.height + splice), background)
    canvas.paste(framed, (10, splice - 20))
    draw = ImageDraw.Draw(canvas)
    rectangle = (10, 10, canvas.width - 11, splice - 15)
    draw.rectangle(rectangle, fill='black')
    font = ImageFont.truetype(title.TITLE_FONT, point)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = rectangle[0] + max(0, ((rectangle[2] - rectangle[0]) - (bbox[2] - bbox[0])) // 2) - bbox[0]
    y = rectangle[1] + max(0, ((rectangle[3] - rectangle[1]) - (bbox[3] - bbox[1])) // 2) - bbox[1]
    draw.text((x, y), text, font=font, fill='white')
    rgb.close()
    framed.close()
    return canvas


class MontageTitleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def assert_equal_pixels(self, expected, actual):
        self.assertEqual(expected.mode, actual.mode)
        self.assertEqual(expected.size, actual.size)
        self.assertIsNone(ImageChops.difference(expected, actual).getbbox())

    def test_all_sizes_modes_long_titles_and_backgrounds_match_original(self):
        for mode in ('RGB', 'RGBA', 'L', 'P', '1', 'CMYK'):
            image = Image.new('RGB', (123, 79), '#b35a96').convert(mode)
            ImageDraw.Draw(image).rectangle((5, 5, 70, 60), fill=0)
            if mode == 'RGBA':
                image.putalpha(43)
            if mode == 'P':
                image.info['transparency'] = 0
            source = self.root / ('source.tiff' if mode == 'CMYK' else 'source.png')
            image.save(source)
            image.close()
            for size in ('xs', 's', 'm', 'b'):
                for text in ('', 'Plivanje – čćžšđ', 'a long title that extends well beyond the image width'):
                    with self.subTest(mode=mode, size=size, text=text):
                        output = self.root / 'result.png'
                        title.render_title(source, output, text, size, '#8aacc8')
                        with original_title(source, text, size, '#8aacc8') as expected, Image.open(output) as actual:
                            self.assert_equal_pixels(expected, actual)

    def test_tiny_and_tall_inputs_preserve_frame_clipping(self):
        for dimensions in ((1, 1), (8, 33000)):
            source = self.root / 'source.png'
            Image.new('RGB', dimensions, 'red').save(source)
            output = self.root / 'result.png'
            title.render_title(source, output, 'Title', 'xs')
            with original_title(source, 'Title', 'xs', title.DEFAULT_BACKGROUND) as expected, Image.open(output) as actual:
                self.assert_equal_pixels(expected, actual)

    def test_jpeg_encoding_defaults_are_unchanged(self):
        source = self.root / 'source.png'
        Image.new('RGBA', (170, 95), (25, 100, 140, 30)).save(source)
        expected_path = self.root / 'expected.jpg'
        with original_title(source, 'Title', 'xs', title.DEFAULT_BACKGROUND) as expected:
            expected.save(expected_path)
        output = self.root / 'result.jpg'
        title.render_title(source, output, 'Title', 'xs')
        self.assertEqual(expected_path.read_bytes(), output.read_bytes())

    def test_existing_in_place_and_separate_output_argument_forms(self):
        source = self.root / 'source.png'
        Image.new('RGB', (150, 90), 'cyan').save(source)
        with original_title(source, 'Title', 's', title.DEFAULT_BACKGROUND) as expected:
            output = self.root / 'output.png'
            args = SimpleNamespace(MontageTile=None, files=[str(source), str(output)],
                                   ImgTitle='Title', TitleSize='s', Background=title.DEFAULT_BACKGROUND)
            title.TitleImg(args)
            with Image.open(output) as actual:
                self.assert_equal_pixels(expected, actual)
            args.files = [str(source)]
            title.TitleImg(args)
            with Image.open(source) as actual:
                self.assert_equal_pixels(expected, actual)
