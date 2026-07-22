import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from PIL import Image

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


if __name__ == "__main__":
    unittest.main()
