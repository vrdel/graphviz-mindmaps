import os
from pathlib import Path
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from PIL import Image, ImageDraw

from graphviz_mindmaps.execute import image


def _result(returncode=0, stderr=b"", stdout=b""):
    return SimpleNamespace(returncode=returncode, stderr=stderr, stdout=stdout)


class RenderDotImageTests(unittest.TestCase):
    def test_direct_dot_render_success_does_not_use_fallback(self):
        with tempfile.TemporaryDirectory() as tempdir:
            output = os.path.join(tempdir, "graph.jpg")
            tmpdirs = []

            with mock.patch.object(image.subprocess, "run", return_value=_result()) as run:
                image.RenderDotImage("digraph G {}", output, tmpdirs)

            run.assert_called_once_with(
                ["dot", "-Tjpg", "-o", output],
                input=b"digraph G {}",
                capture_output=True,
            )
            self.assertEqual(tmpdirs, [])

    def test_png_output_uses_png_renderer(self):
        with tempfile.TemporaryDirectory() as tempdir:
            output = os.path.join(tempdir, "graph.png")

            with mock.patch.object(image.subprocess, "run", return_value=_result()) as run:
                image.RenderDotImage("digraph G {}", output, [])

            run.assert_called_once_with(
                ["dot", "-Tpng", "-o", output],
                input=b"digraph G {}",
                capture_output=True,
            )

    def test_cairo_bitmap_limit_uses_svg_inkscape_fallback(self):
        with tempfile.TemporaryDirectory() as tempdir:
            output = os.path.join(tempdir, "graph.png")
            tmpdirs = []
            commands = []

            def fake_run(command, **kwargs):
                commands.append(command)
                if command[:2] == ["dot", "-Tpng"]:
                    return _result(1, stderr=b"dot: graph is too large for cairo-renderer bitmaps")
                if command[:2] == ["dot", "-Tsvg"]:
                    return _result()
                if command[0] == "/usr/bin/inkscape":
                    png_path = command[4]
                    Image.new("RGB", (1, 1), "white").save(png_path)
                    return _result()
                return _result(2, stderr=b"unexpected command")

            with mock.patch.object(image.shutil, "which", return_value="/usr/bin/inkscape"):
                with mock.patch.object(image.subprocess, "run", side_effect=fake_run):
                    image.RenderDotImage("digraph G {}", output, tmpdirs)

            self.assertTrue(os.path.exists(output))
            self.assertEqual(len(tmpdirs), 1)
            inkscape_commands = [command for command in commands if command[0] == "/usr/bin/inkscape"]
            self.assertEqual(1, len(inkscape_commands))
            self.assertFalse(any(command[:2] == ["dot", "-Tpng:gd"] for command in commands))
            self.assertEqual(
                [
                    "/usr/bin/inkscape",
                    inkscape_commands[0][1],
                    "--export-type=png",
                    "--export-filename",
                    inkscape_commands[0][4],
                ],
                inkscape_commands[0],
            )

    def test_cairo_bitmap_warning_on_success_still_overwrites_with_inkscape(self):
        with tempfile.TemporaryDirectory() as tempdir:
            output = os.path.join(tempdir, "graph.png")
            tmpdirs = []
            commands = []

            def fake_run(command, **kwargs):
                commands.append(command)
                if command[:2] == ["dot", "-Tpng"]:
                    Image.new("RGB", (1, 1), "red").save(output)
                    return _result(0, stderr=b"dot: graph is too large for cairo-renderer bitmaps. Scaling by 0.5")
                if command[:2] == ["dot", "-Tsvg"]:
                    return _result()
                if command[0] == "/usr/bin/inkscape":
                    png_path = command[4]
                    Image.new("RGB", (1, 1), "white").save(png_path)
                    return _result()
                return _result(2, stderr=b"unexpected command")

            with mock.patch.object(image.shutil, "which", return_value="/usr/bin/inkscape"):
                with mock.patch.object(image.subprocess, "run", side_effect=fake_run):
                    image.RenderDotImage("digraph G {}", output, tmpdirs)

            with Image.open(output) as rendered:
                self.assertEqual((255, 255, 255), rendered.getpixel((0, 0)))
            self.assertEqual(["dot", "-Tsvg"], commands[1][:2])
            self.assertEqual("/usr/bin/inkscape", commands[2][0])

    def test_cairo_bitmap_limit_reports_missing_inkscape(self):
        with tempfile.TemporaryDirectory() as tempdir:
            output = os.path.join(tempdir, "graph.jpg")

            with mock.patch.object(
                image.subprocess,
                "run",
                return_value=_result(1, stderr=b"dot: graph is too large for cairo-renderer bitmaps"),
            ):
                with mock.patch.object(image.shutil, "which", return_value=None):
                    with self.assertRaisesRegex(RuntimeError, "inkscape is not installed"):
                        image.RenderDotImage("digraph G {}", output, [])


class SingleSavePostProcessingTests(unittest.TestCase):
    def test_png_pixels_match_previous_crop_title_scale_order(self):
        from graphviz_mindmaps.tools.montage_title import render_title
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, 'source.png')
            old, new = Path(directory, 'old.png'), Path(directory, 'new.png')
            for mode in ('RGB', 'RGBA', 'L', 'P'):
                original = Image.new('RGBA', (240, 130), (40, 80, 120, 91))
                ImageDraw.Draw(original).rectangle((20, 15, 130, 90), fill=(190, 30, 50, 123))
                if mode == 'P':
                    original.convert('RGB').convert('P').save(source)
                else:
                    original.convert(mode).save(source)
                original.close()
                for notitle in (True, False):
                    for scale in (None, '50', '125'):
                        with self.subTest(mode=mode, notitle=notitle, scale=scale):
                            shutil.copyfile(source, old)
                            image.ShaveImage(old)
                            if not notitle:
                                render_title(old, old, 'Example title', 's')
                            if scale:
                                image.ResizeByPercent(old, int(scale))
                            image.PostProcessImage(source, new, 'Example title', notitle, scale)
                            with Image.open(old) as before, Image.open(new) as after:
                                self.assertEqual(before.size, after.size)
                                self.assertEqual(before.mode, after.mode)
                                self.assertEqual(before.tobytes(), after.tobytes())

    def test_png_compression_changes_encoding_without_changing_pixels(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, 'source.png')
            Image.new('RGB', (400, 300), '#9abced').save(source)
            sizes = []
            pixels = []
            for level in (0, 1, 6, 9):
                output = Path(directory, f'level-{level}.png')
                image.PostProcessImage(source, output, '', notitle=True, png_compression=level)
                sizes.append(output.stat().st_size)
                with Image.open(output) as result:
                    pixels.append(result.tobytes())
            self.assertTrue(all(value == pixels[0] for value in pixels))
            self.assertGreater(sizes[0], sizes[1])
            self.assertGreater(sizes[1], sizes[-1])

    def test_write_image_saves_once_and_cleans_up_render_temporaries(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, 'source.png')
            output = Path(directory, 'result.png')
            Image.new('RGB', (200, 100), 'red').save(source)
            args = SimpleNamespace(jpgname=str(output), scale='50', preview=False)
            temporary = []
            raw_paths = []
            def render(_dot, raw, _tmpdirs):
                raw_paths.append(raw)
                shutil.copyfile(source, raw)
            save = Image.Image.save
            with mock.patch.object(image, 'RenderDotImage', side_effect=render), mock.patch.object(
                Image.Image, 'save', autospec=True, side_effect=save,
            ) as saves, mock.patch.object(image.subprocess, 'call', side_effect=AssertionError('legacy title subprocess')):
                result = image.WriteImg('digraph {}', args, '', 'Example title', False, temporary, png_compression=9)
                self.assertEqual(1, saves.call_count)
                self.assertEqual({'compress_level': 9}, saves.call_args.kwargs)
            self.assertNotEqual(str(output), raw_paths[0])
            self.assertFalse(Path(raw_paths[0]).exists())
            self.assertEqual([], result['tmpdir'])
            self.assertIsNone(args.jpgname)
            with Image.open(output) as actual:
                self.assertEqual((113, 113), actual.size)

    def test_jpeg_uses_one_final_save_with_default_encoder_options(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory, 'source.png'), Path(directory, 'result.jpg')
            Image.new('RGBA', (30, 20), (10, 20, 30, 50)).save(source)
            save = Image.Image.save
            with mock.patch.object(Image.Image, 'save', autospec=True, side_effect=save) as saves:
                image.PostProcessImage(source, output, '', notitle=True, png_compression=9)
                self.assertEqual(1, saves.call_count)
                self.assertEqual({}, saves.call_args.kwargs)
            with Image.open(output) as actual:
                self.assertEqual('JPEG', actual.format)
                self.assertEqual((26, 16), actual.size)

    def test_failed_final_save_preserves_previous_output_and_removes_partial_file(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory, 'source.png'), Path(directory, 'result.png')
            Image.new('RGB', (20, 20), 'red').save(source)
            output.write_bytes(b'previous output')
            with mock.patch.object(Image.Image, 'save', side_effect=OSError('encoder failure')):
                with self.assertRaisesRegex(OSError, 'encoder failure'):
                    image.PostProcessImage(source, output, '', notitle=True)
            self.assertEqual(b'previous output', output.read_bytes())
            self.assertFalse(list(Path(directory).glob('.gvmm-output-*')))

    def test_tiny_image_crop_and_compression_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory, 'source.png'), Path(directory, 'result.png')
            Image.new('RGBA', (1, 1), (10, 20, 30, 40)).save(source)
            image.PostProcessImage(source, output, '', notitle=True)
            with Image.open(output) as actual:
                self.assertEqual((1, 1), actual.size)
                self.assertEqual((10, 20, 30, 40), actual.getpixel((0, 0)))
        for value in ('-1', '10', '1.5', 'fast', '', float('nan')):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'png_compression'):
                image.ParsePngCompression(value)


if __name__ == "__main__":
    unittest.main()
