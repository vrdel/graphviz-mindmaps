import unittest
from xml.etree import ElementTree as ET

from graphviz_mindmaps.render.svgbob_styles import StyleSvgbobSvg, SVG


PALETTE = {'ccyan': '#aaddff', 'cblue': '#224488', 'cred': '#ffaaaa',
           'corang': '#ffcc88', 'cwhite': '#ffffff', 'ctrans': 'transparent'}


class SvgbobStyleTests(unittest.TestCase):
    def test_tokens_aliases_shades_and_literal_text(self):
        root = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
          <style>.box {fill:ccyan;stroke:cred-10;stroke-width:4px;color:corange10;}
          .plain {fill:red;stroke:#f9f;font-family:ccyan;}</style>
          <rect fill="ctrans" style="stroke:ccyan !important"/>
          <text id="ccyan">fill:ccyan; linear-gradient(ccyan,cblue)</text>
        </svg>''')
        result = ET.fromstring(StyleSvgbobSvg(root, PALETTE))
        styles = result.find(SVG + 'style').text
        self.assertIn('fill:#aaddff', styles)
        self.assertIn('stroke:#f5a0a0', styles)
        self.assertIn('color:#ffd692', styles)
        self.assertIn('stroke-width:4px', styles)
        self.assertIn('fill:red;stroke:#f9f;font-family:ccyan', styles)
        rect = result.find(SVG + 'rect')
        self.assertEqual('transparent', rect.get('fill'))
        self.assertEqual('stroke:#aaddff !important', rect.get('style'))
        text = result.find(SVG + 'text')
        self.assertEqual('ccyan', text.get('id'))
        self.assertEqual('fill:ccyan; linear-gradient(ccyan,cblue)', text.text)

    def test_linear_radial_and_transparent_gradients_reuse_definitions(self):
        root = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
          <style>.a {fill:linear-gradient(90deg, ccyan, cblue, ctrans);}
          .b {fill:radial-gradient(cwhite, rgb(1,2,3));}</style>
          <rect fill="linear-gradient(90deg, ccyan, cblue, ctrans)"/>
          <path stroke="linear-gradient(to bottom, cred, cblue)"/>
        </svg>''')
        result = ET.fromstring(StyleSvgbobSvg(root, PALETTE))
        definitions = result.find(SVG + 'defs')
        self.assertEqual(3, len(definitions))
        first, radial, vertical = definitions
        self.assertEqual(('0%', '100%'), (first.get('x1'), first.get('x2')))
        self.assertEqual(['0%', '50%', '100%'], [stop.get('offset') for stop in first])
        self.assertEqual(['#aaddff', '#224488', '#224488'], [stop.get('stop-color') for stop in first])
        self.assertEqual('0', first[-1].get('stop-opacity'))
        self.assertEqual(SVG + 'radialGradient', radial.tag)
        self.assertEqual('#010203', radial[-1].get('stop-color'))
        self.assertEqual(('0%', '100%'), (vertical.get('y1'), vertical.get('y2')))
        self.assertEqual(f'url(#{first.get("id")})', result.find(SVG + 'rect').get('fill'))

    def test_invalid_gradients_fail_clearly(self):
        for value in ('linear-gradient(ccyan)', 'linear-gradient(nope, ccyan)',
                      'linear-gradient(nandeg, ccyan, cblue)', 'linear-gradient(ccyan,,cblue)',
                      'radial-gradient(cwhite)', 'linear-gradient(90deg, ccyan, cblue'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'Svgbob gradient'):
                root = ET.Element(SVG + 'svg')
                ET.SubElement(root, SVG + 'rect', fill=value)
                StyleSvgbobSvg(root, PALETTE)

    def test_existing_gradient_ids_and_paints_are_preserved(self):
        root = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg">
          <defs><linearGradient id="gvmm-svgbob-gradient-0"/></defs>
          <rect fill="linear-gradient(ccyan,cblue)"/>
          <path fill="url(#gvmm-svgbob-gradient-0)"/>
        </svg>''')
        result = ET.fromstring(StyleSvgbobSvg(root, PALETTE))
        self.assertNotEqual(result.find(SVG + 'rect').get('fill'), result.find(SVG + 'path').get('fill'))
        self.assertEqual('url(#gvmm-svgbob-gradient-0)', result.find(SVG + 'path').get('fill'))
