from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET

from graphviz_mindmaps.render.mermaid import RenderMermaidImage, ParseMermaidSketch
from graphviz_mindmaps.render.mermaid_sketch import ApplyMermaidSketch
from graphviz_mindmaps.render.svgbob_sketch import SVG
from tests.test_mermaid import HAS_PELE

SOURCE = '''flowchart LR
 subgraph Pipeline
 A[Input] --> B{Ready}
 B -.-> C(Output)
 end
 style A fill:ccyan,stroke:cred,stroke-width:3px
'''


class MermaidSketchTests(unittest.TestCase):
    def test_validation(self):
        self.assertEqual((False, 1), ParseMermaidSketch())
        self.assertEqual((True, .5), ParseMermaidSketch('on', '.5'))
        for value in ('yes', '1'):
            with self.assertRaisesRegex(ValueError, 'mermaid_sketch'):
                ParseMermaidSketch(value)
        for value in ('nan', 'inf', -1, 6, 'bad'):
            with self.assertRaisesRegex(ValueError, 'mermaid_roughness'):
                ParseMermaidSketch('on', value)

    @unittest.skipUnless(HAS_PELE, 'Pele, Node and librsvg required')
    def test_real_sketch_preserves_labels_fills_markers_and_scale(self):
        with tempfile.TemporaryDirectory() as directory:
            plain = RenderMermaidImage(SOURCE, directory, width=None)
            sketch = RenderMermaidImage(SOURCE, directory, width=None, sketch='on')
            before = ET.parse(plain.with_suffix('.svg')).getroot()
            after = ET.parse(sketch.with_suffix('.svg')).getroot()
            for selector in ('text',):
                self.assertEqual([ET.tostring(e) for e in before.iter(SVG+selector)],
                                 [ET.tostring(e) for e in after.iter(SVG+selector)])
            markers = lambda root: [ET.tostring(e) for e in root.iter() if 'pele-marker' in e.get('class', '').split()]
            self.assertTrue(markers(before))
            self.assertEqual(markers(before), markers(after))
            self.assertEqual([e.get('fill') for e in before.iter(SVG+'rect')],
                             [e.get('fill') for e in after.iter(SVG+'rect')])
            self.assertGreater(len(list(after.iter(SVG+'path'))), len(list(before.iter(SVG+'path'))))
            self.assertNotEqual(plain.read_bytes(), sketch.read_bytes())
            vb = list(map(float, after.get('viewBox').split()))
            self.assertAlmostEqual(float(before.get('width')) / float(before.get('viewBox').split()[2]),
                                   float(after.get('width')) / vb[2])
            original = sketch.with_suffix('.svg').read_bytes()
            sketch.unlink()
            self.assertEqual(sketch, RenderMermaidImage(SOURCE, directory, width=None, sketch='on'))
            self.assertEqual(original, sketch.with_suffix('.svg').read_bytes())
            with patch('graphviz_mindmaps.render.mermaid.subprocess.run') as run:
                self.assertEqual(sketch, RenderMermaidImage(SOURCE, directory, width=None, sketch='on'))
                run.assert_not_called()
            strong = RenderMermaidImage(SOURCE, directory, width=None, sketch=True, roughness=2)
            self.assertNotEqual(sketch, strong)
            self.assertNotEqual(original, strong.with_suffix('.svg').read_bytes())
            self.assertEqual(plain, RenderMermaidImage(SOURCE, directory, width=None, sketch='off', roughness=2))

    @unittest.skipUnless(HAS_PELE, 'Pele, Node and librsvg required')
    def test_other_diagram_types(self):
        with tempfile.TemporaryDirectory() as directory:
            for source in ('sequenceDiagram\nAlice->>Bob: Hello',
                           'classDiagram\nAnimal <|-- Duck',
                           'mindmap\n root((Plan))\n  Work\n  Rest',
                           'pie title Time\n"Work":8\n"Rest":16'):
                with self.subTest(source=source):
                    self.assertTrue(RenderMermaidImage(source, directory, sketch=True).exists())

    @unittest.skipUnless(HAS_PELE, 'Pele, Node and librsvg required')
    def test_transformed_bounds_and_invisible_shapes(self):
        root = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 20 20">
          <g transform="translate(100,50) scale(2)" stroke="red" stroke-width="3">
            <rect width="10" height="10" fill="blue"/>
            <path d="M0 0L10 10" stroke="none"/>
          </g></svg>''')
        invisible = ET.tostring(root[0][1])
        ApplyMermaidSketch(root)
        self.assertEqual(invisible, ET.tostring(root[0][-1]))
        self.assertGreater(float(root.get('width')), 120)
        self.assertGreater(float(root.get('height')), 70)
        self.assertTrue(all(e.get('stroke') == 'red' for e in root[0][1:-1]))
