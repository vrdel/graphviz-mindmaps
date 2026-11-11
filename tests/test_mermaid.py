import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

from PIL import Image

from graphviz_mindmaps.constants import font, vrbtcolors
from graphviz_mindmaps.parser.attributes import ResolveVerbatimFillColorToken
from graphviz_mindmaps.model.document import MarkdownBody
from graphviz_mindmaps.render.markdown import RenderMarkdown
from graphviz_mindmaps.render.mermaid import RenderMermaidImage, _static_svg
from graphviz_mindmaps.theme import ApplyTheme, PeleThemeColors, THEME_PALETTES


ROOT = Path(__file__).resolve().parents[1]
HAS_PELE = (shutil.which('node') and shutil.which('rsvg-convert')
            and (ROOT / 'node_modules/pele/dist/pele.js').exists())


class MermaidTests(unittest.TestCase):
    def test_theme_color_maps_cover_all_palettes_without_mutating_active_theme(self):
        self.addCleanup(ApplyTheme, 'default')
        from graphviz_mindmaps.constants import fontcolor
        ApplyTheme('nord')
        for name in ('default', *THEME_PALETTES):
            with self.subTest(theme=name):
                colors = PeleThemeColors(name)
                self.assertEqual(8, sum(key.startswith('--pele-series-') for key in colors))
                self.assertTrue(all(value.startswith('#') and len(value) == 7
                                    for value in colors.values()))
                if name != 'default':
                    self.assertEqual(THEME_PALETTES[name]['fg'], colors['--pele-fg'])
                    self.assertEqual(THEME_PALETTES[name]['panel'], colors['--pele-surface'])
                self.assertEqual(THEME_PALETTES['nord']['fg'], fontcolor['def'])

    def test_static_svg_resolves_inherited_and_overridden_colors(self):
        source = ('<svg style="--_s:var(--pele-surface,#f3f3f3);font:16px sans-serif">'
                  '<rect fill="var(--_s)"/>'
                  '<g style="--pele-surface:#123456"><rect fill="var(--_s)"/></g>'
                  '<text>literal var(--_s)</text></svg>')
        root = ElementTree.fromstring(_static_svg(source))
        self.assertEqual('#f3f3f3', root[0].get('fill'))
        self.assertEqual('#123456', root[1][0].get('fill'))
        self.assertEqual('literal var(--_s)', root[2].text)
        self.assertEqual('font:16px sans-serif', root.get('style'))

    def test_missing_dependencies_and_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            for missing, message in (('node', 'Node.js'), ('rsvg-convert', 'rsvg-convert')):
                with self.subTest(missing=missing), patch(
                    'graphviz_mindmaps.render.mermaid.shutil.which',
                    side_effect=lambda name: None if name == missing else '/bin/' + name,
                ), self.assertRaisesRegex(ValueError, message):
                    RenderMermaidImage('flowchart LR\nA-->B', directory)
            with patch('graphviz_mindmaps.render.mermaid.shutil.which', return_value='/bin/tool'), patch(
                'graphviz_mindmaps.render.mermaid.subprocess.run',
                side_effect=subprocess.TimeoutExpired('node', 30),
            ), self.assertRaisesRegex(ValueError, 'timed out'):
                RenderMermaidImage('flowchart LR\nA-->B', directory)

    def test_static_svg_resolves_color_tokens_only_in_color_properties(self):
        svg = ('<svg><rect fill="ccyan" stroke="cred-10" '
               'style="color:corange10;fill:ctrans;stroke-width:4px;stop-color:cred999;'
               'flood-color:cred-999;lighting-color:ccyan !important;font-family:ccyan"/>'
               '<text data-id="ccyan">fill:ccyan,stroke:cred-10</text>'
               '<path fill="#f9f" stroke="red" style="color:rgb(1,2,3)"/></svg>')
        palette = {'ccyan': '#dffdfa', 'cred': '#fde0df', 'corang': '#fdecdf',
                   'ctrans': 'transparent'}
        root = ElementTree.fromstring(_static_svg(svg, color_tokens=palette))
        self.assertEqual('#dffdfa', root[0].get('fill'))
        self.assertEqual('#f3d6d5', root[0].get('stroke'))
        self.assertEqual('color:#fff6e9;fill:transparent;stroke-width:4px;stop-color:#ffffff;'
                         'flood-color:#000000;lighting-color:#dffdfa !important;font-family:ccyan',
                         root[0].get('style'))
        self.assertEqual('ccyan', root[1].get('data-id'))
        self.assertEqual('fill:ccyan,stroke:cred-10', root[1].text)
        self.assertEqual('#f9f', root[2].get('fill'))
        self.assertEqual('red', root[2].get('stroke'))
        self.assertEqual('color:rgb(1,2,3)', root[2].get('style'))

    def test_markdown_mermaid_errors_include_outline_location(self):
        body = MarkdownBody('text\n\n```mermaid\nbad\n```', 'map.otl', 'Diagram', 5,
                            locations=[(10 + i, 3) for i in range(5)])
        with tempfile.TemporaryDirectory() as directory, patch(
            'graphviz_mindmaps.render.markdown.RenderMermaidImage',
            side_effect=ValueError('Pele rendering failed: syntax error'),
        ), self.assertRaisesRegex(ValueError, "map.otl:12: Markdown node 'Diagram': Pele"):
            RenderMarkdown(body, [directory])

    def test_ordinary_code_does_not_require_pele(self):
        body = MarkdownBody('```python\nprint(1)\n```', '<test>', 'Code', 1)
        with tempfile.TemporaryDirectory() as directory, patch(
            'graphviz_mindmaps.render.markdown.RenderMermaidImage',
        ) as render:
            self.assertIn('<IMG SRC=', RenderMarkdown(body, [directory]))
            render.assert_not_called()

    @unittest.skipUnless(HAS_PELE, 'optional Pele npm package, Node and rsvg-convert required')
    def test_real_pele_diagram_types_and_transparent_pngs(self):
        sources = (
            'flowchart LR\nA[Outline] --> B[Pele]\nstyle B fill:#abcdef',
            'sequenceDiagram\nAlice->>Bob: Hello',
            'classDiagram\nAnimal <|-- Duck',
            'mindmap\n  root((Plan))\n    Work\n    Rest',
            'pie title Time\n"Work" : 8\n"Rest" : 16',
        )
        with tempfile.TemporaryDirectory() as directory:
            for source in sources:
                with self.subTest(source=source):
                    path = RenderMermaidImage(source, directory, 420)
                    with Image.open(path) as image:
                        rgba = image.convert('RGBA')
                        self.assertIsNotNone(rgba.getbbox())
                        self.assertEqual(0, rgba.getchannel('A').getextrema()[0])
                        # CSS variables must resolve to colored surfaces, not solid black.
                        self.assertGreater(len(set(rgba.getdata())), 20)
                    svg = path.with_suffix('.svg').read_text()
                    self.assertNotIn('var(', svg)
                    if 'flowchart' in source:
                        self.assertIn('#abcdef', svg)
                    with patch('graphviz_mindmaps.render.mermaid.subprocess.run') as run:
                        self.assertEqual(path, RenderMermaidImage(source, directory, 420))
                        run.assert_not_called()

    @unittest.skipUnless(HAS_PELE, 'optional Pele npm package, Node and rsvg-convert required')
    def test_real_pele_custom_color_styles_follow_theme_and_cache_palette(self):
        self.addCleanup(ApplyTheme, 'default')
        source = ('flowchart LR\nA["fill:ccyan,stroke:cred-10"]-->B[Class]-->C[Transparent]\n'
                  'style A fill:ccyan,stroke:cred-10,stroke-width:4px\n'
                  'classDef custom fill:corange10,stroke:cgrey,color:cblue-10\n'
                  'class B custom\nstyle C fill:ctrans,stroke:cblack\n'
                  'linkStyle 0 stroke:cviole10,stroke-width:4px')
        with tempfile.TemporaryDirectory() as directory:
            outputs = []
            for theme in ('default', 'nord', 'github-light', 'default'):
                ApplyTheme(theme)
                output = RenderMermaidImage(source, directory, width=None)
                outputs.append(output)
                root = ElementTree.fromstring(output.with_suffix('.svg').read_text())
                styles = ';'.join(element.get('style', '') for element in root.iter())
                palette = dict(vrbtcolors)
                for property, token in (('fill', 'ccyan'), ('stroke', 'cred-10'),
                                        ('fill', 'corange10'), ('stroke', 'cviole10')):
                    self.assertIn(property + ':' + ResolveVerbatimFillColorToken(token, palette), styles)
                self.assertIn('fill:transparent', styles)
                self.assertIn('stroke-width:4px', styles)
                self.assertIn('fill:ccyan,stroke:cred-10', ''.join(root.itertext()))
                self.assertNotIn('stroke:cblack', styles)
                self.assertNotIn('stroke:cgrey', styles)
            self.assertEqual(3, len(set(outputs)))
            self.assertEqual(outputs[0], outputs[-1])
            # A user-defined palette change must invalidate the same-source cache.
            with patch.dict(vrbtcolors, {'ccyan': '#123456'}):
                customized = RenderMermaidImage(source, directory, width=None)
                self.assertNotEqual(outputs[-1], customized)
                self.assertIn('fill:#123456', customized.with_suffix('.svg').read_text())

    @unittest.skipUnless(HAS_PELE, 'optional Pele npm package, Node and rsvg-convert required')
    def test_real_pele_parse_errors_and_width_specific_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'Pele rendering failed'):
                RenderMermaidImage('this is not a diagram', directory)
            source = 'flowchart LR\nA-->B'
            self.assertNotEqual(RenderMermaidImage(source, directory, 200),
                                RenderMermaidImage(source, directory, 400))

    @unittest.skipUnless(HAS_PELE, 'optional Pele npm package, Node and rsvg-convert required')
    def test_real_pele_natural_dimensions_exceed_markdown_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            for direction, dimension, limit in (('LR', 'width', 420), ('TB', 'height', 900)):
                source = 'flowchart ' + direction + '\n' + '\n'.join(
                    f'A{i}[Step {i}] --> A{i + 1}[Step {i + 1}]' for i in range(15))
                with self.subTest(direction=direction):
                    output = RenderMermaidImage(source, directory, width=None)
                    svg = ElementTree.fromstring(output.with_suffix('.svg').read_text())
                    with Image.open(output) as image:
                        self.assertGreater(getattr(image, dimension), limit)
                        self.assertEqual(image.width, round(float(svg.get('width'))))
                        self.assertEqual(image.height, round(float(svg.get('height'))))

    @unittest.skipUnless(HAS_PELE, 'optional Pele npm package, Node and rsvg-convert required')
    def test_unwrapped_markdown_uses_real_pele_at_natural_size(self):
        import re
        source = 'flowchart LR\n' + '\n'.join(f'A{i}[Step {i}] --> A{i + 1}[Step {i + 1}]'
                                              for i in range(10))
        body = MarkdownBody('Before\n\n```mermaid\n' + source + '\n```\n\nAfter',
                            '<test>', 'Natural diagram', 1)
        with tempfile.TemporaryDirectory() as directory:
            natural = RenderMermaidImage(source + '\n', directory, width=None,
                                         face=font['comic'], size=18)
            label = RenderMarkdown(body, [directory], width=100, wrap='off')
            self.assertEqual([str(natural)], re.findall(r'<IMG SRC="([^"]+)"', label))
            with Image.open(natural) as image:
                self.assertGreater(image.width, 100)

    @unittest.skipUnless(HAS_PELE, 'optional Pele npm package, Node and rsvg-convert required')
    def test_real_pele_uses_node_font_and_size_with_separate_cached_images(self):
        body = MarkdownBody('```mermaid\nflowchart LR\nA[Node label]\n```',
                            '<test>', 'Font inheritance', 1)
        with tempfile.TemporaryDirectory() as directory:
            outputs = []
            for face, size in (('Dejavu Sans Mono', 18), ('Dejavu Serif', 18),
                               ('Dejavu Serif', 26)):
                with self.subTest(face=face, size=size):
                    output = RenderMermaidImage('flowchart LR\nA[Node label]\n', directory,
                                                width=None, face=face, size=size)
                    outputs.append(output)
                    root = ElementTree.fromstring(output.with_suffix('.svg').read_text())
                    self.assertIn('font-family:' + face, root.get('style'))
                    self.assertIn(f'font:{size}px ', root.get('style'))
                    label = RenderMarkdown(body, [directory], face=face, size=size, wrap=False)
                    self.assertIn(str(output), label)
            self.assertEqual(3, len(set(outputs)))
            label = RenderMarkdown(body, [directory], face='Dejavu Serif', size=26,
                                   wrap=False, mermaid_font='off')
            default = RenderMermaidImage('flowchart LR\nA[Node label]\n', directory, width=None, size=26)
            self.assertIn(str(default), label)
            self.assertNotIn(default, outputs)
            style = ElementTree.fromstring(default.with_suffix('.svg').read_text()).get('style')
            self.assertIn('font-family:sans-serif', style)
            self.assertIn('font:26px ', style)
            with patch('graphviz_mindmaps.render.mermaid.subprocess.run') as run:
                self.assertEqual(outputs[-1], RenderMermaidImage(
                    'flowchart LR\nA[Node label]\n', directory, width=None,
                    face='Dejavu Serif', size=26))
                run.assert_not_called()

    @unittest.skipUnless(HAS_PELE, 'optional Pele npm package, Node and rsvg-convert required')
    def test_real_mermaid_font_size_override_relayouts_diagrams_and_caches_size(self):
        import re
        with tempfile.TemporaryDirectory() as directory:
            for source in ('flowchart LR\nA[Build]-->B[Deploy]', 'sequenceDiagram\nClient->>API: Request'):
                body = MarkdownBody('```mermaid\n' + source + '\n```', '<test>', 'Font sizes', 1)
                outputs, sizes = [], []
                for size in (14, 24.5, 28):
                    label = RenderMarkdown(body, [directory], size=18, wrap=False,
                                           mermaid_font='off', mermaid_font_size=size)
                    path = Path(re.search(r'<IMG SRC="([^"]+)"', label).group(1))
                    outputs.append(path)
                    root = ElementTree.fromstring(path.with_suffix('.svg').read_text())
                    self.assertIn(f'font:{size:g}px ', root.get('style'))
                    self.assertIn('font-family:sans-serif', root.get('style'))
                    with Image.open(path) as image:
                        sizes.append(image.size)
                self.assertEqual(3, len(set(outputs)))
                self.assertGreater(sizes[-1][0], sizes[0][0])
                self.assertGreater(sizes[-1][1], sizes[0][1])
                with patch('graphviz_mindmaps.render.mermaid.subprocess.run') as run:
                    label = RenderMarkdown(body, [directory], wrap=False, mermaid_font='off', mermaid_font_size='28')
                    self.assertIn(str(outputs[-1]), label)
                    run.assert_not_called()

    @unittest.skipUnless(HAS_PELE, 'optional Pele npm package, Node and rsvg-convert required')
    def test_real_pele_themes_and_explicit_styles_have_separate_cached_images(self):
        source = 'flowchart LR\nA[Themed]-->B[Custom]\nstyle B fill:#abcdef'
        chart = 'pie title Tasks\n"Done" : 3\n"Pending" : 2'
        with tempfile.TemporaryDirectory() as directory:
            outputs = []
            for theme in ('github-light', 'nord', 'default'):
                with self.subTest(theme=theme):
                    colors = PeleThemeColors(theme)
                    output = RenderMermaidImage(source, directory, colors=colors)
                    outputs.append(output)
                    svg = output.with_suffix('.svg').read_text()
                    self.assertIn(colors['--pele-fg'], svg)
                    self.assertIn(colors['--pele-surface'], svg)
                    self.assertIn(colors['--pele-border'], svg)
                    self.assertIn('#abcdef', svg)
                    self.assertNotIn('var(', svg)
                    pie = RenderMermaidImage(chart, directory, colors=colors)
                    self.assertIn(colors['--pele-series-1'], pie.with_suffix('.svg').read_text())
                    with Image.open(output) as image:
                        self.assertEqual(0, image.convert('RGBA').getchannel('A').getextrema()[0])
            self.assertEqual(3, len(set(outputs)))
            with patch('graphviz_mindmaps.render.mermaid.subprocess.run') as run:
                reordered = dict(reversed(list(PeleThemeColors('nord').items())))
                self.assertEqual(outputs[1], RenderMermaidImage(source, directory, colors=reordered))
                run.assert_not_called()

    @unittest.skipUnless(HAS_PELE, 'optional Pele npm package, Node and rsvg-convert required')
    def test_wheel_helper_resolves_pele_from_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            helper = Path(directory) / 'pele.mjs'
            shutil.copyfile(ROOT / 'graphviz_mindmaps/render/pele.mjs', helper)
            result = subprocess.run([shutil.which('node'), str(helper)], cwd=ROOT,
                                    input=json.dumps({'source': 'flowchart LR\nA-->B', 'width': 420}),
                                    capture_output=True, text=True, check=True)
            self.assertIn('<svg', result.stdout)
            missing = subprocess.run([shutil.which('node'), str(helper)], cwd=directory,
                                     input=json.dumps({'source': 'flowchart LR\nA-->B', 'width': 420}),
                                     capture_output=True, text=True)
            self.assertNotEqual(0, missing.returncode)
            self.assertIn('Pele is not installed', missing.stderr)
