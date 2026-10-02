import io
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image

from graphviz_mindmaps.cli import build_runtime, read_input_lines
from graphviz_mindmaps.model.document import MarkdownBody, RenderSession
from graphviz_mindmaps.parser.markdown import DecodeMarkdownBody, ParseMarkdown, PrepareMarkdownBodies
from graphviz_mindmaps.parser.outline import ExtractMindmapBlocks
from graphviz_mindmaps.render.dot import GenDot
from graphviz_mindmaps.render.label_html import ApplyInlineBacktickBold
from graphviz_mindmaps.render.markdown import RenderMarkdown
from graphviz_mindmaps.theme import ApplyTheme


class MarkdownTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(ApplyTheme, 'default')

    def outline(self, source, attrs='md', title='Markdown node'):
        return ['# Root', '\t: fname=out.jpg notitle', '\t# ' + title,
                '\t\t: ' + attrs] + ['\t\t: ' + line for line in source.split('\n')]

    def render(self, lines, theme='default'):
        blocks = ExtractMindmapBlocks(lines, ApplyInlineBacktickBold)
        self.assertEqual(1, len(blocks))
        session = RenderSession(tmpdir=[self.temp.name])
        with patch('graphviz_mindmaps.render.dot.WriteDot'):
            GenDot(blocks[0], SimpleNamespace(dotname='out.dot', jpgname=None), session, build_runtime(theme))
        return session.dotbuf

    def graphviz(self, dot):
        if shutil.which('dot'):
            for format in ('svg', 'jpg'):
                result = subprocess.run(['dot', '-T' + format], input=dot.encode(), capture_output=True)
                self.assertEqual(0, result.returncode, result.stderr.decode())
                self.assertTrue(result.stdout)

    def test_exact_example_and_sibling(self):
        lines = self.outline("\n# header title 1\n\ni'm text of **bolded** text of paragraph.\n")
        lines += ['\t# sibling', '\t\t: node']
        blocks = ExtractMindmapBlocks(lines, ApplyInlineBacktickBold)
        self.assertEqual(3, sum(line.lstrip().startswith('# ') for line in blocks[0]))
        dot = self.render(lines)
        self.assertIn('<B>bolded</B>', dot)
        self.assertIn('header', dot)
        self.assertIn('sibling', dot)
        self.assertNotIn('GVMM_MARKDOWN', dot)
        self.graphviz(dot)

    def test_source_is_preserved_and_body_attributes_are_literal(self):
        source = '# H\n  - nested\n: colon\n\tcode\ntrailing  \nbackslash\\\n\n\u00a0space\nbg=red\nroot_symb=star'
        prepared = PrepareMarkdownBodies(self.outline(source))
        title, body = DecodeMarkdownBody(prepared[2][2:])
        self.assertEqual(source + '\n', body.source)
        self.assertEqual(len(source.split('\n')), len(body.locations))
        self.assertEqual((5, 5), body.locations[0])
        self.assertNotIn('bg=red', '\n'.join(prepared))

    def test_file_and_stdin_preserve_trailing_spaces_and_file_boundaries(self):
        for name in ('a.otl', 'b.otl'):
            Path(self.temp.name, name).write_text('\n'.join(self.outline('first  \nsecond')))
        files = [str(Path(self.temp.name, name)) for name in ('a.otl', 'b.otl')]
        raw = read_input_lines(files)
        self.assertTrue(raw[4].endswith('  '))
        blocks = ExtractMindmapBlocks(raw, ApplyInlineBacktickBold)
        self.assertEqual(2, len(blocks))
        for block, filename in zip(blocks, files):
            _, body = DecodeMarkdownBody(block[2])
            self.assertEqual(filename, body.filename)
            self.assertEqual('first  \nsecond\n', body.source)
        with patch('sys.stdin', io.StringIO('text  \n')):
            self.assertEqual('text  ', read_input_lines(None)[0])

    def test_multiline_title_and_child_after_body(self):
        lines = ['# Root', '\t: fname=out.jpg', '\t# first', '\t# second',
                 '\t\t: markdown hl2fm', '\t\t: # body heading',
                 '\t\t# child', '\t\t\t: node', '\t# sibling', '\t\t: node']
        dot = self.render(lines)
        self.assertIn('second', dot)
        self.assertIn('child', dot)
        self.graphviz(dot)

    def test_empty_body_and_eof(self):
        for lines in (self.outline(''), ['# Root', '\t: fname=out.jpg', '\t# empty', '\t\t: md']):
            self.graphviz(self.render(lines))

    def test_invalid_prefix_and_modes_have_diagnostics(self):
        for bad in ('\t\t\t: misindented', 'unprefixed body'):
            with self.assertRaisesRegex(ValueError, r'<input>:6:.*expected a colon'):
                PrepareMarkdownBodies(self.outline('good') + [bad])
        for attrs in ('md code=python', 'md block', 'md draw', 'md l1r', 'md w2fm'):
            with self.subTest(attrs=attrs), self.assertRaisesRegex(ValueError, 'Markdown node'):
                PrepareMarkdownBodies(self.outline('body', attrs))

    def test_non_markdown_bodies_do_not_select_markdown(self):
        for mode in ('block', 'code python'):
            lines = self.outline('md\n# code comment', attrs=mode)
            self.assertEqual([line.rstrip() for line in lines], PrepareMarkdownBodies(lines))

    def test_root_body_and_attributes_are_separate(self):
        lines = ['# root title', '# continued', '\t: fname=out.jpg notitle',
                 '\t: theme=nord root_fg=white root_symb=check', '\t: md hl2fm md_width=260',
                 '\t: # Heading', '\t:', '\t: theme=missing fname=wrong.jpg',
                 '\t# normal child', '\t\t: node']
        dot = self.render(lines)
        self.assertIn('Heading', dot)
        self.assertIn('theme=missing', dot)
        self.assertIn('normal', dot)
        self.assertNotIn('GVMM_MARKDOWN', dot)
        self.graphviz(dot)

    def test_full_profile_light_and_dark(self):
        source = '''# Heading **bold**

Paragraph with *italic*, ~~strike~~, `a;b <tag>`, [link](https://example.org), and **nested *emphasis***.

Setext heading
--------------

3. First item wraps with several words here in this sentence.
4. Second
   - nested
   - [x] done
   - [ ] pending

> A quoted **paragraph**.
>
> Another paragraph.

---

```python
# comment should not end the body
if ready:
    run()
```

    indented = True

| left | right |
| :--- | ---: |
| **bold** | `code` |

<b>literal HTML & text</b>
'''
        for theme in ('github-light', 'nord'):
            with self.subTest(theme=theme):
                dot = self.render(self.outline(source, 'md md_width=300'), theme)
                self.assertIn('<S>', dot)
                self.assertIn('☑', dot)
                self.assertIn('3.', dot)
                self.assertIn('&lt;b&gt;', dot)
                self.assertIn('<IMG SRC=', dot)
                self.graphviz(dot)

    def test_soft_hard_breaks_and_node_local_reference_links(self):
        body = MarkdownBody('one\ntwo  \nthree\\\nfour', '<test>', 'title', 1)
        blocks = ParseMarkdown(body)
        self.assertEqual(2, sum(run.hardbreak for run in blocks[0].runs))
        self.assertEqual('one two', ''.join(r.text for r in blocks[0].runs)[:7])
        linked = ParseMarkdown(MarkdownBody('[x]\n\n[x]: https://example.org', '<test>', 'title', 1))
        plain = ParseMarkdown(MarkdownBody('[x]', '<test>', 'title', 1))
        self.assertTrue(linked[0].runs[0].link)
        self.assertFalse(plain[0].runs[0].link)

    def test_wrap_preserves_styled_words_and_long_code(self):
        body = MarkdownBody('prefix **some**word and `a long code span` plus more words', '<test>', 'title', 1)
        result = RenderMarkdown(body, [self.temp.name], width=120)
        self.assertIn('<BR ALIGN="LEFT"/>', result)
        self.assertNotIn('some</B></FONT><BR', result)
        self.assertIn('a&#160;long&#160;code&#160;span', result)

    def test_local_image_relative_to_source_and_remote_rejected(self):
        original = Path(self.temp.name, 'sample.png')
        Image.new('RGB', (800, 200), 'red').save(original)
        sourcefile = Path(self.temp.name, 'map.otl')
        sourcefile.write_text('\n'.join(self.outline('![example](sample.png)', 'md md_width=100')))
        self.graphviz(self.render(read_input_lines([str(sourcefile)])))
        with Image.open(original) as image:
            self.assertEqual((800, 200), image.size)
        for url in ('https://example.org/image.png', 'missing.png'):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, 'Markdown node'):
                self.render(self.outline('![alt](' + url + ')'))
        # The Markdown parser rejects file: URLs as links, leaving literal text.
        self.assertNotIn('<IMG SRC=', self.render(self.outline('![alt](file:///tmp/x.png)')))

    def test_width_validation(self):
        for value in ('zero', '0', '-1', 'nan', 'inf'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'md_width'):
                self.render(self.outline('text', 'md md_width=' + value))

    def test_header_word_font_ignores_symbols_and_does_not_change_body(self):
        from graphviz_mindmaps.constants import font
        for style in ('', 'symb=check', 'quest'):
            with self.subTest(style=style):
                dot = self.render(self.outline('models.User remains ordinary body text.',
                                  'md hl1w2fmld ' + style, 'za models.User ide logika'))
                self.assertIn('<B><FONT FACE="%s">models.User</FONT></B>' % font['mono'], dot)
                self.assertNotIn('<FONT FACE="%s">za' % font['mono'], dot)
                self.graphviz(dot)


if __name__ == '__main__':
    unittest.main()
