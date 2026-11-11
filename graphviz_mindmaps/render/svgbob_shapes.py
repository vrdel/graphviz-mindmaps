"""Recover tagged rectangular outlines Svgbob groups with touching connectors."""
from collections import defaultdict
from copy import deepcopy
import re
from xml.etree import ElementTree as ET


SVG = '{http://www.w3.org/2000/svg}'
EPSILON = 1e-6


def _elements(parent):
    for child in list(parent):
        if child.tag != SVG + 'defs':
            yield parent, child
            yield from _elements(child)


def _line(element):
    if element.tag != SVG + 'line':
        return None
    try:
        x1, y1, x2, y2 = (float(element.get(key)) for key in ('x1', 'y1', 'x2', 'y2'))
    except (TypeError, ValueError):
        return None
    if y1 == y2:
        return 'horizontal', y1, min(x1, x2), max(x1, x2)
    if x1 == x2:
        return 'vertical', x1, min(y1, y2), max(y1, y2)
    return None


def _covers(segments, start, end):
    cursor = start
    for first, last in sorted(segments):
        if first > cursor + EPSILON:
            return False
        cursor = max(cursor, last)
        if cursor >= end - EPSILON:
            return True
    return False


def RecoverSvgbobRectangles(root):
    """Restore missing tag owners using closed SVG line cycles, without moving edges."""
    elements = list(_elements(root))
    tags = []
    for parent, element in elements:
        if element.tag == SVG + 'text':
            match = re.fullmatch(r'\{([A-Za-z_]\w*(?:,[A-Za-z_]\w*)*)\}', element.text or '')
            if match:
                tags.append((parent, element, match.group(1).split(',')))
    if not tags:
        return
    horizontal, vertical = defaultdict(list), defaultdict(list)
    for _, element in elements:
        line = _line(element)
        if line:
            axis, coordinate, start, end = line
            (horizontal if axis == 'horizontal' else vertical)[coordinate].append((start, end))
    recovered = {}
    for parent, tag, classes in tags:
        x, y = float(tag.get('x')), float(tag.get('y'))
        candidates = []
        sides = [value for value, spans in vertical.items() if any(a <= y <= b for a, b in spans)]
        for left in (value for value in sides if value < x):
            for right in (value for value in sides if value > x):
                tops = [value for value, spans in horizontal.items()
                        if value < y and _covers(spans, left, right)]
                bottoms = [value for value, spans in horizontal.items()
                           if value > y and _covers(spans, left, right)]
                if tops and bottoms:
                    top, bottom = max(tops), min(bottoms)
                    if _covers(vertical[left], top, bottom) and _covers(vertical[right], top, bottom):
                        candidates.append((left, top, right, bottom))
        if candidates:
            bounds = min(candidates, key=lambda box: (box[2] - box[0]) * (box[3] - box[1]))
            recovered.setdefault(bounds, set()).update(classes)
            parent.remove(tag)
    # Add enclosing fills first so nested rectangles remain visible.
    insertion = next((index + 1 for index, element in enumerate(root)
                      if 'backdrop' in element.get('class', '').split()), 0)
    for (left, top, right, bottom), classes in sorted(
        recovered.items(), key=lambda item: -(item[0][2] - item[0][0]) * (item[0][3] - item[0][1]),
    ):
        rectangle = ET.Element(SVG + 'rect', {
            'x': f'{left:g}', 'y': f'{top:g}', 'width': f'{right - left:g}',
            'height': f'{bottom - top:g}', 'rx': '0',
            'class': 'solid nofill ' + ' '.join(sorted(classes)),
        })
        root.insert(insertion, rectangle)
        insertion += 1
        # Replace the outline with the styled rectangle, retaining any line
        # portions extending beyond it and all touching arrow geometry.
        for parent, element in list(_elements(root)):
            line = _line(element)
            if not line:
                continue
            axis, coordinate, start, end = line
            if axis == 'horizontal' and coordinate in (top, bottom):
                first, last = left, right
            elif axis == 'vertical' and coordinate in (left, right):
                first, last = top, bottom
            else:
                continue
            if end <= first or start >= last:
                continue
            pieces = [(a, b) for a, b in ((start, min(end, first)), (max(start, last), end)) if b > a]
            for a, b in pieces:
                remaining = deepcopy(element)
                keys = ('x1', 'x2') if axis == 'horizontal' else ('y1', 'y2')
                for key, value in zip(keys, (a, b)):
                    remaining.set(key, f'{value:g}')
                parent.insert(list(parent).index(element), remaining)
            parent.remove(element)
