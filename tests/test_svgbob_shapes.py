import unittest
from xml.etree import ElementTree as ET

from graphviz_mindmaps.render.svgbob_shapes import RecoverSvgbobRectangles, SVG


class SvgbobShapeTests(unittest.TestCase):
    def root(self):
        root = ET.Element(SVG + 'svg')
        ET.SubElement(root, SVG + 'rect', {'class': 'backdrop'})
        return root

    def outline(self, root, left, top, right, bottom):
        group = ET.SubElement(root, SVG + 'g')
        for x1, y1, x2, y2 in ((left, top, right, top), (left, bottom, right, bottom),
                               (left, top, left, bottom), (right, top, right, bottom)):
            ET.SubElement(group, SVG + 'line', dict(zip(('x1', 'y1', 'x2', 'y2'),
                                                      map(str, (x1, y1, x2, y2)))))
        return group

    def test_connected_box_recovers_tag_and_preserves_arrow_and_label(self):
        root = self.root()
        group = self.outline(root, 10, 20, 110, 120)
        connector = ET.SubElement(group, SVG + 'line', x1='110', y1='60', x2='160', y2='60')
        arrow = ET.SubElement(root, SVG + 'polygon', points='160,56 168,60 160,64')
        ET.SubElement(root, SVG + 'text', x='70', y='100').text = '{cpas}'
        ET.SubElement(root, SVG + 'text', x='20', y='60').text = 'Keep label'
        RecoverSvgbobRectangles(root)
        rectangle = root[1]
        self.assertEqual('solid nofill cpas', rectangle.get('class'))
        self.assertEqual(('10', '20', '100', '100'), tuple(rectangle.get(key) for key in ('x', 'y', 'width', 'height')))
        self.assertEqual([connector], list(root.iter(SVG + 'line')))
        self.assertIn(arrow, root)
        self.assertEqual(['Keep label'], [node.text for node in root.iter(SVG + 'text')])

    def test_nested_rectangles_select_smallest_owner_and_combine_tags(self):
        root = self.root()
        self.outline(root, 0, 0, 200, 200)
        self.outline(root, 20, 20, 100, 100)
        ET.SubElement(root, SVG + 'text', x='30', y='40').text = '{cpas}'
        ET.SubElement(root, SVG + 'text', x='30', y='60').text = '{extra,other}'
        RecoverSvgbobRectangles(root)
        rectangles = [node for node in root.iter(SVG + 'rect') if 'cpas' in node.get('class', '')]
        self.assertEqual(1, len(rectangles))
        self.assertEqual('80', rectangles[0].get('width'))
        self.assertEqual('solid nofill cpas extra other', rectangles[0].get('class'))
        self.assertEqual(4, len(list(root.iter(SVG + 'line'))))

    def test_open_contours_and_tags_outside_rectangles_remain_literal(self):
        root = self.root()
        group = self.outline(root, 10, 10, 100, 100)
        group.remove(group[0])
        ET.SubElement(root, SVG + 'text', x='20', y='30').text = '{cpas}'
        ET.SubElement(root, SVG + 'text', x='200', y='200').text = '{outside}'
        before = ET.tostring(root)
        RecoverSvgbobRectangles(root)
        self.assertEqual(before, ET.tostring(root))

    def test_collinear_outline_extensions_are_retained(self):
        root = self.root()
        group = self.outline(root, 10, 20, 110, 120)
        group[0].set('x1', '0')
        group[0].set('x2', '130')
        ET.SubElement(root, SVG + 'text', x='20', y='50').text = '{cpas}'
        RecoverSvgbobRectangles(root)
        remaining = {(node.get('x1'), node.get('x2')) for node in root.iter(SVG + 'line')}
        self.assertEqual({('0', '10'), ('110', '130')}, remaining)
