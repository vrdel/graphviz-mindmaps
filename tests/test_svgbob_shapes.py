import unittest
from xml.etree import ElementTree as ET

from graphviz_mindmaps.render.svgbob_shapes import RecoverSvgbobRectangles, RecoverSvgbobRoundedRectangles, SVG


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

    def test_untagged_connected_rectangles_and_grid_cells_recover_only_when_requested(self):
        root = self.root()
        self.outline(root, 10, 20, 110, 120)
        self.outline(root, 110, 20, 210, 120)
        connector = ET.SubElement(root, SVG + 'line', x1='210', y1='70', x2='250', y2='70')
        before = ET.tostring(root)
        RecoverSvgbobRectangles(root)
        self.assertEqual(before, ET.tostring(root))
        RecoverSvgbobRectangles(root, all_rectangles=True)
        boxes = [node for node in root.iter(SVG + 'rect') if node.get('class') != 'backdrop']
        self.assertEqual(2, len(boxes))
        self.assertEqual(['100', '100'], [node.get('width') for node in boxes])
        self.assertEqual([connector], list(root.iter(SVG + 'line')))

    def rounded(self):
        root = self.root()
        for path in ('M 14,20 A 4,4 0,0,0 10,24', 'M 106,20 A 4,4 0,0,1 110,24',
                     'M 10,116 A 4,4 0,0,0 14,120', 'M 110,116 A 4,4 0,0,1 106,120'):
            ET.SubElement(root, SVG + 'path', d=path, attrib={'class': 'nofill'})
        for x1, y1, x2, y2 in ((14,20,106,20), (14,120,106,120), (10,24,10,116), (110,24,110,116)):
            ET.SubElement(root, SVG + 'line', dict(zip(('x1','y1','x2','y2'), map(str,(x1,y1,x2,y2)))))
        connector = ET.SubElement(root, SVG + 'line', x1='110', y1='60', x2='180', y2='60')
        return root, connector

    def test_rounded_rectangle_preserves_radius_connectors_and_tags(self):
        root, connector = self.rounded()
        arrow = ET.SubElement(root, SVG + 'polygon', points='180,56 188,60 180,64')
        ET.SubElement(root, SVG + 'text', x='30', y='60').text = 'label'
        ET.SubElement(root, SVG + 'text', x='40', y='100').text = '{special}'
        RecoverSvgbobRoundedRectangles(root)
        rect = root[1]
        self.assertEqual(('10','20','100','100','4','4'),
                         tuple(rect.get(k) for k in ('x','y','width','height','rx','ry')))
        self.assertIn('special', rect.get('class'))
        self.assertEqual([connector], list(root.iter(SVG + 'line')))
        self.assertFalse(list(root.iter(SVG + 'path')))
        self.assertIn(arrow, root)
        self.assertEqual(['label'], [e.text for e in root.iter(SVG + 'text')])

    def test_rounded_recovery_requires_a_closed_outline_and_is_opt_in_without_tags(self):
        root, _ = self.rounded()
        before = ET.tostring(root)
        RecoverSvgbobRoundedRectangles(root)
        self.assertEqual(before, ET.tostring(root))
        # A missing side must not be bridged to produce a filled shape.
        root.remove(next(e for e in root if e.tag == SVG + 'line'))
        before = ET.tostring(root)
        RecoverSvgbobRoundedRectangles(root, all_rectangles=True)
        self.assertEqual(before, ET.tostring(root))
        root, _ = self.rounded()
        RecoverSvgbobRoundedRectangles(root, all_rectangles=True)
        self.assertEqual('4', root[1].get('rx'))

    def test_connected_box_recovers_tag_and_preserves_arrow_and_label(self):
        root = self.root()
        group = self.outline(root, 10, 20, 110, 120)
        connector = ET.SubElement(group, SVG + 'line', x1='110', y1='60', x2='160', y2='60')
        arrow = ET.SubElement(root, SVG + 'polygon', points='160,56 168,60 160,64')
        ET.SubElement(root, SVG + 'text', x='70', y='100').text = '{base}'
        ET.SubElement(root, SVG + 'text', x='20', y='60').text = 'Keep label'
        RecoverSvgbobRectangles(root)
        rectangle = root[1]
        self.assertEqual('solid nofill base', rectangle.get('class'))
        self.assertEqual(('10', '20', '100', '100'), tuple(rectangle.get(key) for key in ('x', 'y', 'width', 'height')))
        self.assertEqual([connector], list(root.iter(SVG + 'line')))
        self.assertIn(arrow, root)
        self.assertEqual(['Keep label'], [node.text for node in root.iter(SVG + 'text')])

    def test_nested_rectangles_select_smallest_owner_and_combine_tags(self):
        root = self.root()
        self.outline(root, 0, 0, 200, 200)
        self.outline(root, 20, 20, 100, 100)
        ET.SubElement(root, SVG + 'text', x='30', y='40').text = '{base}'
        ET.SubElement(root, SVG + 'text', x='30', y='60').text = '{extra,other}'
        RecoverSvgbobRectangles(root)
        rectangles = [node for node in root.iter(SVG + 'rect') if 'base' in node.get('class', '')]
        self.assertEqual(1, len(rectangles))
        self.assertEqual('80', rectangles[0].get('width'))
        self.assertEqual('solid nofill base extra other', rectangles[0].get('class'))
        self.assertEqual(4, len(list(root.iter(SVG + 'line'))))

    def test_open_contours_and_tags_outside_rectangles_remain_literal(self):
        root = self.root()
        group = self.outline(root, 10, 10, 100, 100)
        group.remove(group[0])
        ET.SubElement(root, SVG + 'text', x='20', y='30').text = '{base}'
        ET.SubElement(root, SVG + 'text', x='200', y='200').text = '{outside}'
        before = ET.tostring(root)
        RecoverSvgbobRectangles(root)
        self.assertEqual(before, ET.tostring(root))

    def test_collinear_outline_extensions_are_retained(self):
        root = self.root()
        group = self.outline(root, 10, 20, 110, 120)
        group[0].set('x1', '0')
        group[0].set('x2', '130')
        ET.SubElement(root, SVG + 'text', x='20', y='50').text = '{base}'
        RecoverSvgbobRectangles(root)
        remaining = {(node.get('x1'), node.get('x2')) for node in root.iter(SVG + 'line')}
        self.assertEqual({('0', '10'), ('110', '130')}, remaining)
