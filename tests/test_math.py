from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET

from PIL import Image

from graphviz_mindmaps.model.document import MarkdownBody
from graphviz_mindmaps.parser.markdown import ParseMarkdown
from graphviz_mindmaps.render.markdown import RenderMarkdown

ROOT = Path(__file__).resolve().parents[1]
SVG = '{http://www.w3.org/2000/svg}'
HAS_MATHJAX = bool(shutil.which('node') and shutil.which('rsvg-convert') and
                   (ROOT / 'node_modules/@mathjax/src/package.json').exists())


def body(source, locations=None):
    return MarkdownBody(source, 'example.otl', 'Equations', 4, locations=locations or [])


class MathParsingTests(unittest.TestCase):
    def test_inline_display_and_tex_contents_are_preserved(self):
        blocks = ParseMarkdown(body(r'Value $a -> b$ and $\alpha + \beta$.' + '\n\n$$\n'
                                    + r'\frac{x}{y}' + '\n$$'))
        self.assertEqual(['paragraph', 'math_block'], [b.kind for b in blocks])
        self.assertEqual(['a -> b', r'\alpha + \beta'], [r.text for r in blocks[0].runs if r.math])
        self.assertEqual(r'\frac{x}{y}', blocks[1].source.strip())
        self.assertEqual(2, blocks[1].source_line)

    def test_code_escaped_dollars_currency_and_existing_list_marker_stay_literal(self):
        source = r'Cost $5 and $10; escaped \$x\$; code `$x$`.' + '\n\n- $ existing callout\n\n```text\n$x$\n```'
        blocks = ParseMarkdown(body(source))
        self.assertFalse(any(r.math for b in blocks for r in b.runs))
        self.assertEqual('$x$', blocks[-1].source.strip())
        self.assertTrue(blocks[1].children[0].callout)
        self.assertEqual('existing callout', blocks[1].children[0].children[0].runs[0].text)

    def test_math_inside_emphasis_highlights_and_links_retains_context(self):
        runs = ParseMarkdown(body(r'**$x$** ==$y$== [$z$](https://example.org)'))[0].runs
        maths = [r for r in runs if r.math]
        self.assertTrue(maths[0].bold)
        self.assertTrue(maths[1].highlight)
        self.assertEqual('https://example.org', maths[2].link)

    def test_rawmarkers_preserves_tex_and_does_not_disable_math(self):
        source = body(r'$a -> b$')
        source.rawmarkers = True
        run, = ParseMarkdown(source)[0].runs
        self.assertTrue(run.math)
        self.assertEqual('a -> b', run.text)


class MathRenderingTests(unittest.TestCase):
    def graphviz(self, label):
        if not shutil.which('dot'):
            self.skipTest('Graphviz required')
        result = subprocess.run(['dot', '-Tsvg'], input='digraph { n [shape=plain label=<' + label + '>]; }',
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn('Warning:', result.stderr)
        return result.stdout

    def test_math_errors_include_outline_location(self):
        source = body('Text\n\n$$\n\\bad\n$$', [(10+i, 3) for i in range(5)])
        with patch('graphviz_mindmaps.render.markdown.RenderMathImage', side_effect=ValueError('invalid TeX')):
            with self.assertRaisesRegex(ValueError, r'example.otl:12: Markdown node.*invalid TeX'):
                RenderMarkdown(source, [])
            source = body(r'$\bad$', [(21, 3)])
            with self.assertRaisesRegex(ValueError, r'example.otl:21: Markdown node.*invalid TeX'):
                RenderMarkdown(source, [])

    def test_plain_markdown_does_not_invoke_mathjax(self):
        with patch('graphviz_mindmaps.render.markdown.RenderMathImage', side_effect=AssertionError('unexpected math rendering')) as render:
            RenderMarkdown(body(r'Cost $5 or $10 and `$x$`.'), [])
            render.assert_not_called()

    @unittest.skipUnless(HAS_MATHJAX, 'MathJax, Node and librsvg required')
    def test_real_inline_and_display_math_in_nested_markdown_and_wrapping(self):
        inline = r'Energy $E=mc^2$ and a fraction $\frac{a}{b}$ in text.'
        nested = ('## Heading $x^2$\n\n' + inline + '\n\n==Math $a+b$==\n\n' +
                  r'- Item $\alpha+\beta$' + '\n\n> Quote $x+y$\n\n::: info Equation\n' + inline + '\n:::\n\n' +
                  '| Symbol | Value |\n| --- | --- |\n| $x$ | $y$ |\n\n$$\n' +
                  r'\begin{bmatrix}a & b \\ c & d\end{bmatrix}' + '\n$$')
        with tempfile.TemporaryDirectory() as directory:
            label = RenderMarkdown(body(nested), [directory], foreground='#123456', size=18, width=260)
            self.assertGreater(len(re.findall('<IMG SRC=', label)), 8)
            self.graphviz(label)
            text = 'Words before $x+y=2$ and many more words after the equation to wrap.'
            wrapped = RenderMarkdown(body(text), [directory], width=100, wrap=True)
            natural = RenderMarkdown(body(text), [directory], width=100, wrap=False)
            self.graphviz(wrapped)
            self.graphviz(natural)
            self.assertGreater(wrapped.count('<TR>'), natural.count('<TR>'))
            # Oversized display equations follow md_wrap; unwrapped ones keep
            # natural dimensions and can expand their node.
            long = body('$$' + '+'.join('x' for _ in range(30)) + '$$')
            labels = [RenderMarkdown(long, [directory], width=100, wrap=wrap) for wrap in (True, False)]
            paths = [re.search(r'<IMG SRC="([^"]+)"', label).group(1) for label in labels]
            self.assertNotEqual(paths[0], paths[1])
            with Image.open(paths[0]) as image:
                self.assertLessEqual(image.width, 134)
            self.graphviz(labels[0])
            self.graphviz(labels[1])
