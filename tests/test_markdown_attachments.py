from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image

from graphviz_mindmaps.cli import build_runtime, read_input_lines
from graphviz_mindmaps.model.document import MarkdownBody, RenderSession
from graphviz_mindmaps.parser.markdown import ParseMarkdown
from graphviz_mindmaps.parser.outline import ExtractMindmapBlocks
from graphviz_mindmaps.render.dot import GenDot
from graphviz_mindmaps.render.label_html import ApplyInlineBacktickBold
from graphviz_mindmaps.theme import ApplyTheme


class MarkdownAttachmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(ApplyTheme, 'default')
        self.root = Path(self.temp.name)
        self.image = self.root / 'photo.png'
        Image.new('RGBA', (200, 100), (20, 40, 60, 77)).save(self.image)
        self.original = self.image.read_bytes()

    def render(self, source, attrs='md md_wrap=off', root=False):
        if root:
            lines = ['# Caption', '\t: fname=out.png ' + attrs] + ['\t: ' + line for line in source.splitlines()]
        else:
            lines = ['# Root', '\t: fname=out.png', '\t# Caption', '\t\t: ' + attrs] + ['\t\t: ' + line for line in source.splitlines()]
        filename = self.root / 'example.otl'
        filename.write_text('\n'.join(lines))
        blocks = ExtractMindmapBlocks(read_input_lines([str(filename)]), ApplyInlineBacktickBold)
        session = RenderSession(tmpdir=[str(self.root)])
        with patch('graphviz_mindmaps.render.dot.WriteDot'):
            GenDot(blocks[0], SimpleNamespace(dotname='out.dot', jpgname=None), session, build_runtime('default'))
        return session.dotbuf

    def images(self, dot):
        return [Path(path) for path in re.findall(r'<IMG SRC="([^"]+)"', dot)]

    def graphviz(self, dot):
        if shutil.which('dot'):
            svg = subprocess.run(['dot', '-Tsvg'], input=dot, capture_output=True, text=True, timeout=30)
            self.assertEqual(0, svg.returncode, svg.stderr)
            self.assertNotIn('Warning:', svg.stderr)

    def test_body_attachments_render_in_order_with_filters_scale_and_hidden_headers(self):
        source = 'Before\nimg=photo.png|70\nBetween\nimg_neg:photo.png|50\nAfter'
        for root in (False, True):
            for noheader in ('', ' noheader'):
                with self.subTest(root=root, noheader=noheader):
                    dot = self.render(source, 'md md_wrap=off csand' + noheader, root)
                    first, second = self.images(dot)
                    with Image.open(first) as image:
                        self.assertEqual((140, 70), image.size)
                        self.assertEqual((20, 40, 60, 77), image.getpixel((0, 0)))
                    with Image.open(second) as image:
                        self.assertEqual((100, 50), image.size)
                        self.assertEqual((235, 215, 195, 77), image.getpixel((0, 0)))
                    self.assertLess(dot.index('Before'), dot.index(str(first)))
                    self.assertLess(dot.index(str(first)), dot.index('Between'))
                    self.assertLess(dot.index('Between'), dot.index(str(second)))
                    self.assertLess(dot.index(str(second)), dot.index('After'))
                    self.assertEqual(self.original, self.image.read_bytes())
                    self.graphviz(dot)

    def test_sketch_overlay_and_quoted_relative_paths_in_nested_blocks(self):
        spaced = self.root / 'photo with spaces.png'
        shutil.copyfile(self.image, spaced)
        directive = 'img_neg_sk_cred20="photo with spaces.png"|50'
        for source in (directive, '> ' + directive, '- item\n\n  ' + directive,
                       '::: info Example\n' + directive + '\n:::'):
            with self.subTest(source=source):
                dot = self.render(source, 'md noheader md_wrap=off')
                path, = self.images(dot)
                self.assertNotEqual(spaced, path)
                with Image.open(path) as image:
                    self.assertEqual((100, 50), image.size)
                    self.assertEqual('RGBA', image.mode)
                    self.assertEqual(77, image.getpixel((0, 0))[3])
                self.graphviz(dot)
        self.assertEqual(self.original, spaced.read_bytes())

    def test_plain_attachment_uses_original_and_wrap_off_keeps_scaled_size(self):
        dot = self.render('img=photo.png', 'md noheader md_wrap=off mdw=30')
        self.assertEqual([self.image], self.images(dot))
        dot = self.render('img=photo.png|70', 'md noheader md_wrap=on mdw=30')
        path, = self.images(dot)
        with Image.open(path) as image:
            self.assertLessEqual(image.width, 30)
        dot = self.render('img=photo.png|70', 'md noheader md_wrap=off mdw=30')
        with Image.open(self.images(dot)[0]) as image:
            self.assertEqual((140, 70), image.size)
        self.assertEqual(self.original, self.image.read_bytes())

    def test_directives_are_not_parsed_in_code_or_inline_prose(self):
        source = ('Inline `img=photo.png|70` and prose img_neg=photo.png.\n\n'
                  '```text\nimg=photo.png\n```\n\n    img_neg=photo.png')
        blocks = ParseMarkdown(MarkdownBody(source, '<test>', 'Literal', 1))
        self.assertEqual(['paragraph', 'fence', 'code_block'], [block.kind for block in blocks])
        self.assertEqual('img=photo.png', blocks[1].source.strip())
        self.assertEqual('img_neg=photo.png', blocks[2].source.strip())

    def test_invalid_attachments_report_the_body_source_line(self):
        for directive in ('img=missing.png', 'img_neg=missing.png', 'img=photo.png|0',
                          'img_neg=photo.png|nan', 'img=https://example.org/photo.png',
                          'img_neg=file:///tmp/photo.png', 'img="unterminated', 'img=two paths.png'):
            with self.subTest(directive=directive), self.assertRaisesRegex(ValueError, r'example.otl:7: Markdown node.*'):
                self.render('Before\n\n' + directive)
