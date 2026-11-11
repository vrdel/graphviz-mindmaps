import io
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import unquote

from PIL import Image

from graphviz_mindmaps.cli import build_runtime, read_input_lines
from graphviz_mindmaps.model.document import MarkdownBody, RenderSession
from graphviz_mindmaps.parser.markdown import DecodeMarkdownBody, ParseMarkdown, PrepareMarkdownBodies
from graphviz_mindmaps.parser.outline import ExtractMindmapBlocks
from graphviz_mindmaps.render.dot import GenDot
from graphviz_mindmaps.render.label_html import ApplyInlineBacktickBold
from graphviz_mindmaps.render.markdown import RenderMarkdown
from graphviz_mindmaps.theme import ApplyTheme, PeleThemeColors


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

    def test_markdown_title_colors_select_positions_and_follow_theme(self):
        from graphviz_mindmaps.constants import fontcolor
        source = '\n\n'.join('#' * level + f' Heading{position}'
                              for position, level in enumerate((3, 1, 5, 2, 1, 6, 2), 1))
        source += '\n\nOrdinaryBody'
        for root in (False, True):
            for theme in ('default', 'nord'):
                attrs = 'md mt[1,5]r mt7b'
                lines = (['# OutlineTitle', '\t: fname=out.jpg ' + attrs] +
                         ['\t: ' + line for line in source.splitlines()]
                         if root else self.outline(source, attrs, 'OutlineTitle'))
                with self.subTest(root=root, theme=theme):
                    dot = self.render(lines, theme)
                    alternate = [line.replace('mt[1,5]r', 'mt[1-5]r') for line in lines]
                    self.assertEqual(dot, self.render(alternate, theme))
                    for position in range(1, 8):
                        ink = fontcolor['r'] if position <= 5 else fontcolor['b'] if position == 7 else fontcolor['def']
                        self.assertRegex(dot, r'<FONT [^>]*COLOR="' + ink + r'"><B>Heading' + str(position) + r'</B></FONT>')
                    self.assertRegex(dot, r'<FONT [^>]*COLOR="' + fontcolor['def'] + r'">OrdinaryBody</FONT>')
                    self.assertNotRegex(dot, r'<FONT [^>]*COLOR="' + fontcolor['r'] + r'">(?:<B>)?OutlineTitle')
                    self.graphviz(dot)

    def test_markdown_title_color_ranges_overrides_nested_headings_and_node_scope(self):
        from graphviz_mindmaps.constants import fontcolor
        source = ('## Top\n\n## **Strong** and `code`\n\n> ## Quoted\n\n'
                  '- item\n\n  ## Listed\n\n::: info Container\n## Inside\n:::\n\n## Last')
        attrs = 'md mt[6-1]b mt2r mt[4-5]r mt4g'
        lines = self.outline(source, attrs)
        lines += ['\t# sibling', '\t\t: md', '\t\t: # SiblingBody']
        dot = self.render(lines)
        for text, color in (('Top', 'b'), ('Strong', 'r'), ('code', 'r'), ('Quoted', 'b'),
                            ('Listed', 'g'), ('Inside', 'r'), ('Last', 'b'), ('SiblingBody', 'def')):
            self.assertRegex(dot, r'<FONT [^>]*COLOR="' + fontcolor[color] + r'"><B>' + text + r'</B></FONT>')
        self.graphviz(dot)

    def test_markdown_title_colors_validate_selectors_with_outline_location(self):
        for token in ('mt[]r', 'mt[1,]r', 'mt[1-]r', 'mt[1,,2]r', 'mt[1,5]z', 'mt0r', 'mt[0-5]r'):
            for root in (False, True):
                attrs = 'md ' + token
                lines = (['# Root', '\t: fname=out.jpg ' + attrs, '\t: # Heading']
                         if root else self.outline('# Heading', attrs))
                with self.subTest(token=token, root=root), self.assertRaisesRegex(
                    ValueError, r'<input>:\d+: Markdown node .*Markdown title',
                ):
                    self.render(lines)

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

    def test_custom_containers_render_in_root_and_child_nodes(self):
        source = ('::: warning **Migration** checklist\n'
                  'A paragraph with *formatting*.\n\n'
                  '* [x] export\n* [ ] import\n\n'
                  'Another paragraph.\n:::\nOutside')
        for root in (False, True):
            for theme in ('github-light', 'nord'):
                with self.subTest(root=root, theme=theme):
                    lines = (['# Root', '\t: fname=out.jpg md'] +
                             ['\t: ' + line for line in source.split('\n')]
                             if root else self.outline(source, 'md md_width=180'))
                    dot = self.render(lines, theme)
                    self.assertIn('BGCOLOR="#F1E6A8"', dot)
                    self.assertIn('<B>Migration</B>', dot)
                    self.assertIn('<I>formatting</I>', dot)
                    self.assertIn('☑', dot)
                    self.assertIn('Outside', dot)
                    self.assertNotIn(':::', dot)
                    self.graphviz(dot)

    def test_container_names_titles_and_implicit_close(self):
        for name, color in (('note', '#B4E4E3'), ('tip', '#B8E3B4'),
                            ('danger', '#F2B8B8'), ('custom-name', '#E0E0E0')):
            with self.subTest(name=name):
                blocks = ParseMarkdown(MarkdownBody(
                    f'::: {name}\nbody', '<test>', 'test', 1))
                self.assertEqual(1, len(blocks))
                self.assertEqual('container', blocks[0].kind)
                self.assertEqual(color, blocks[0].callout)
                self.assertEqual(name.replace('-', ' ').capitalize(),
                                 ''.join(run.text for run in blocks[0].runs))

    def test_nested_containers_preserve_code_and_following_paragraph(self):
        source = (':::: note Outer\n::: tip Inner\ninside\n:::\n'
                  '```text\n::::\n```\n::::\nafter')
        blocks = ParseMarkdown(MarkdownBody(source, '<test>', 'test', 1))
        self.assertEqual(['container', 'paragraph'], [block.kind for block in blocks])
        self.assertEqual(['container', 'fence'],
                         [block.kind for block in blocks[0].children])
        self.assertEqual('::::\n', blocks[0].children[1].source)
        self.graphviz(self.render(self.outline(source)))

    def test_containers_in_lists_and_quotes(self):
        for source in ('* item\n\n  ::: note\n  body\n  :::\n\n* sibling',
                       '> ::: note\n> body\n> :::\n\nafter'):
            with self.subTest(source=source):
                dot = self.render(self.outline(source))
                self.assertIn('BGCOLOR="#B4E4E3"', dot)
                self.assertNotIn(':::', dot)
                self.graphviz(dot)

    def test_container_fences_are_literal_in_code_or_when_escaped(self):
        source = ('\\::: note\nliteral\n\n'
                  '```text\n::: tip\ncode\n:::\n```\n\n'
                  '    ::: danger\n    indented')
        blocks = ParseMarkdown(MarkdownBody(source, '<test>', 'test', 1))
        self.assertEqual(['paragraph', 'fence', 'code_block'],
                         [block.kind for block in blocks])

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

    def test_dash_lists_render_unicode_minus(self):
        source = ('- minus\n  * nested bullet\n- ! callout\n'
                  '- [x] done\n- [ ] pending\n\n* star\n\n+ plus\n\n1. numbered')
        for root in (False, True):
            with self.subTest(root=root):
                lines = (['# Root', '\t: fname=out.jpg md'] +
                         ['\t: ' + line for line in source.split('\n')]
                         if root else self.outline(source))
                dot = self.render(lines)
                self.assertEqual(2, dot.count('>−&#160;</TD>'))
                self.assertEqual(3, dot.count('>•&#160;</TD>'))
                self.assertIn('>− ☑&#160;</TD>', dot)
                self.assertIn('>− ☐&#160;</TD>', dot)
                self.assertIn('>1.&#160;</TD>', dot)
                self.assertEqual(2, dot.count('BGCOLOR="#F2B8B8"'))
                self.graphviz(dot)

    def test_task_items_preserve_bullets_and_checkboxes(self):
        for marker, rendered in (('*', '•'), ('+', '•'), ('-', '−')):
            with self.subTest(marker=marker):
                source = (f'{marker} Ubuntu 26.04 LTS migracija\n'
                          f'{marker} window focus ring\n'
                          '  - da mogu konacno setati ispravnim redoslijedom\n'
                          '    fokusiranih prozora\n'
                          f'{marker} [x] Obsidian automated Canvas export\n'
                          f'{marker} [X] uppercase\n'
                          f'{marker} [ ] pending')
                dot = self.render(self.outline(source, 'md ccyan md_width=180'))
                self.assertEqual(2, dot.count(f'>{rendered} ☑&#160;</TD>'))
                self.assertIn(f'>{rendered} ☐&#160;</TD>', dot)
                self.assertNotIn('[x]', dot)
                self.assertNotIn('[X]', dot)
                self.assertNotIn('[ ]', dot)
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

    def test_block_body_hash_heading_does_not_end_node(self):
        source = ('\nNOTES.md\n# Sample heading\n\n'
                  'A sample paragraph after the heading.\n'
                  'Use `sample-command` here.\n')
        for mode in ('block rawmarkers', 'block', 'verbatim', 'draw'):
            for marker in (':', '|', ';'):
                with self.subTest(mode=mode, marker=marker):
                    lines = self.outline(source, mode)
                    lines[4:] = [line.replace('\t\t:', '\t\t' + marker, 1)
                                 for line in lines[4:]]
                    lines += ['\t\t# child', '\t\t\t: node', '\t# sibling', '\t\t: node']
                    blocks = ExtractMindmapBlocks(lines, ApplyInlineBacktickBold)
                    self.assertEqual(4, sum(line.lstrip().startswith('# ') for line in blocks[0]))
                    dot = self.render(lines)
                    self.assertIn('#&nbsp;Sample&nbsp;heading', dot)
                    self.assertIn('sample-command', dot)
                    self.assertIn('child', dot)
                    self.assertIn('sibling', dot)
                    self.graphviz(dot)

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

    def test_svgbob_standalone_nodes_preserve_source_hide_headers_and_grow_naturally(self):
        source = '+---------+     +----------+\n| outline |---->| renderer |\n+---------+     +----------+'
        path = Path(self.temp.name, 'svgbob.png')
        Image.new('RGBA', (1200, 1400), (20, 30, 40, 255)).save(path)
        for root in (False, True):
            lines = (['# Hidden diagram title', '\t: fname=out.jpg svgbob mdw=20'] +
                     ['\t: ' + line for line in source.splitlines()]
                     if root else self.outline(source, 'svgbob mdw=20', 'Hidden diagram title'))
            with self.subTest(root=root), patch(
                'graphviz_mindmaps.render.markdown.RenderSvgbobImage', return_value=path,
            ) as render:
                dot = self.render(lines, 'nord')
                self.assertEqual(source + '\n', render.call_args.args[0])
                self.assertEqual([str(path)], re.findall(r'<IMG SRC="([^"]+)"', dot))
                self.assertNotIn('Hidden&nbsp;diagram', dot)
                node = 'node1' if root else 'node101'
                attrs = re.search(r'\b' + node + r'\[([^\n]+)', dot).group(1)
                self.assertIn('fillcolor="transparent"', attrs)
                self.assertEqual(PeleThemeColors('nord')['--pele-fg'], render.call_args.kwargs['foreground'])
                self.graphviz(dot)
        lines = self.outline(source, 'svgbob ccyan', 'Diagram')
        lines += ['\t\t# child', '\t\t\t: node', '\t# sibling', '\t\t: node']
        with patch('graphviz_mindmaps.render.markdown.RenderSvgbobImage', return_value=path):
            dot = self.render(lines)
        from graphviz_mindmaps.constants import vrbtcolors
        self.assertIn('fillcolor="' + vrbtcolors['ccyan'] + '"', dot)
        self.assertIn('child', dot)
        self.assertIn('sibling', dot)

    def test_svgbob_fences_render_nested_and_follow_markdown_wrapping(self):
        path = Path(self.temp.name, 'svgbob.png')
        Image.new('RGBA', (1000, 1100), (20, 30, 40, 255)).save(path)
        fence = '```svgbob\n+---+\n| A |\n+---+\n```'
        for source in (fence, '> ' + fence.replace('\n', '\n> '),
                       '- item\n\n  ' + fence.replace('\n', '\n  '),
                       '::: info Diagram\n' + fence + '\n:::'):
            for wrap in ('on', 'off'):
                for root in (False, True):
                    attrs = 'md mdw=100 md_wrap=' + wrap
                    lines = (['# Root', '\t: fname=out.jpg ' + attrs] +
                             ['\t: ' + line for line in source.splitlines()]
                             if root else self.outline(source, attrs))
                    with self.subTest(source=source, wrap=wrap, root=root), patch(
                        'graphviz_mindmaps.render.markdown.RenderSvgbobImage', return_value=path,
                    ) as render:
                        dot = self.render(lines)
                        self.assertEqual('+---+\n| A |\n+---+\n', render.call_args.args[0])
                        image = re.findall(r'<IMG SRC="([^"]+)"', dot)[0]
                        if wrap == 'off':
                            self.assertEqual(str(path), image)
                        else:
                            with Image.open(image) as resized:
                                self.assertLessEqual(resized.width, 100)
                                self.assertLessEqual(resized.height, 900)

    def test_svgbob_stroke_width_in_root_child_and_nested_fences_is_node_local(self):
        path = Path(self.temp.name, 'svgbob.png')
        Image.new('RGBA', (100, 50), (20, 30, 40, 255)).save(path)
        for mode in ('md', 'svgbob'):
            source = '> ```svgbob\n> +---+\n> | A |\n> +---+\n> ```' if mode == 'md' else '+---+\n| A |\n+---+'
            for root in (False, True):
                def lines(option):
                    attrs = mode + ' ' + option
                    return (['# Root', '\t: fname=out.jpg ' + attrs] +
                            ['\t: ' + line for line in source.splitlines()]
                            if root else self.outline(source, attrs))

                with self.subTest(mode=mode, root=root), patch(
                    'graphviz_mindmaps.render.markdown.RenderSvgbobImage', return_value=path,
                ) as render:
                    self.render(lines(''))
                    self.assertEqual(2, render.call_args.kwargs['stroke_width'])
                    self.render(lines('svgbob_stroke_width=0.5'))
                    self.assertEqual(0.5, render.call_args.kwargs['stroke_width'])
                    siblings = lines('svgbob_stroke_width=4') + [
                        '\t# sibling', '\t\t: svgbob', '\t\t: +---+']
                    self.render(siblings)
                    self.assertEqual(2, render.call_args.kwargs['stroke_width'])
                    for value in ('-1', 'nan', 'inf', 'text'):
                        with self.assertRaisesRegex(ValueError, r'<input>:\d+: .*svgbob_stroke_width'):
                            self.render(lines('svgbob_stroke_width=' + value))

    def test_svgbob_conflicting_modes_and_errors_report_outline_location(self):
        for attrs in ('svgbob md', 'svgbob mermaid', 'svgbob code python',
                      'svgbob block', 'svgbob draw', 'svgbob verbatim'):
            with self.subTest(attrs=attrs), self.assertRaisesRegex(ValueError, 'mutually exclusive'):
                PrepareMarkdownBodies(self.outline('+--+', attrs))
        for mode, source, location in (('svgbob', '+--+', "<input>:5: Svgbob node"),
                                       ('md', '```svgbob\n+--+\n```', "<input>:5: Markdown node")):
            with patch('graphviz_mindmaps.render.markdown.RenderSvgbobImage',
                       side_effect=ValueError('Svgbob is not installed')):
                with self.assertRaisesRegex(ValueError, location + ".*Svgbob is not installed"):
                    self.render(self.outline(source, mode))

    def test_mermaid_theme_uses_root_override_and_does_not_leak_between_maps(self):
        path = Path(self.temp.name, 'diagram.png')
        Image.new('RGBA', (160, 80), (220, 240, 240, 255)).save(path)
        for mode in ('md', 'mermaid'):
            source = 'flowchart LR\nA-->B'
            if mode == 'md':
                source = '```mermaid\n' + source + '\n```'
            for root in (False, True):
                lines = (['# Root', '\t: fname=out.jpg ' + mode] +
                         ['\t: ' + line for line in source.splitlines()]
                         if root else self.outline(source, mode))
                with self.subTest(mode=mode, root=root), patch(
                    'graphviz_mindmaps.render.markdown.RenderMermaidImage', return_value=path,
                ) as render:
                    self.render(lines, 'github-light')
                    self.assertEqual(PeleThemeColors('github-light'), render.call_args.kwargs['colors'])
                    overridden = list(lines)
                    overridden[1] += ' theme=nord'
                    self.render(overridden, 'github-light')
                    self.assertEqual(PeleThemeColors('nord'), render.call_args.kwargs['colors'])
                    self.render(lines, 'github-light')
                    self.assertEqual(PeleThemeColors('github-light'), render.call_args.kwargs['colors'])

    def test_mermaid_inherits_containing_node_font_and_size(self):
        path = Path(self.temp.name, 'diagram.png')
        Image.new('RGBA', (160, 80), (220, 240, 240, 255)).save(path)
        for mode in ('md', 'mermaid'):
            source = 'flowchart LR\nA-->B'
            if mode == 'md':
                source = '```mermaid\n' + source + '\n```'
            for token, face in (('fontmono', 'Dejavu Sans Mono'),
                                ('fontserif', 'Dejavu Serif'),
                                ('fontsans', 'Dejavu Sans')):
                with self.subTest(mode=mode, font=token), patch(
                    'graphviz_mindmaps.render.markdown.RenderMermaidImage', return_value=path,
                ) as render:
                    self.render(self.outline(source, mode + ' ' + token + ' f22'))
                    self.assertEqual(face, render.call_args.kwargs['face'])
                    self.assertEqual(22, render.call_args.kwargs['size'])

    def test_mermaid_font_option_defaults_validation_and_node_scope(self):
        path = Path(self.temp.name, 'diagram.png')
        Image.new('RGBA', (160, 80), (220, 240, 240, 255)).save(path)
        for mode in ('md', 'mermaid'):
            source = 'flowchart LR\nA-->B'
            if mode == 'md':
                source = '```mermaid\n' + source + '\n```'
            for root in (False, True):
                def lines(option):
                    attrs = mode + ' fontmono f22 ' + option
                    return (['# Root', '\t: fname=out.jpg ' + attrs] +
                            ['\t: ' + line for line in source.splitlines()]
                            if root else self.outline(source, attrs))

                with self.subTest(mode=mode, root=root), patch(
                    'graphviz_mindmaps.render.markdown.RenderMermaidImage', return_value=path,
                ) as render:
                    self.render(lines(''))
                    inherited = render.call_args.kwargs
                    self.render(lines('mermaid_font=on'))
                    self.assertEqual(inherited, render.call_args.kwargs)
                    self.render(lines('mermaid_font=off'))
                    self.assertNotIn('face', render.call_args.kwargs)
                    self.assertNotIn('size', render.call_args.kwargs)
                    # A sibling with no option still inherits its font.
                    siblings = lines('mermaid_font=off') + [
                        '\t# Sibling', '\t\t: mermaid fontserif',
                        '\t\t: flowchart LR', '\t\t: A-->B']
                    self.render(siblings)
                    self.assertEqual('Dejavu Serif', render.call_args.kwargs['face'])
                    for value in ('yes', 'auto', '0'):
                        with self.assertRaisesRegex(ValueError, 'mermaid_font must be on or off'):
                            self.render(lines('mermaid_font=' + value))

    def test_standalone_mermaid_preserves_source_and_hides_header(self):
        source = 'flowchart LR\n  A["literal *text* :-)"] --> B["# destination"]\n'
        path = Path(self.temp.name, 'diagram.png')
        Image.new('RGBA', (160, 80), (220, 240, 240, 255)).save(path)
        for root in (False, True):
            lines = (['# Hidden diagram title', '\t: fname=out.jpg mermaid mdw=220'] +
                     ['\t: ' + line for line in source.split('\n')]
                     if root else self.outline(source, 'mermaid mdw=220 ccyan', 'Hidden diagram title'))
            prepared = PrepareMarkdownBodies(lines)
            _, body = DecodeMarkdownBody(prepared[0 if root else 2].lstrip('\t')[2:])
            self.assertTrue(body.mermaid)
            self.assertEqual(source + '\n', body.source)
            with self.subTest(root=root), patch(
                'graphviz_mindmaps.render.markdown.RenderMermaidImage', return_value=path,
            ) as render, patch('graphviz_mindmaps.render.markdown.ParseMarkdown') as markdown:
                dot = self.render(lines)
                self.assertEqual(source + '\n', render.call_args.args[0])
                self.assertIsNone(render.call_args.args[2])
                markdown.assert_not_called()
                self.assertIn('<IMG SRC=', dot)
                self.assertNotIn('Hidden&nbsp;diagram', dot)
                self.assertNotIn('flowchart', dot)
                self.graphviz(dot)

    def test_standalone_mermaid_background_defaults_to_transparent(self):
        from graphviz_mindmaps.constants import vrbtcolors
        path = Path(self.temp.name, 'diagram.png')
        Image.new('RGBA', (160, 80), (0, 0, 0, 0)).save(path)
        for theme in ('default', 'nord'):
            for root in (False, True):
                for attrs, expected in (('', 'transparent'), ('ccyan', None),
                                        ('root_bg="#123456"' if root else 'bg="#123456"', '#123456')):
                    mode = 'mermaid ' + attrs
                    lines = (['# Root', '\t: fname=out.jpg ' + mode,
                              '\t: flowchart LR', '\t: A-->B']
                             if root else self.outline('flowchart LR\nA-->B', mode))
                    with self.subTest(theme=theme, root=root, attrs=attrs), patch(
                        'graphviz_mindmaps.render.markdown.RenderMermaidImage', return_value=path,
                    ):
                        dot = self.render(lines, theme)
                        node = 'node1' if root else 'node101'
                        rendered = re.search(r'\b' + node + r'\[([^\n]+)', dot).group(1)
                        self.assertIn('fillcolor="' + (expected or vrbtcolors['ccyan']) + '"', rendered)
                        self.graphviz(dot)

    def test_standalone_mermaid_does_not_resize_wide_or_tall_diagrams(self):
        path = Path(self.temp.name, 'large-diagram.png')
        Image.new('RGBA', (1200, 1400), (220, 240, 240, 255)).save(path)
        for root in (False, True):
            for width in ('100', '2000'):
                attrs = 'mermaid mdw=' + width
                lines = (['# Root', '\t: fname=out.jpg ' + attrs,
                          '\t: flowchart LR', '\t: A-->B']
                         if root else self.outline('flowchart LR\nA-->B', attrs))
                with self.subTest(root=root, width=width), patch(
                    'graphviz_mindmaps.render.markdown.RenderMermaidImage', return_value=path,
                ) as render:
                    dot = self.render(lines)
                    self.assertIsNone(render.call_args.args[2])
                    self.assertEqual([str(path)], re.findall(r'<IMG SRC="([^"]+)"', dot))
                    self.graphviz(dot)
        self.assertFalse(list(Path(self.temp.name).glob('md-image-*')))

    def test_standalone_mermaid_keeps_children_siblings_and_node_options(self):
        path = Path(self.temp.name, 'diagram.png')
        Image.new('RGBA', (160, 80), (220, 240, 240, 255)).save(path)
        lines = self.outline('flowchart LR\nA-->B', 'mermaid ccyan symb=book', 'Hidden')
        lines += ['\t\t# Child', '\t\t\t: node', '\t# Sibling', '\t\t: node']
        with patch('graphviz_mindmaps.render.markdown.RenderMermaidImage', return_value=path):
            dot = self.render(lines)
        self.assertNotIn('Hidden', dot)
        self.assertIn('Child', dot)
        self.assertIn('Sibling', dot)
        self.assertIn('FACE="FontAwesome"', dot)
        self.graphviz(dot)

    def test_standalone_mermaid_rejects_conflicting_modes_and_reports_location(self):
        for attrs in ('mermaid md', 'markdown mermaid', 'mermaid code python',
                      'mermaid block', 'mermaid draw', 'mermaid verbatim'):
            with self.subTest(attrs=attrs), self.assertRaisesRegex(ValueError, 'mutually exclusive'):
                PrepareMarkdownBodies(self.outline('flowchart LR\nA-->B', attrs))
        with patch('graphviz_mindmaps.render.markdown.RenderMermaidImage',
                   side_effect=ValueError('Pele rendering failed: invalid diagram')):
            with self.assertRaisesRegex(ValueError, "<input>:5: Mermaid node 'Diagram': Pele"):
                self.render(self.outline('bad diagram', 'mermaid', 'Diagram'))

    def test_unwrapped_mermaid_fences_keep_natural_width_and_height(self):
        path = Path(self.temp.name, 'large-diagram.png')
        Image.new('RGBA', (1200, 1000), (220, 240, 240, 255)).save(path, dpi=(96, 96))
        fence = '```mermaid\nflowchart LR\nA-->B\n```'
        for root in (False, True):
            for source in ('Before\n\n' + fence + '\n\nAfter',
                           '::: note\n' + fence + '\n:::',
                           '* Diagram\n\n' + '\n'.join('  ' + line for line in fence.splitlines()),
                           '\n'.join('> ' + line for line in fence.splitlines())):
                lines = (['# Root', '\t: fname=out.jpg md mdw=100 md_wrap=off'] +
                         ['\t: ' + line for line in source.splitlines()]
                         if root else self.outline(source, 'md noheader mdw=100 md_wrap=off'))
                with self.subTest(root=root, source=source), patch(
                    'graphviz_mindmaps.render.markdown.RenderMermaidImage', return_value=path,
                ) as render:
                    dot = self.render(lines)
                    render.assert_called_once()
                    self.assertIsNone(render.call_args.args[2])
                    self.assertEqual([str(path)], re.findall(r'<IMG SRC="([^"]+)"', dot))
                    if shutil.which('dot'):
                        result = subprocess.run(['dot', '-Tplain'], input=dot.encode(),
                                                capture_output=True, check=True)
                        target = 'node node1 ' if root else 'node node101 '
                        node = next(line.split() for line in result.stdout.decode().splitlines()
                                    if line.startswith(target))
                        # Graphviz reports points; the PNG's natural size is at 96 dpi.
                        self.assertGreaterEqual(float(node[4]) * 72, 1200 * 72 / 96)
                        self.assertGreaterEqual(float(node[5]) * 72, 1000 * 72 / 96)
                    self.graphviz(dot)
        self.assertFalse(list(Path(self.temp.name).glob('md-image-*')))

    def test_mermaid_fences_embed_images_in_root_child_and_nested_blocks(self):
        path = Path(self.temp.name, 'diagram.png')
        Image.new('RGBA', (800, 200), (243, 243, 243, 255)).save(path)
        fence = '```mermaid\nflowchart LR\nA-->B\n```'
        for root in (False, True):
            for source in (fence, '::: note\n' + fence + '\n:::',
                           '* Diagram\n\n' + '\n'.join('  ' + line for line in fence.splitlines()),
                           '\n'.join('> ' + line for line in fence.splitlines())):
                with self.subTest(root=root, source=source), patch(
                    'graphviz_mindmaps.render.markdown.RenderMermaidImage', return_value=path,
                ) as render:
                    lines = (['# Root', '\t: fname=out.jpg md mdw=200'] +
                             ['\t: ' + line for line in source.splitlines()]
                             if root else self.outline(source, 'md mdw=200'))
                    dot = self.render(lines)
                    render.assert_called_once()
                    self.assertEqual('flowchart LR\nA-->B\n', render.call_args.args[0])
                    self.assertLessEqual(render.call_args.args[2], 200)
                    images = re.findall(r'<IMG SRC="([^"]+)"', dot)
                    self.assertEqual(1, len(images))
                    with Image.open(images[0]) as image:
                        self.assertLessEqual(image.width, 200)
                    self.assertNotIn('flowchart', dot)
                    self.graphviz(dot)

    def test_code_background_is_transparent_including_resized_blocks(self):
        for source in ('```python\nvalue = 123456789\n```', '    value = 123456789'):
            for width in (420, 80):
                with self.subTest(source=source, width=width):
                    dot = self.render(self.outline(source, f'md bg=seagreen1 md_width={width}'))
                    paths = re.findall(r'<IMG SRC="([^"]+)"', dot)
                    self.assertTrue(paths)
                    for path in paths:
                        with Image.open(path) as image:
                            self.assertEqual('RGBA', image.mode)
                            self.assertEqual(0, image.getpixel((0, 0))[3])
                            self.assertGreater(image.getchannel('A').getextrema()[1], 0)
                    self.graphviz(dot)

    @unittest.skipUnless(shutil.which('dot'), 'Graphviz is required')
    def test_horizontal_rule_does_not_add_empty_text_lines(self):
        from xml.etree import ElementTree
        for source in ('Before\n\n---\n\nAfter', '---', 'Before\n\n---', '---\n\nAfter'):
            with self.subTest(source=source):
                dot = self.render(self.outline(source, 'md noheader'))
                result = subprocess.run(['dot', '-Tsvg'], input=dot.encode(),
                                        capture_output=True, check=True)
                positions = {element.text: float(element.attrib['y'])
                             for element in ElementTree.fromstring(result.stdout).iter('{http://www.w3.org/2000/svg}text')}
                if source == 'Before\n\n---\n\nAfter':
                    self.assertIn('Before', positions)
                    self.assertIn('After', positions)
                    self.assertLess(abs(positions['Before'] - positions['After']), 45)
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

    def test_file_links_use_http_link_styling(self):
        for url in ('file://filename.md', 'file:///tmp/filename.md',
                    'file:///tmp/my%20notes.md', 'FILE:///tmp/filename.md'):
            for source, label in ((f'<{url}>', unquote(url)), (f'[notes]({url})', 'notes'),
                                  (f'[notes][local]\n\n[local]: {url}', 'notes')):
                with self.subTest(source=source):
                    blocks = ParseMarkdown(MarkdownBody(source, '<test>', 'links', 1))
                    self.assertEqual(label, ''.join(run.text for run in blocks[0].runs))
                    self.assertTrue(all(run.link == url for run in blocks[0].runs))
                    dot = self.render(self.outline(source))
                    http = self.render(self.outline(source.replace(url, 'http://this.is.link')))
                    colors = lambda text: set(re.findall(r'<FONT[^>]* COLOR="([^"]+)"', text))
                    self.assertEqual(colors(http), colors(dot))
                    self.assertNotIn('&lt;', dot)
                    self.graphviz(dot)

    def test_file_links_do_not_enable_other_rejected_schemes(self):
        for source in ('[bad](javascript:alert%281%29)', '<javascript:alert%281%29>',
                       '[bad](vbscript:example)', '[bad](data:text/html,example)'):
            with self.subTest(source=source):
                blocks = ParseMarkdown(MarkdownBody(source, '<test>', 'links', 1))
                self.assertTrue(all(not run.link for block in blocks for run in block.runs))

    def test_wrap_preserves_styled_words_and_long_code(self):
        body = MarkdownBody('prefix **some**word and `a long code span` plus more words', '<test>', 'title', 1)
        for spacing in (0, 1):
            result = RenderMarkdown(body, [self.temp.name], width=120, line_spacing=spacing)
            self.assertIn('<BR ALIGN="LEFT"/>' if spacing == 0 else 'HEIGHT="1"', result)
            self.assertNotIn('some</B></FONT><BR', result)
            self.assertNotIn('some</B></FONT></TD>', result)
            self.assertIn('a&#160;long&#160;code&#160;span', result)

    def test_local_image_relative_to_source_and_remote_rejected(self):
        original = Path(self.temp.name, 'sample.png')
        Image.new('RGB', (800, 200), 'red').save(original)
        sourcefile = Path(self.temp.name, 'map.otl')
        sourcefile.write_text('\n'.join(self.outline('![example](sample.png)', 'md md_width=100')))
        self.graphviz(self.render(read_input_lines([str(sourcefile)])))
        with Image.open(original) as image:
            self.assertEqual((800, 200), image.size)
        for url in ('https://example.org/image.png', 'missing.png', 'file:///tmp/x.png'):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, 'Markdown node'):
                self.render(self.outline('![alt](' + url + ')'))

    def test_markdown_wrap_defaults_and_validation(self):
        source = 'first command\nsecond command with several more words'
        for root in (False, True):
            def render(option):
                attrs = 'md mdw=90 ' + option
                return self.render(
                    ['# Root', '\t: fname=out.jpg ' + attrs] +
                    ['\t: ' + line for line in source.splitlines()]
                    if root else self.outline(source, attrs))
            with self.subTest(root=root):
                self.assertEqual(render(''), render('md_wrap=on'))
                self.assertNotEqual(render('md_wrap=on'), render('md_wrap=off'))
                for value in ('yes', 'auto', '0'):
                    with self.assertRaisesRegex(ValueError, 'md_wrap must be on or off'):
                        render('md_wrap=' + value)

    @unittest.skipUnless(shutil.which('dot'), 'Graphviz is required')
    def test_markdown_wrap_off_preserves_source_lines_without_auto_wrapping(self):
        from xml.etree import ElementTree
        source = ('curl -LsSf https://astral.sh/uv/install.sh | sh\n'
                  'uv\nvim .oh-my-zsh/oh-my-zsh.sh <- uv plugin')
        for root in (False, True):
            attrs = 'md noheader fontmono mdw=90 md_wrap=off'
            lines = (['# Root', '\t: fname=out.jpg ' + attrs] +
                     ['\t: ' + line for line in source.splitlines()]
                     if root else self.outline(source, attrs))
            dot = self.render(lines)
            result = subprocess.run(['dot', '-Tsvg'], input=dot.encode(),
                                    capture_output=True, check=True)
            positions = {}
            for element in ElementTree.fromstring(result.stdout).iter('{http://www.w3.org/2000/svg}text'):
                positions.setdefault(float(element.attrib['y']), []).append(element.text or '')
            command_rows = [''.join(parts).replace('\u00a0', ' ') for parts in positions.values()
                            if any(word in ''.join(parts) for word in ('curl', 'uv', 'vim'))]
            with self.subTest(root=root):
                self.assertEqual(source.splitlines(), command_rows)
                self.graphviz(dot)

    @unittest.skipUnless(shutil.which('dot'), 'Graphviz is required')
    def test_markdown_wrap_off_width_follows_content_instead_of_mdw(self):
        sources = (
            'short\nA much longer second line',
            '* short\n* A much longer second line',
            '* ! **Warning**\n* [x] Longer task description',
            '* outer\n  - inner\n  - A much longer nested line',
            '> * short\n> * A much longer quoted line',
            '::: note\n* short\n* A much longer contained line\n:::',
            '==highlighted==\nA much longer second line',
            '| Name | Value |\n| --- | --- |\n| First | A longer value |',
        )
        for root in (False, True):
            def rendered_width(source, width):
                attrs = f'md noheader fontmono md_wrap=off mdw={width}'
                lines = (['# Root', '\t: fname=out.jpg ' + attrs] +
                         ['\t: ' + line for line in source.splitlines()]
                         if root else self.outline(source, attrs))
                dot = self.render(lines)
                result = subprocess.run(['dot', '-Tplain'], input=dot.encode(),
                                        capture_output=True, check=True)
                target = 'node node1 ' if root else 'node node101 '
                node = next(line.split() for line in result.stdout.decode().splitlines()
                            if line.startswith(target))
                return float(node[4])
            for source in sources:
                with self.subTest(root=root, source=source):
                    self.assertEqual(rendered_width(source, 100), rendered_width(source, 800))
            self.assertGreater(rendered_width('* A much longer second line', 100),
                               rendered_width('* short', 800))

    @unittest.skipUnless(shutil.which('dot'), 'Graphviz is required')
    def test_unwrapped_lists_stay_left_aligned_below_wider_paragraphs(self):
        from xml.etree import ElementTree
        lists = ('* Short\n* Tiny\n  - Nested',
                 '1. Short\n2. Tiny\n   - Nested',
                 '* ! **Short**\n* [x] Tiny\n  - Nested')
        for root in (False, True):
            for spacing in (0, 1):
                for listing in lists:
                    source = 'Anchor this paragraph is much longer than the list below it.\n\n' + listing
                    attrs = f'md noheader fontmono md_wrap=off mdlns={spacing}'
                    lines = (['# Root', '\t: fname=out.jpg ' + attrs] +
                             ['\t: ' + line for line in source.splitlines()]
                             if root else self.outline(source, attrs))
                    with self.subTest(root=root, spacing=spacing, listing=listing):
                        dot = self.render(lines)
                        result = subprocess.run(['dot', '-Tsvg'], input=dot.encode(),
                                                capture_output=True, check=True)
                        self.assertFalse(result.stderr, result.stderr.decode())
                        positions = {element.text: float(element.attrib['x'])
                                     for element in ElementTree.fromstring(result.stdout).iter('{http://www.w3.org/2000/svg}text')
                                     if element.text in ('Anchor', 'Short', 'Tiny', 'Nested')}
                        self.assertAlmostEqual(positions['Short'], positions['Tiny'], delta=1)
                        self.assertGreater(positions['Short'], positions['Anchor'])
                        self.assertLess(positions['Short'] - positions['Anchor'], 65)
                        self.assertGreater(positions['Nested'], positions['Short'])
                        self.assertLess(positions['Nested'] - positions['Short'], 65)

    def test_markdown_wrap_off_preserves_nested_formatting_and_is_node_local(self):
        source = '::: note\n* **Alpha**\n  *Beta* ==Gamma==\n:::'
        dot = self.render(self.outline(source, 'md mdw=90 md_wrap=off'))
        for fragment in ('<B>Alpha</B>', '<I>Beta</I>', 'BGCOLOR="#fff2a8"'):
            self.assertIn(fragment, dot)
        self.graphviz(dot)
        lines = self.outline('first\nsecond', 'md md_wrap=off')
        lines += ['\t# Sibling', '\t\t: md', '\t\t: third', '\t\t: fourth']
        dot = self.render(lines)
        self.assertIn('>third</FONT>&#160;<FONT', dot)
        self.assertNotIn('>first</FONT>&#160;<FONT', dot)
        self.graphviz(dot)

    def test_width_validation(self):
        for value in ('zero', '0', '-1', 'nan', 'inf'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'md_width'):
                self.render(self.outline('text', 'md md_width=' + value))

    def test_markdown_line_spacing_validation_and_default(self):
        source = 'First line  \nSecond line'
        self.assertEqual(self.render(self.outline(source)),
                         self.render(self.outline(source, 'md md_line_spacing=1')))
        self.assertNotEqual(self.render(self.outline(source)),
                            self.render(self.outline(source, 'md mdlns=0')))
        for value in ('-1', 'bad', 'nan', 'inf', '""'):
            for root in (False, True):
                with self.subTest(value=value, root=root):
                    attrs = 'md md_line_spacing=' + value
                    lines = (['# Root', '\t: fname=out.jpg ' + attrs, '\t: text']
                             if root else self.outline('text', attrs))
                    with self.assertRaisesRegex(ValueError, 'md_line_spacing'):
                        self.render(lines)

    @unittest.skipUnless(shutil.which('dot'), 'Graphviz is required')
    def test_markdown_line_spacing_changes_baseline_distance(self):
        from xml.etree import ElementTree
        for source in ('Alpha  \nBeta', '==Alpha==  \nBeta', '* Alpha  \n  Beta'):
            distances = []
            for spacing in (0, 8):
                dot = self.render(self.outline(source, f'md md_line_spacing={spacing} mdls=0'))
                self.graphviz(dot)
                result = subprocess.run(['dot', '-Tsvg'], input=dot.encode(), capture_output=True, check=True)
                positions = {element.text: float(element.attrib['y'])
                             for element in ElementTree.fromstring(result.stdout).iter('{http://www.w3.org/2000/svg}text')
                             if element.text in ('Alpha', 'Beta')}
                distances.append(abs(positions['Beta'] - positions['Alpha']))
            with self.subTest(source=source):
                self.assertAlmostEqual(8, distances[1] - distances[0], delta=1)

    def test_markdown_line_spacing_wrapping_root_and_formatting(self):
        source = '**Alpha** *Beta* Gamma Delta Epsilon Zeta Eta Theta'
        dot = self.render(self.outline(source, 'md mdw=90 md_line_spacing=3.5'))
        self.assertIn('HEIGHT="4" CELLPADDING="0"></TD>', dot)
        self.assertIn('<B>Alpha</B>', dot)
        self.assertIn('<I>Beta</I>', dot)
        self.graphviz(dot)
        root = self.render(['# Root', '\t: fname=out.jpg md md_line_spacing=8',
                            '\t: Alpha  ', '\t: Beta'])
        self.assertIn('HEIGHT="8" CELLPADDING="0"></TD>', root)
        self.graphviz(root)
        single = self.render(self.outline('Alpha', 'md md_line_spacing=8'))
        self.assertNotIn('HEIGHT="8"', single)

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
                                       ('md_list_indent', 'mdli', '48'),
                                       ('md_line_spacing', 'mdlns', '4')):
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
