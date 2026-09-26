import unittest
from types import SimpleNamespace
from unittest.mock import patch

from graphviz_mindmaps import constants
from graphviz_mindmaps.cli import build_parser, build_runtime
from graphviz_mindmaps.model.document import RenderSession
from graphviz_mindmaps.parser.outline import ExtractMindmapBlocks
from graphviz_mindmaps.render.dot import GenDot
from graphviz_mindmaps.render.label_html import ApplyInlineBacktickBold
from graphviz_mindmaps.theme import ApplyTheme, THEME_PALETTES


class RootThemeTests(unittest.TestCase):
    def test_themes_work_from_cli_and_root_and_preserve_borderless_images(self):
        for name in ('solarized-light', 'catppuccin-latte', 'rose-pine-dawn',
                     'github-light', 'one-light', 'gruvbox-light',
                     'dracula', 'catppuccin-mocha', 'tokyo-night',
                     'one-dark', 'rose-pine', 'kanagawa'):
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
            '# Root', '\t: fname=out.jpg ' + root_attrs,
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
