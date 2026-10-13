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

    def test_emoticons_render_in_headings_and_body_modes(self):
        for mode in ('md', 'block', 'verbatim'):
            with self.subTest(mode=mode):
                dot = self.render(self.outline('Happy :-) Neutral :-|', mode, 'Heading :-)'))
                self.assertEqual(2, dot.count('🙂'))
                self.assertIn('😐', dot)
                self.assertNotIn(':-)', dot)
                self.assertNotIn(':-|', dot)
                self.graphviz(dot)
        dot = self.render(['# Root :-)', '\t: fname=out.jpg', '\t# Neutral :-|', '\t\t: node'])
        self.assertIn('Root&nbsp;🙂', dot)
        self.assertIn('😐', dot)
        self.graphviz(dot)

    def test_markdown_emoticons_preserve_code_and_link_targets(self):
        body = MarkdownBody('**:-)** *:-|* `:-)` [:-)](<https://example.org/:-)>)\n\n'
                            '```text\n:-) :-|\n```', '<input>', 'test', 1)
        blocks = ParseMarkdown(body)
        runs = blocks[0].runs
        self.assertTrue(any(run.text == '🙂' and run.bold for run in runs))
        self.assertTrue(any(run.text == '😐' and run.italic for run in runs))
        self.assertTrue(any(run.text == ':-)' and run.code for run in runs))
        self.assertTrue(any(run.text == '🙂' and run.link == 'https://example.org/:-)' for run in runs))
        self.assertEqual(':-) :-|\n', blocks[1].source)

    def test_rawmarkers_preserves_emoticons(self):
        for mode in ('md rawmarkers', 'block rawmarkers', 'draw'):
            with self.subTest(mode=mode):
                dot = self.render(self.outline('Happy :-) Neutral :-|', mode))
                self.assertIn(':-)', dot)
                self.assertIn(':-|', dot)
                self.assertNotIn('🙂', dot)
                self.assertNotIn('😐', dot)

    def test_emoticons_respect_word_and_path_boundaries(self):
        from graphviz_mindmaps.parser.emoticons import ReplaceEmoticons
        self.assertEqual('🙂, 😐!', ReplaceEmoticons(':-), :-|!'))
        literal = 'word:-) :-|word /tmp/:-)/file https://example.org/:-)'
        self.assertEqual(literal, ReplaceEmoticons(literal))

    def test_extended_emoticons_across_body_modes(self):
        source = 'Faces :) :( ;-) :-D XD :-p ;-P :-O :-/ :-( :\'( :\') 8-) :-* O:-) >:-) >:( :-X :-$ <3 </3'
        expected = '🙂 🙁 😉 😃 😆 😛 😜 😮 😕 🙁 😢 😂 😎 😗 😇 😈 😠 🤐 😳 ❤️ 💔'.split()
        for mode in ('md', 'block', 'verbatim'):
            with self.subTest(mode=mode):
                dot = self.render(self.outline(source, mode))
                for emoji in expected:
                    self.assertIn(emoji, dot)
                self.graphviz(dot)
        # Emoticons that contain stars must be converted before legacy bolding.
        dot = self.render(self.outline('', 'node', 'Kisses :-* and :-*; wink ;-)'))
        self.assertEqual(2, dot.count('😗'))
        self.assertIn('😉', dot)
        self.graphviz(dot)

    def test_extended_emoticons_preserve_markdown_code_and_rawmarkers(self):
        text = 'Faces ;-) :-* XD <3 </3 >:( :-/'
        for mode in ('md rawmarkers', 'block rawmarkers', 'draw'):
            dot = self.render(self.outline(text, mode))
            for emoji in ('😉', '😗', '😆', '❤️', '💔', '😠', '😕'):
                self.assertNotIn(emoji, dot)
        body = MarkdownBody('Kiss :-* and :-* with **:-D** and `XD <3`', '<test>', 'test', 1)
        runs = ParseMarkdown(body)[0].runs
        self.assertEqual(2, ''.join(run.text for run in runs).count('😗'))
        self.assertTrue(any(run.text == '😃' and run.bold for run in runs))
        self.assertTrue(any(run.text == 'XD <3' and run.code for run in runs))

    def test_list_callouts_keep_markdown_formatting_and_symbols(self):
        source = ('* ! **Red** item\n  continued text\n'
                  '- ? Yellow *item*\n- $ Green `code`\n- @ Cyan item\n'
                  '- Plain item')
        dot = self.render(self.outline(source, 'md noheader symb=book md_width=180'))
        for color in ('#F2B8B8', '#F1E6A8', '#B8E3B4', '#B4E4E3'):
            self.assertEqual(2, dot.count('BGCOLOR="' + color + '"'))
        self.assertIn('<B>Red</B>', dot)
        self.assertIn('<I>item</I>', dot)
        self.assertIn('continued', dot)
        self.assertIn('FACE="FontAwesome"', dot)
        for marker in ('!', '?', '$', '@'):
            self.assertNotIn('>' + marker + '</FONT>', dot)
        self.graphviz(dot)

    def test_callouts_stop_at_blank_lines_and_nested_items(self):
        source = '* ! warning\n  continuation\n\n  plain paragraph\n  - nested plain\n  - @ nested cyan\n* plain sibling'
        body = MarkdownBody(source, '<input>', 'test', 1)
        items = ParseMarkdown(body)[0].children
        self.assertEqual('#F2B8B8', items[0].callout)
        self.assertEqual('', items[1].callout)
        nested = items[0].children[-1].children
        self.assertEqual('', nested[0].callout)
        self.assertEqual('#B4E4E3', nested[1].callout)
        dot = self.render(self.outline(source))
        self.assertEqual(2, dot.count('BGCOLOR="#F2B8B8"'))
        self.assertEqual(2, dot.count('BGCOLOR="#B4E4E3"'))
        self.assertIn('plain', dot)
        self.graphviz(dot)

    def test_callout_markers_are_literal_outside_bullet_prefixes(self):
        source = ('! ordinary paragraph\n\n* \\! escaped\n* `?` code\n'
                  '* **$** bold\n* @word\n\n1. ! ordered\n\n'
                  '```text\n* ! literal code\n```')
        def walk(blocks):
            for block in blocks:
                yield block
                yield from walk(block.children)
        body = MarkdownBody(source, '<input>', 'test', 1)
        self.assertTrue(all(not block.callout for block in walk(ParseMarkdown(body))))
        for mode in ('md', 'markdown'):
            dot = self.render(self.outline('* ! literal\n* @ literal', mode + ' rawmarkers'))
            self.assertNotIn('BGCOLOR="#F2B8B8"', dot)
            self.assertNotIn('BGCOLOR="#B4E4E3"', dot)
            self.assertIn('>!</FONT>', dot)
            self.graphviz(dot)

    def test_root_markdown_callout(self):
        dot = self.render(['# Root', '\t: fname=out.jpg md', '\t: * $ Success'])
        self.assertEqual(2, dot.count('BGCOLOR="#B8E3B4"'))
        self.graphviz(dot)

    def test_noheader_preserves_body_and_optional_symbols(self):
        for mode in ('md', 'markdown', 'block', 'verbatim'):
            for symbols in ('', ' symb=book:star sym1gf35'):
                for theme in ('default', 'nord'):
                    with self.subTest(mode=mode, symbols=symbols, theme=theme):
                        attrs = mode + ' noheader cteal' + symbols
                        dot = self.render(self.outline('Body text', attrs, 'Hidden; heading'), theme)
                        self.assertNotIn('Hidden', dot)
                        self.assertNotIn('heading', dot)
                        self.assertIn('Body', dot)
                        self.assertNotIn('GVMM_BODY_BOUNDARY', dot)
                        self.assertEqual(2 if symbols else 0, dot.count('FACE="FontAwesome"'))
                        if symbols:
                            self.assertIn('POINT-SIZE="35"', dot)
                        else:
                            self.assertNotIn('<TR><TD></TD></TR>', dot)
                        self.graphviz(dot)

    def test_noheader_empty_body_and_sibling(self):
        for mode in ('md', 'block'):
            for symbols in ('', ' symb=book'):
                with self.subTest(mode=mode, symbols=symbols):
                    lines = self.outline('', mode + ' noheader' + symbols, 'Hidden')
                    lines += ['\t# Visible sibling', '\t\t: node']
                    dot = self.render(lines)
                    self.assertNotIn('Hidden', dot)
                    self.assertIn('Visible', dot)
                    self.graphviz(dot)

    def test_block_header_symbols_with_font_size_and_blank_lines(self):
        body = '\n* First sample\n  continued sample\n* Second sample\n  - final detail\n'
        for mode in ('block', 'verbatim'):
            for header in ('', ' noheader'):
                with self.subTest(mode=mode, header=header):
                    attrs = mode + ' csand10 f16 fontcomic El1it symb=book:star sym1gf30' + header
                    dot = self.render(self.outline(body, attrs, 'Sample heading'))
                    self.assertEqual(2, dot.count('FACE="FontAwesome"'))
                    self.assertIn('POINT-SIZE="30"', dot)
                    self.assertIn('First', dot)
                    self.assertNotIn('<FONT POINT-SIZE="16"></FONT>', dot)
                    if header:
                        self.assertNotIn('Sample', dot)
                    else:
                        self.assertIn('<B><U><FONT>Sample', dot)
                    self.graphviz(dot)

    def test_block_symbols_do_not_shift_header_or_body_selectors(self):
        import re
        for selector in ('l1r', 'l1w1r', 'hl1r', 'hl1w1r', 'El1it'):
            with self.subTest(selector=selector):
                attrs = 'block ' + selector
                plain = self.render(self.outline('\nFirst\nSecond\n', attrs, 'Sample heading'))
                icon = self.render(self.outline('\nFirst\nSecond\n', attrs + ' symb=book', 'Sample heading'))
                node = lambda dot: next(line for line in dot.splitlines() if 'node101[' in line)
                without_icon = re.sub(r'<TR><TD[^>]*><FONT FACE="FontAwesome".*?</TR>', '', node(icon))
                self.assertEqual(node(plain), without_icon)
                self.graphviz(icon)

    def test_block_line_font_sizes_override_default_in_either_order(self):
        from xml.etree import ElementTree
        body = '\nAlpha\n\nCharlie\n\nEcho\n\nGolf\nHotel\n\nJuliet\n\nLima\n'
        for mode in ('block', 'verbatim', 'draw'):
            for attrs in ('f16 l[1,5,10]f10fm', 'l[1,5,10]f10fm f16'):
                with self.subTest(mode=mode, attrs=attrs):
                    dot = self.render(self.outline(body, mode + ' fontcomic ' + attrs))
                    self.assertEqual(3, dot.count('POINT-SIZE="10"'))
                    self.graphviz(dot)
                    if shutil.which('dot'):
                        svg = subprocess.run(['dot', '-Tsvg'], input=dot.encode(), capture_output=True, check=True)
                        text = {element.text.strip(): element.attrib
                                for element in ElementTree.fromstring(svg.stdout).iter('{http://www.w3.org/2000/svg}text')
                                if element.text}
                        for word in ('Alpha', 'Echo', 'Juliet'):
                            self.assertEqual('10.00', text[word]['font-size'])
                            self.assertIn('Mono', text[word]['font-family'])
                        for word in ('Charlie', 'Golf', 'Hotel', 'Lima'):
                            self.assertEqual('16.00', text[word]['font-size'])

    def test_block_font_size_last_selector_wins(self):
        dot = self.render(self.outline('\nAlpha\nBeta\n', 'block f16 l1f10 El2f12'))
        self.assertIn('<FONT POINT-SIZE="16"><FONT POINT-SIZE="10"><FONT POINT-SIZE="12">', dot)
        self.graphviz(dot)

    def test_noheader_empty_heading_keeps_body_and_symbols(self):
        for mode in ('md', 'block'):
            for title in ('', ' '):
                with self.subTest(mode=mode, title=title):
                    lines = self.outline('Body text', mode + ' noheader symb=book:star', title)
                    lines += ['\t# Sibling', '\t\t: node']
                    dot = self.render(lines)
                    self.assertIn('Body', dot)
                    self.assertIn('Sibling', dot)
                    self.assertEqual(2, dot.count('FACE="FontAwesome"'))
                    self.graphviz(dot)

    def test_noheader_keeps_block_body_line_formatting(self):
        dot = self.render(self.outline('First\nSecond', 'block noheader l1r hl1b'))
        self.assertNotIn('Markdown', dot)
        self.assertIn('First', dot)
        self.assertIn('Second', dot)
        self.assertIn('<FONT COLOR="#B30000">', dot)
        plain = self.render(self.outline('First\nSecond', 'block l1r hl1b'))
        body_rows = lambda rendered: [row.split('</TR>', 1)[0]
                                      for row in rendered.split('<TR>')
                                      if 'First' in row or 'Second' in row]
        self.assertEqual(body_rows(plain), body_rows(dot))
        self.graphviz(dot)

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

    def test_markdown_layout_aliases(self):
        source = '* ! First item\n  - nested item\n* Second item'
        for root in (False, True):
            def render(attrs):
                if root:
                    return self.render(['# Root', '\t: fname=out.jpg md ' + attrs] +
                                       ['\t: ' + line for line in source.splitlines()])
                return self.render(self.outline(source, 'md noheader symb=book ' + attrs))
            for long, short, value in (('md_width', 'mdw', '180'),
                                       ('md_list_spacing', 'mdls', '0'),
                                       ('md_list_indent', 'mdli', '48')):
                with self.subTest(root=root, option=short):
                    expected = render(long + '=' + value)
                    self.assertEqual(expected, render(short + '=' + value))
                    for attrs in (f'{short}=99 {long}={value}', f'{long}={value} {short}=99'):
                        self.assertEqual(expected, render(attrs))
                    with self.assertRaisesRegex(ValueError, long):
                        render(short + '=-1')
            dot = render('mdw=180 mdls=8 mdli=32')
            self.assertEqual(render('md_width=180 md_list_spacing=8 md_list_indent=32'), dot)
            self.graphviz(dot)

    def test_list_layout_options_validate_for_child_and_root(self):
        for option in ('md_list_spacing', 'md_list_indent'):
            for value in ('bad', '-1', 'nan', 'inf', '""'):
                for root in (False, True):
                    with self.subTest(option=option, value=value, root=root):
                        attrs = 'md ' + option + '=' + value
                        lines = (['# Root', '\t: fname=out.jpg ' + attrs, '\t: * item']
                                 if root else self.outline('* item', attrs))
                        with self.assertRaisesRegex(ValueError, option):
                            self.render(lines)

    def test_list_layout_options_preserve_callouts_and_nested_lists(self):
        source = '* ! **warning**\n  - nested\n  - [x] task\n* plain\n\n1. ordered\n2. second'
        for spacing in (0, 12):
            with self.subTest(spacing=spacing):
                dot = self.render(self.outline(source,
                    f'md noheader symb=book md_list_spacing={spacing} md_list_indent=48'))
                self.assertIn('WIDTH="42"', dot)
                self.assertEqual(2, dot.count('BGCOLOR="#F2B8B8"'))
                self.assertIn('☑', dot)
                self.assertIn('FACE="FontAwesome"', dot)
                self.assertEqual(3 if spacing else 0,
                                 dot.count('COLSPAN="2" HEIGHT="12"'))
                self.graphviz(dot)
        root = self.render(['# Root', '\t: fname=out.jpg md md_list_spacing=12 md_list_indent=48',
                            '\t: * first', '\t: * second'])
        self.assertIn('COLSPAN="2" HEIGHT="12"', root)
        self.assertIn('WIDTH="42"', root)
        self.graphviz(root)

    @unittest.skipUnless(shutil.which('dot'), 'Graphviz is required')
    def test_list_spacing_changes_rendered_height(self):
        heights = []
        for spacing in (0, 8, 20):
            dot = self.render(self.outline('* first\n* second\n* third',
                                          f'md md_list_spacing={spacing}'))
            result = subprocess.run(['dot', '-Tpng'], input=dot.encode(), capture_output=True, check=True)
            with Image.open(io.BytesIO(result.stdout)) as picture:
                heights.append(picture.height)
        self.assertLess(heights[0], heights[1])
        self.assertLess(heights[1], heights[2])

    @unittest.skipUnless(shutil.which('dot'), 'Graphviz is required')
    def test_list_indent_changes_nested_text_position(self):
        from xml.etree import ElementTree
        offsets = []
        for indent in (0, 48):
            dot = self.render(self.outline('* Outer\n  - Nested',
                                          f'md md_list_indent={indent} md_list_spacing=0'))
            result = subprocess.run(['dot', '-Tsvg'], input=dot.encode(), capture_output=True, check=True)
            root = ElementTree.fromstring(result.stdout)
            positions = {text.text: float(text.attrib['x'])
                         for text in root.iter('{http://www.w3.org/2000/svg}text')
                         if text.text in ('Outer', 'Nested')}
            offsets.append(positions['Nested'] - positions['Outer'])
        self.assertGreater(offsets[1], offsets[0])

    def test_highlight_parsing_and_literal_markers(self):
        source = '==plain **bold** *italic* `code` [link](https://example.org)=='
        runs = ParseMarkdown(MarkdownBody(source, '<test>', 'title', 1))[0].runs
        self.assertTrue(all(run.highlight for run in runs))
        for attr in ('bold', 'italic', 'code', 'link'):
            self.assertTrue(any(getattr(run, attr) for run in runs))
        for source in (r'\=\=literal\=\=', '`==code==`', '==unclosed',
                       '== spaced ==', '===literal===', 'a = b'):
            with self.subTest(source=source):
                runs = ParseMarkdown(MarkdownBody(source, '<test>', 'title', 1))[0].runs
                self.assertFalse(any(run.highlight for run in runs))
        runs = ParseMarkdown(MarkdownBody('**==nested==** and ==next==', '<test>', 'title', 1))[0].runs
        self.assertTrue(any(run.bold and run.highlight for run in runs))
        self.assertEqual(['nested', 'next'], [run.text for run in runs if run.highlight])

    def test_highlight_rendering_wraps_and_nested_blocks(self):
        source = '''# ==Heading==

Before ==several **bold** words that wrap across lines== after.

==first\x20\x20
second==

- ==list item==

> ==quote==

| left | right |
| :--- | ---: |
| ==cell== | plain |
'''
        for theme in ('github-light', 'nord'):
            with self.subTest(theme=theme):
                dot = self.render(self.outline(source, 'md md_width=160'), theme)
                self.assertIn('BGCOLOR="#fff2a8"', dot)
                self.assertIn('COLOR="#202020"', dot)
                self.assertIn('<B>bold</B>', dot)
                self.assertNotIn('==', dot)
                self.graphviz(dot)

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
