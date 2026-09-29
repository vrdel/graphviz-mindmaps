import unittest
from types import SimpleNamespace
from unittest.mock import patch

from graphviz_mindmaps import constants, fontawesome
from graphviz_mindmaps.cli import build_parser, build_runtime
from graphviz_mindmaps.model.document import RenderSession
from graphviz_mindmaps.parser.outline import ExtractMindmapBlocks
from graphviz_mindmaps.render.dot import GenDot
from graphviz_mindmaps.render.label_html import ApplyInlineBacktickBold
from graphviz_mindmaps.theme import ApplyTheme, THEME_PALETTES


class RootThemeTests(unittest.TestCase):
    def test_root_symbol_color_and_size_override_only_selected_icon(self):
        for theme in ('default', 'github-light', 'nord'):
            with self.subTest(theme=theme):
                runtime = build_runtime(theme)
                attrs = 'root_symb=book:star:check root_fg=white'
                plain = self.render(runtime, attrs)
                changed = self.render(runtime, attrs + '\n\t: root_sym3rf35')
                root = next(line for line in changed.dotbuf.splitlines() if 'node1[' in line)
                self.assertIn('fontcolor="white"', root)
                self.assertIn('<FONT FACE="FontAwesome" COLOR="%s" POINT-SIZE="35">%s</FONT>'
                              % (constants.fontcolor['r'], fontawesome.symb['check']), root)
                self.assertEqual(2, root.count('COLOR="white" POINT-SIZE="25"'))
                child = lambda session: next(line for line in session.dotbuf.splitlines() if 'node101[' in line)
                self.assertEqual(child(plain), child(changed))

    def test_root_symbol_partial_and_group_controls(self):
        session = self.render(build_runtime('nord'),
                              'root_sym[1,3]gf35 root_sym2f40 root_sym2b\n\t: '
                              'root_symb=book:star:check root_fg=white')
        root = next(line for line in session.dotbuf.splitlines() if 'node1[' in line)
        self.assertEqual(2, root.count('COLOR="%s" POINT-SIZE="35"' % constants.fontcolor['g']))
        self.assertIn('COLOR="%s" POINT-SIZE="40"' % constants.fontcolor['b'], root)

    def test_child_and_out_of_range_controls_do_not_style_root_symbols(self):
        runtime = build_runtime('default')
        attrs = 'root_symb=book:star:check'
        plain = self.render(runtime, attrs)
        self.assertEqual(plain.dotbuf, self.render(runtime, attrs + ' root_sym0gf35 root_sym4gf35').dotbuf)
        changed = self.render(runtime, attrs, child_attrs='node root_sym3gf35')
        root = lambda session: next(line for line in session.dotbuf.splitlines() if 'node1[' in line)
        self.assertEqual(root(plain), root(changed))

    def test_consecutive_root_attribute_lines_match_single_line(self):
        attrs = [
            'leaf=node sgmargin=2 theme=github-light',
            'bg=#efefef root_bw=4 root_bs=dashed root_bg=seagreen1',
            'root_symb=check',
        ]
        runtime = build_runtime('default')
        single = self.render(runtime, ' '.join(attrs))
        multiple = self.render(runtime, '\n\t: ' + '\n\t: '.join(attrs))
        self.assertEqual(single.dotbuf, multiple.dotbuf)
        self.assertEqual('#efefef', multiple.bgcolor)
        self.assertIn('fillcolor="seagreen1"', multiple.dotbuf)
        self.assertIn('penwidth="4"', multiple.dotbuf)
        self.assertIn('FACE="FontAwesome"', multiple.dotbuf)

    def test_root_continuations_preserved_without_merging_child_attributes(self):
        lines = [
            '# Root', '\t: fname=out.jpg notitle',
            '\t: theme=github-light', '\t: root_symb=check',
            '\t# Child', '\t\t: node', '\t\t: bg=red root_bg=red',
            '\t# Sibling', '\t\t: node',
        ]
        blocks = ExtractMindmapBlocks(lines, ApplyInlineBacktickBold)
        self.assertEqual([lines[:6] + lines[7:]], blocks)

    def test_root_only_map_preserves_last_attribute_line(self):
        lines = ['# Root', '\t: fname=out.jpg', '\t: root_bg=seagreen1']
        self.assertEqual([lines], ExtractMindmapBlocks(lines, ApplyInlineBacktickBold))

    def test_root_borders_override_defaults_without_affecting_children(self):
        for theme in ('default', 'nord'):
            for style in ('solid', 'dashed', 'dotted', 'rounded,dashed'):
                with self.subTest(theme=theme, style=style):
                    runtime = build_runtime(theme)
                    defaults = 'global_bw=7 global_bs=dotted global_bc=red'
                    plain = self.render(runtime, defaults)
                    changed = self.render(runtime, defaults +
                                          ' root_bw=2.5 root_bs="%s" root_bc="#123456" root_bg=navy' % style)
                    root = next(line for line in changed.dotbuf.splitlines() if 'node1[' in line)
                    self.assertIn('penwidth="2.5"', root)
                    self.assertIn('style="radial,%s"' % style, root)
                    self.assertIn(' color="#123456"', root)
                    self.assertIn('fillcolor="navy"', root)
                    self.assertEqual(1, root.count('style='))
                    child = lambda session: next(line for line in session.dotbuf.splitlines() if 'node101[' in line)
                    self.assertEqual(child(plain), child(changed))
                    self.assertEqual(plain.dotbuf, self.render(runtime, defaults).dotbuf)

    def test_root_border_zero_width_and_child_attributes(self):
        runtime = build_runtime('nord')
        plain = self.render(runtime)
        root = lambda session: next(line for line in session.dotbuf.splitlines() if 'node1[' in line)
        self.assertIn('penwidth="0"', root(self.render(runtime, 'root_bw=0')))
        self.assertIn(' color="navy"', root(self.render(runtime, 'root_bc=navy')))
        child = self.render(runtime, child_attrs='node root_bw=0 root_bs=dashed root_bc=red')
        self.assertEqual(root(plain), root(child))

    def test_root_icons_resolve_names_aliases_and_use_default_symbol_color(self):
        runtime = build_runtime('nord')
        session = self.render(runtime, 'root_symb="book:quest:missing-icon:lightbulb-o"')
        root = next(line for line in session.dotbuf.splitlines() if 'node1[' in line)
        self.assertEqual(3, root.count('FACE="FontAwesome"'))
        self.assertIn('fontcolor="%s"' % THEME_PALETTES['nord']['fg'], root)
        self.assertEqual(3, root.count('COLOR="%s"' % constants.fontcolor['r']))
        previous = -1
        for name in ('book', 'question-circle', 'lightbulb-o'):
            position = root.index('>%s</FONT>' % fontawesome.symb[name])
            self.assertGreater(position, previous)
            previous = position
        self.assertIn('</FONT></TD></TR><TR><TD>Root', root)
        self.assertNotIn('FACE="FontAwesome"', self.render(runtime).dotbuf)

    def test_explicit_root_fg_overrides_title_and_icon_colors(self):
        for attrs in ('root_fg=white root_symb=book:star',
                      'root_symb=book:star root_fg="#abcdef"',
                      'root_symb=book:star\n\t: root_fg="#abcdef"'):
            with self.subTest(attrs=attrs):
                color = 'white' if 'white' in attrs else '#abcdef'
                session = self.render(build_runtime('nord'), attrs)
                root = next(line for line in session.dotbuf.splitlines() if 'node1[' in line)
                self.assertIn('fontcolor="%s"' % color, root)
                self.assertEqual(2, root.count('COLOR="%s"' % color))

    def test_unknown_or_child_root_icons_do_not_change_root(self):
        runtime = build_runtime('default')
        plain = self.render(runtime)
        self.assertEqual(plain.dotbuf, self.render(runtime, 'root_symb=missing-icon').dotbuf)
        child = self.render(runtime, child_attrs='node root_symb=book')
        root = lambda session: next(line for line in session.dotbuf.splitlines() if 'node1[' in line)
        self.assertEqual(root(plain), root(child))

    def test_root_colors_override_theme_without_changing_children_or_canvas(self):
        for theme in ('default', 'nord'):
            with self.subTest(theme=theme):
                runtime = build_runtime(theme)
                plain = self.render(runtime)
                changed = self.render(runtime, 'root_bg="#123456" root_fg="white"')
                root = next(line for line in changed.dotbuf.splitlines() if 'node1[' in line)
                self.assertIn('fillcolor="#123456"', root)
                self.assertIn('fontcolor="white"', root)
                self.assertEqual(1, root.count('fillcolor='))
                self.assertEqual(1, root.count('fontcolor='))
                self.assertEqual(plain.bgcolor, changed.bgcolor)
                child = lambda session: next(line for line in session.dotbuf.splitlines() if 'node101[' in line)
                self.assertEqual(child(plain), child(changed))
                self.assertEqual(plain.dotbuf, self.render(runtime).dotbuf)

    def test_individual_root_colors_and_child_attributes(self):
        runtime = build_runtime('nord')
        for attrs, expected in (('root_bg=navy', 'fillcolor="navy"'),
                                ('root_fg="#abcdef"', 'fontcolor="#abcdef"')):
            with self.subTest(attrs=attrs):
                session = self.render(runtime, attrs)
                root = next(line for line in session.dotbuf.splitlines() if 'node1[' in line)
                self.assertIn(expected, root)
                other = 'fontcolor' if attrs.startswith('root_bg') else 'fillcolor'
                color = THEME_PALETTES['nord']['fg' if other == 'fontcolor' else 'panel']
                self.assertIn('%s="%s"' % (other, color), root)
        plain = self.render(runtime)
        child_attrs = self.render(runtime, child_attrs='node root_bg=navy root_fg=white')
        root = lambda session: next(line for line in session.dotbuf.splitlines() if 'node1[' in line)
        self.assertEqual(root(plain), root(child_attrs))

    def test_themes_work_from_cli_and_root_and_preserve_borderless_images(self):
        for name in THEME_PALETTES:
            with self.subTest(theme=name):
                args = build_parser().parse_args(['--theme', name])
                cli_session = self.render(build_runtime(args.theme))
                root_session = self.render(build_runtime('nord'), 'theme=' + name)
                self.assertEqual(cli_session.dotbuf, root_session.dotbuf)
                self.assertEqual(THEME_PALETTES[name]['bg'], root_session.bgcolor)
                self.assertIn('shape=none', constants.nodetype['img'])
                self.assertIn('fillcolor="%s"' % THEME_PALETTES[name]['panel'], root_session.dotbuf)

    def tearDown(self):
        ApplyTheme('default')

    def render(self, runtime, root_attrs='', child_attrs='node'):
        blocks = ExtractMindmapBlocks([
            '# Root', *('\t: fname=out.jpg ' + root_attrs).splitlines(),
            '\t# Child', '\t\t: ' + child_attrs,
        ], ApplyInlineBacktickBold)
        session = RenderSession()
        with patch('graphviz_mindmaps.render.dot.WriteDot'):
            GenDot(blocks[0], SimpleNamespace(dotname='out.dot', jpgname=None), session, runtime)
        return session

    def test_root_theme_overrides_cli_and_does_not_leak_to_next_map(self):
        runtime = build_runtime('papercolor')
        nord = self.render(runtime, 'theme=nord')
        self.assertEqual(THEME_PALETTES['nord']['bg'], nord.bgcolor)
        self.assertIn('fillcolor="%s"' % THEME_PALETTES['nord']['panel'], nord.dotbuf)
        self.assertIn('fontcolor="%s"' % THEME_PALETTES['nord']['fg'], nord.dotbuf)
        paper = self.render(runtime)
        self.assertEqual(THEME_PALETTES['papercolor']['bg'], paper.bgcolor)
        self.assertIn('fillcolor="%s"' % THEME_PALETTES['papercolor']['panel'], paper.dotbuf)
        self.assertEqual('papercolor', runtime.theme_name)

    def test_explicit_default_theme_overrides_cli(self):
        session = self.render(build_runtime('nord'), 'theme=default')
        self.assertEqual(constants.DEFAULT_BGCOLOR, session.bgcolor)

    def test_explicit_colors_override_root_theme(self):
        session = self.render(build_runtime('default'), 'theme=nord bg="#123456"',
                              'node bg="#abcdef" fg="#fedcba"')
        self.assertEqual('#123456', session.bgcolor)
        self.assertIn('fillcolor="#abcdef"', session.dotbuf)
        self.assertIn('fontcolor="#fedcba"', session.dotbuf)

    def test_child_theme_does_not_select_global_palette(self):
        session = self.render(build_runtime('papercolor'), child_attrs='node theme=nord')
        self.assertEqual(THEME_PALETTES['papercolor']['bg'], session.bgcolor)

    def test_unknown_root_theme_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unknown theme: missing'):
            self.render(build_runtime('default'), 'theme=missing')
