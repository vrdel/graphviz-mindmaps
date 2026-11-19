from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

from PIL import Image, ImageColor

from graphviz_mindmaps.render.svgbob import FindSvgbob, FindSvgbobFont, ParseSvgbobFill, RenderSvgbobImage
from graphviz_mindmaps.model.document import MarkdownBody
from graphviz_mindmaps.render.markdown import RenderMarkdown
from graphviz_mindmaps.constants import vrbtcolors
from graphviz_mindmaps.theme import ApplyTheme


SOURCE = '+---------+     +----------+\n| outline |---->| renderer |\n+---------+     +----------+\n'
HAS_SVGBOB = bool(FindSvgbob() and shutil.which('rsvg-convert'))


class SvgbobTests(unittest.TestCase):
    def setUp(self):
        FindSvgbobFont.cache_clear()
        self.addCleanup(FindSvgbobFont.cache_clear)

    def test_font_selection_uses_configured_constants(self):
        from types import SimpleNamespace
        with patch('graphviz_mindmaps.render.svgbob.SVGBOB_FONT', 'Example Mono'), patch(
            'graphviz_mindmaps.render.svgbob.SVGBOB_FALLBACK_FONT', 'Fallback Mono',
        ):
            for matched, expected in (('Example Mono', 'Example Mono'), ('Other Mono', 'Fallback Mono')):
                FindSvgbobFont.cache_clear()
                with patch('graphviz_mindmaps.render.svgbob.subprocess.run',
                           return_value=SimpleNamespace(stdout=matched)) as run:
                    self.assertEqual(expected, FindSvgbobFont())
                    self.assertEqual('Example Mono', run.call_args.args[0][-1])

    def test_preferred_font_requires_an_exact_installed_family(self):
        from types import SimpleNamespace
        for families, expected in (('Comic True Mono', 'Comic True Mono'),
                                   ('Other Alias,Comic True Mono', 'Comic True Mono'),
                                   ('DejaVu Sans Mono', 'Dejavu Sans Mono'),
                                   ('Comic Sans MS', 'Dejavu Sans Mono')):
            FindSvgbobFont.cache_clear()
            with self.subTest(families=families), patch(
                'graphviz_mindmaps.render.svgbob.subprocess.run',
                return_value=SimpleNamespace(stdout=families),
            ) as run:
                self.assertEqual(expected, FindSvgbobFont())
                self.assertEqual(expected, FindSvgbobFont())
                run.assert_called_once()
        for error in (FileNotFoundError('fontconfig missing'), subprocess.TimeoutExpired('fc-match', 5)):
            FindSvgbobFont.cache_clear()
            with patch('graphviz_mindmaps.render.svgbob.subprocess.run', side_effect=error):
                self.assertEqual('Dejavu Sans Mono', FindSvgbobFont())

    @unittest.skipUnless(HAS_SVGBOB, 'optional Svgbob CLI and rsvg-convert required')
    def test_selected_font_depends_on_sketch_mode_and_is_used_in_svg_and_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            outputs = []
            for sketch, available, expected in ((False,'Comic True Mono','Dejavu Sans Mono'),
                                                (True,'Comic True Mono','Comic True Mono'),
                                                (True,'Dejavu Sans Mono','Dejavu Sans Mono')):
                with patch('graphviz_mindmaps.render.svgbob.FindSvgbobFont', return_value=available) as resolve, patch(
                    'graphviz_mindmaps.render.svgbob.ApplySvgbobSketch',
                ), patch('graphviz_mindmaps.render.svgbob.SketchProfile',return_value={}):
                    output = RenderSvgbobImage(SOURCE, directory, sketch=sketch)
                    outputs.append(output)
                    if not sketch:
                        resolve.assert_not_called()
                    self.assertIn('font-family: ' + expected, output.with_suffix('.svg').read_text())
                    with patch('graphviz_mindmaps.render.svgbob.subprocess.run') as run:
                        self.assertEqual(output, RenderSvgbobImage(SOURCE, directory, sketch=sketch))
                        run.assert_not_called()
            self.assertEqual(3,len(set(outputs)))

    def test_default_fill_validation(self):
        self.assertIsNone(ParseSvgbobFill(None))
        for value in ('ccyan', 'cred-10', 'ctrans', 'none', 'transparent', '#f9f', 'red',
                      'linear-gradient(90deg, ccyan, cblue)', 'radial-gradient(cwhite, cgreen)'):
            self.assertEqual(value, ParseSvgbobFill(value))
        for value in ('', 'unknown', 'cunknown', 'linear-gradient(ccyan)', '#gggggg'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'svgbob_fill'):
                ParseSvgbobFill(value)

    @unittest.skipUnless(HAS_SVGBOB, 'optional Svgbob CLI and rsvg-convert required')
    def test_real_default_fill_legend_overrides_transparency_themes_and_cache(self):
        source = '''+------------+    +------------+    +------------+
| default    |--->| override   |--->| clear      |
|            |    |  {special} |    |    {clear} |
+------------+    +------------+    +------------+

# Legend:
special = {fill: cred;}
clear = {fill: none;}
'''
        self.addCleanup(ApplyTheme, 'default')
        outputs = []
        with tempfile.TemporaryDirectory() as directory:
            for theme in ('default', 'nord'):
                ApplyTheme(theme)
                output = RenderSvgbobImage(source, directory, fill='ccyan')
                outputs.append(output)
                root = ElementTree.fromstring(output.with_suffix('.svg').read_text())
                boxes = sorted([e for e in root.iter('{http://www.w3.org/2000/svg}rect')
                                if 'backdrop' not in e.get('class', '')], key=lambda e: float(e.get('x')))
                self.assertEqual(3, len(boxes))
                with Image.open(output) as image:
                    rgba = image.convert('RGBA')
                    pixels = [rgba.getpixel((round(float(b.get('x')) + 5), round(float(b.get('y')) + 5)))
                              for b in boxes]
                    self.assertEqual(ImageColor.getcolor(vrbtcolors['ccyan'], 'RGBA'), pixels[0])
                    self.assertEqual(ImageColor.getcolor(vrbtcolors['cred'], 'RGBA'), pixels[1])
                    self.assertEqual(0, pixels[2][3])
                    self.assertEqual(0, rgba.getpixel((0, 0))[3])
                with patch('graphviz_mindmaps.render.svgbob.subprocess.run') as run:
                    self.assertEqual(output, RenderSvgbobImage(source, directory, fill='ccyan'))
                    run.assert_not_called()
                other = RenderSvgbobImage(source, directory, fill='#123456')
                self.assertNotEqual(output, other)
                gradient = RenderSvgbobImage(source, directory, fill='linear-gradient(ccyan,cblue)')
                self.assertIn('linearGradient', gradient.with_suffix('.svg').read_text())
            self.assertNotEqual(outputs[0], outputs[1])

    @unittest.skipUnless(HAS_SVGBOB, 'optional Svgbob CLI and rsvg-convert required')
    def test_connected_rounded_box_gets_default_fill_and_legend_override(self):
        source = '''                                       +---------+
                              +------->| worker  |
       "DATA-SERVICE"         |        | module  |
 .---------------------.      |        +---------+
 |"/example/items"     +------+
 |"/example/sets"      |              +------------+
 |                     +------------->| processor  |
 '---------------------'              |  module    |
                                      +------------+
                                        Service A
                                      "worker/client"
'''
        svg = '{http://www.w3.org/2000/svg}'
        with tempfile.TemporaryDirectory() as directory:
            plain = RenderSvgbobImage(source, directory, stroke_width=1)
            output = RenderSvgbobImage(source, directory, stroke_width=1, fill='cwhite')
            before = ElementTree.fromstring(plain.with_suffix('.svg').read_text())
            after = ElementTree.fromstring(output.with_suffix('.svg').read_text())
            rect = next(e for e in after.iter(svg + 'rect') if e.get('rx') == '4')
            self.assertEqual((before.get('width'),before.get('height')), (after.get('width'),after.get('height')))
            self.assertEqual([e.get('points') for e in before.iter(svg + 'polygon')],
                             [e.get('points') for e in after.iter(svg + 'polygon')])
            x,y,w,h = [float(rect.get(k)) for k in ('x','y','width','height')]
            point = (round(x+8),round(y+h-8))
            with Image.open(plain) as image:
                self.assertEqual(0, image.convert('RGBA').getpixel(point)[3])
            with Image.open(output) as image:
                self.assertEqual(ImageColor.getcolor(vrbtcolors['cwhite'],'RGBA'), image.convert('RGBA').getpixel(point))
            # Put an overriding tag in the otherwise blank row of the same box.
            lines = source.splitlines()
            lines[6] = lines[6][:3] + '{special}' + lines[6][12:]
            tagged = '\n'.join(lines) + '\n\n# Legend:\nspecial = { fill: cred; }\n'
            overridden = RenderSvgbobImage(tagged, directory, stroke_width=1, fill='cwhite')
            with Image.open(overridden) as image:
                self.assertEqual(ImageColor.getcolor(vrbtcolors['cred'],'RGBA'), image.convert('RGBA').getpixel(point))

    @unittest.skipUnless(HAS_SVGBOB, 'optional Svgbob CLI and rsvg-convert required')
    def test_rounded_default_fill_survives_fractionally_scaled_font_coordinates(self):
        source = " .--------.\n | hello  +---->\n |        |\n '--------'\n"
        with tempfile.TemporaryDirectory() as directory:
            for size in (14,18,20,28,36):
                with self.subTest(font_size=size):
                    output = RenderSvgbobImage(source, directory, font_size=size, fill='cwhite')
                    root = ElementTree.fromstring(output.with_suffix('.svg').read_text())
                    rect = next(e for e in root.iter('{http://www.w3.org/2000/svg}rect')
                                if float(e.get('rx', '0')) > 0)
                    self.assertAlmostEqual(4 * size / 14, float(rect.get('rx')), places=4)
                    x,y,w,h = [float(rect.get(k)) for k in ('x','y','width','height')]
                    with Image.open(output) as image:
                        self.assertEqual(ImageColor.getcolor(vrbtcolors['cwhite'],'RGBA'),
                                         image.convert('RGBA').getpixel((round(x+w/2),round(y+h*.8))))

    @unittest.skipUnless(HAS_SVGBOB, 'optional Svgbob CLI and rsvg-convert required')
    def test_quoted_query_labels_expand_viewport_instead_of_getting_clipped(self):
        source = ('" ?tags=scope:GROUP_A,GROUP_B "\n'
                  '" &tags=status:active,inactive "\n'
                  '" &tags=category:example "\n'
                  '" &type=GROUP_A,GROUP_B "\n')
        with tempfile.TemporaryDirectory() as directory:
            for size in (14,18):
                with self.subTest(font_size=size):
                    output = RenderSvgbobImage(source, directory, font_size=size)
                    root = ElementTree.fromstring(output.with_suffix('.svg').read_text())
                    labels = list(root.iter('{http://www.w3.org/2000/svg}text'))
                    self.assertIn('&type=GROUP_A,GROUP_B', labels[-1].text)
                    baseline = float(labels[-1].get('y'))
                    self.assertGreater(float(root.get('height')), baseline)
                    self.assertGreater(float(root.get('width')), 100)
                    with Image.open(output) as image:
                        self.assertEqual((int(root.get('width')),int(root.get('height'))), image.size)
                        alpha = image.convert('RGBA').getchannel('A')
                        self.assertGreater(alpha.getbbox()[3], baseline - size / 2)
                    with patch('graphviz_mindmaps.render.svgbob.subprocess.run') as run:
                        self.assertEqual(output, RenderSvgbobImage(source, directory, font_size=size))
                        run.assert_not_called()

    def test_missing_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('graphviz_mindmaps.render.svgbob.FindSvgbob', return_value=None):
                with self.assertRaisesRegex(ValueError, 'Svgbob is not installed'):
                    RenderSvgbobImage(SOURCE, directory)
            with patch('graphviz_mindmaps.render.svgbob.FindSvgbob', return_value='/bin/tool'), \
                    patch('graphviz_mindmaps.render.svgbob.shutil.which', return_value=None):
                with self.assertRaisesRegex(ValueError, 'rsvg-convert'):
                    RenderSvgbobImage(SOURCE, directory)

    def test_errors_timeouts_and_invalid_svg(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory, 'fake-cli')
            executable.touch()
            failures = (
                (subprocess.CompletedProcess([], 1, '', 'bad input'), 'Svgbob rendering failed: bad input'),
                (subprocess.CompletedProcess([], 0, 'invalid', ''), 'invalid SVG'),
                (subprocess.CompletedProcess([], 0, '<html/>', ''), 'missing SVG root'),
                (subprocess.TimeoutExpired('svgbob', 30), 'timed out'),
            )
            for result, message in failures:
                with self.subTest(message=message), patch(
                    'graphviz_mindmaps.render.svgbob.FindSvgbob', return_value=str(executable),
                ), patch('graphviz_mindmaps.render.svgbob.shutil.which', return_value='/bin/tool'), patch(
                    'graphviz_mindmaps.render.svgbob.subprocess.run',
                    **({'side_effect': result} if isinstance(result, Exception) else {'return_value': result}),
                ), self.assertRaisesRegex(ValueError, message):
                    RenderSvgbobImage(SOURCE, directory)
            self.assertFalse(list(Path(directory).rglob('*.png')))

    @unittest.skipUnless(HAS_SVGBOB, 'optional Svgbob CLI and rsvg-convert required')
    def test_real_diagram_transparency_labels_colors_and_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            outputs = []
            for foreground in ('#2e3440', '#eceff4'):
                output = RenderSvgbobImage(SOURCE, directory, foreground)
                outputs.append(output)
                root = ElementTree.fromstring(output.with_suffix('.svg').read_text())
                text = ''.join(root.itertext())
                self.assertIn('outline', text)
                self.assertIn('renderer', text)
                self.assertIn('stroke: ' + foreground, text)
                self.assertIn('fill: ' + foreground, text)
                with Image.open(output) as image:
                    rgba = image.convert('RGBA')
                    self.assertEqual((0, 255), rgba.getchannel('A').getextrema())
                    self.assertEqual(round(float(root.get('width'))), image.width)
                    self.assertEqual(round(float(root.get('height'))), image.height)
                with patch('graphviz_mindmaps.render.svgbob.subprocess.run') as run:
                    self.assertEqual(output, RenderSvgbobImage(SOURCE, directory, foreground))
                    run.assert_not_called()
            self.assertNotEqual(*outputs)

    @unittest.skipUnless(HAS_SVGBOB, 'optional Svgbob CLI and rsvg-convert required')
    def test_real_stroke_width_defaults_fractional_values_and_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            default = RenderSvgbobImage(SOURCE, directory)
            outputs, sizes = [], []
            for width in (0, 0.5, 2, 4):
                output = RenderSvgbobImage(SOURCE, directory, stroke_width=width)
                outputs.append(output)
                svg = output.with_suffix('.svg').read_text()
                self.assertIn(f'stroke-width: {width};', svg)
                with Image.open(output) as image:
                    sizes.append(image.size)
                if width == 2:
                    self.assertEqual(default, output)
            self.assertEqual(4, len(set(outputs)))
            self.assertEqual(1, len(set(sizes)))
            with patch('graphviz_mindmaps.render.svgbob.subprocess.run') as run:
                self.assertEqual(outputs[1], RenderSvgbobImage(SOURCE, directory, stroke_width='0.5'))
                run.assert_not_called()

    @unittest.skipUnless(HAS_SVGBOB, 'optional Svgbob CLI and rsvg-convert required')
    def test_real_color_tokens_gradients_pixels_and_theme_cache(self):
        self.addCleanup(ApplyTheme, 'default')
        source = '''+--------------------+      +--------------------+
|{front}             |      |{jobs}              |
| ccyan API          | ---> | Background workers |
+--------------------+      +--------------------+

# Legend:
front = { fill: linear-gradient(90deg, ccyan, cblue); stroke: cred-10; }
jobs = { fill: radial-gradient(cwhite, cgreen); stroke: cgreen-100; }
'''
        with tempfile.TemporaryDirectory() as directory:
            outputs = []
            for theme in ('default', 'nord', 'default'):
                ApplyTheme(theme)
                output = RenderSvgbobImage(source, directory)
                outputs.append(output)
                root = ElementTree.fromstring(output.with_suffix('.svg').read_text())
                self.assertEqual(4, len(list(root.iter('{http://www.w3.org/2000/svg}stop'))))
                self.assertIn(vrbtcolors['ccyan'], output.with_suffix('.svg').read_text())
                labels = [element.text for element in root.iter('{http://www.w3.org/2000/svg}text')]
                self.assertIn('ccyan', labels)
                self.assertIn('API', labels)
                rectangle = next(element for element in root.iter()
                                 if 'front' in element.get('class', '').split())
                x, y, w, h = [float(rectangle.get(key)) for key in ('x', 'y', 'width', 'height')]
                with Image.open(output) as image:
                    rgba = image.convert('RGBA')
                    self.assertNotEqual(rgba.getpixel((round(x + w * .2), round(y + h * .2))),
                                        rgba.getpixel((round(x + w * .8), round(y + h * .2))))
                    self.assertEqual(0, rgba.getchannel('A').getextrema()[0])
            self.assertNotEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0], outputs[2])
            with patch.dict(vrbtcolors, {'ccyan': '#123456'}):
                output = RenderSvgbobImage(source, directory)
                self.assertNotEqual(outputs[0], output)
                self.assertIn('#123456', output.with_suffix('.svg').read_text())

    @unittest.skipUnless(HAS_SVGBOB, 'optional Svgbob CLI and rsvg-convert required')
    def test_real_gradient_fades_to_transparency_without_black_fringe(self):
        source = '''+--------------------+
|{fade}              |
| Transparent fade   |
+--------------------+

# Legend:
fade = { fill: linear-gradient(90deg, ccyan, ctrans); }
'''
        with tempfile.TemporaryDirectory() as directory:
            output = RenderSvgbobImage(source, directory)
            root = ElementTree.fromstring(output.with_suffix('.svg').read_text())
            rectangle = next(element for element in root.iter()
                             if 'fade' in element.get('class', '').split())
            x, y, w, h = [float(rectangle.get(key)) for key in ('x', 'y', 'width', 'height')]
            with Image.open(output) as image:
                rgba = image.convert('RGBA')
                left = rgba.getpixel((round(x + w * .2), round(y + h * .2)))
                right = rgba.getpixel((round(x + w * .8), round(y + h * .2)))
                self.assertGreater(left[3], right[3])
                self.assertLess(max(abs(a - b) for a, b in zip(left[:3], right[:3])), 4)

    @unittest.skipUnless(HAS_SVGBOB, 'optional Svgbob CLI and rsvg-convert required')
    def test_real_tagged_rectangle_with_touching_arrows_gets_colored(self):
        source = '''+------------+     +------------------+     +------------+
| Source     |---->| Filter processor |---->| Topology   |
|            |     |           {base} |     |            |
+------------+     +------------------+     +------------+

# Legend:
base = { fill: ccyan; stroke: cred-10; }
'''
        with tempfile.TemporaryDirectory() as directory:
            output = RenderSvgbobImage(source, directory, stroke_width=1)
            root = ElementTree.fromstring(output.with_suffix('.svg').read_text())
            namespace = '{http://www.w3.org/2000/svg}'
            rectangle = next(node for node in root.iter(namespace + 'rect')
                             if 'base' in node.get('class', '').split())
            self.assertNotIn('{base}', ''.join(node.text or '' for node in root.iter(namespace + 'text')))
            self.assertIn('Filter', ''.join(root.itertext()))
            raw = subprocess.run([FindSvgbob()], input=source, text=True,
                                 capture_output=True, check=True)
            original = ElementTree.fromstring(raw.stdout)
            self.assertEqual([node.get('points') for node in original.iter(namespace + 'polygon')],
                             [node.get('points') for node in root.iter(namespace + 'polygon')])
            x, y, width, height = [float(rectangle.get(key)) for key in ('x', 'y', 'width', 'height')]
            with Image.open(output) as image:
                pixel = image.convert('RGBA').getpixel((round(x + width / 2), round(y + height * .8)))
                self.assertEqual(ImageColor.getcolor(vrbtcolors['ccyan'], 'RGBA'), pixel)

    @unittest.skipUnless(HAS_SVGBOB, 'optional Svgbob CLI and rsvg-convert required')
    def test_real_font_size_scales_text_grid_and_cache(self):
        source = '''+------------+     +------------------+     +------------+
| Source     |---->| Filter processor |---->| Topology   |
|            |     |           {base} |     |            |
+------------+     +------------------+     +------------+

# Legend:
base = { fill: linear-gradient(90deg, ccyan, cblue); }
'''
        with tempfile.TemporaryDirectory() as directory:
            default = RenderSvgbobImage(source, directory)
            with Image.open(default) as image:
                baseline = image.size
            outputs = []
            for size in (10, 14, 18, 28):
                output = RenderSvgbobImage(source, directory, font_size=size)
                outputs.append(output)
                root = ElementTree.fromstring(output.with_suffix('.svg').read_text())
                self.assertIn(f'font-size: {size}px', ''.join(root.itertext()))
                self.assertIn('stroke-width: 2;', ''.join(root.itertext()))
                self.assertTrue(any('base' in node.get('class', '').split()
                                    for node in root.iter('{http://www.w3.org/2000/svg}rect')))
                self.assertNotIn('{base}', ''.join(root.itertext()))
                with Image.open(output) as image:
                    for expected, actual in zip(baseline, image.size):
                        self.assertAlmostEqual(expected * size / 14, actual, delta=1)
                if size == 14:
                    self.assertEqual(default, output)
            self.assertEqual(4, len(set(outputs)))
            with patch('graphviz_mindmaps.render.svgbob.subprocess.run') as run:
                self.assertEqual(outputs[2], RenderSvgbobImage(source, directory, font_size='18'))
                run.assert_not_called()

    @unittest.skipUnless(HAS_SVGBOB, 'optional Svgbob CLI and rsvg-convert required')
    def test_real_markdown_inherits_font_size_and_explicit_override_wins(self):
        body = MarkdownBody('```svgbob\n' + SOURCE + '```', '<test>', 'Inherited size', 1)
        with tempfile.TemporaryDirectory() as directory:
            inherited = RenderSvgbobImage(SOURCE, directory, font_size=22)
            label = RenderMarkdown(body, [directory], size=22, foreground='#000000', wrap=False)
            self.assertIn(str(inherited), label)
            self.assertIn('font-size: 22px', inherited.with_suffix('.svg').read_text())
            overridden = RenderSvgbobImage(SOURCE, directory, font_size=14)
            label = RenderMarkdown(body, [directory], size=22, foreground='#000000', wrap=False,
                                   svgbob_font_size=14)
            self.assertIn(str(overridden), label)
            self.assertNotEqual(inherited, overridden)

    @unittest.skipUnless(HAS_SVGBOB, 'optional Svgbob CLI and rsvg-convert required')
    def test_real_spacing_unicode_and_literal_xml_characters(self):
        source = '┌───────────────┐\n│ a < b & c > d │\n└───────────────┘\n'
        with tempfile.TemporaryDirectory() as directory:
            output = RenderSvgbobImage(source, directory)
            root = ElementTree.fromstring(output.with_suffix('.svg').read_text())
            text = ''.join(element.text or '' for element in root.iter()
                           if element.tag.endswith('}text'))
            # Svgbob positions separate text fragments on the character grid.
            self.assertIn('a<b&c>d', text.replace(' ', ''))


if __name__ == '__main__':
    unittest.main()
