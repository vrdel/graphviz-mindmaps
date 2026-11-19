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


def RecoverSvgbobRectangles(root, all_rectangles=False):
    """Recover tagged rectangles, or all closed rectangular faces when requested."""
    elements = list(_elements(root))
    tags = []
    for parent, element in elements:
        if element.tag == SVG + 'text':
            match = re.fullmatch(r'\{([A-Za-z_]\w*(?:,[A-Za-z_]\w*)*)\}', element.text or '')
            if match:
                tags.append((parent, element, match.group(1).split(',')))
    if not tags and not all_rectangles:
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
    if all_rectangles:
        # Untagged rectangles touching connectors can also be emitted as lines.
        # Recover closed rectangular faces, excluding spans across grid columns.
        xs = sorted(vertical)
        for index, left in enumerate(xs):
            for right in xs[index + 1:]:
                levels = sorted(y for y, spans in horizontal.items() if _covers(spans, left, right))
                for top, bottom in zip(levels, levels[1:]):
                    if not (_covers(vertical[left], top, bottom) and _covers(vertical[right], top, bottom)):
                        continue
                    if any(left < x < right and _covers(spans, top, bottom)
                           for x, spans in vertical.items()):
                        continue
                    recovered.setdefault((left, top, right, bottom), set())
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
        _remove_outline(root, left, top, right, bottom)


def _remove_outline(root, left, top, right, bottom, rx=0, ry=0):
    """Remove only border segments, preserving connector extensions."""
    for parent, element in list(_elements(root)):
        line = _line(element)
        if not line:
            continue
        axis, coordinate, start, end = line
        if axis == 'horizontal' and coordinate in (top, bottom):
            first, last = left + rx, right - rx
        elif axis == 'vertical' and coordinate in (left, right):
            first, last = top + ry, bottom - ry
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


_NUMBER = r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?'
_CORNER = re.compile(r'^\s*M\s*(' + _NUMBER + r')[,\s]+(' + _NUMBER + r')\s*'
                     r'A\s*(' + _NUMBER + r')[,\s]+(' + _NUMBER + r')[,\s]+'
                     r'0[,\s]+0[,\s]+([01])[,\s]+(' + _NUMBER + r')[,\s]+(' + _NUMBER + r')\s*$')


def _corner(element):
    if element.tag != SVG + 'path':
        return None
    match = _CORNER.fullmatch(element.get('d', ''))
    if not match:
        return None
    x1, y1, rx, ry, sweep, x2, y2 = map(float, match.groups())
    tolerance = max(1e-4, *(abs(v) * 1e-6 for v in (x1,y1,x2,y2)))
    if rx <= 0 or ry <= 0 or abs(abs(x2 - x1) - rx) > tolerance or abs(abs(y2 - y1) - ry) > tolerance:
        return None
    # Normalize direction to run from the upper endpoint to the lower one.
    if y1 > y2:
        x1, y1, x2, y2, sweep = x2, y2, x1, y1, 1 - sweep
    kind = ('tl' if not sweep else 'br') if x2 < x1 else ('tr' if sweep else 'bl')
    return kind, min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), rx, ry


def _rounded_covers(spans, first, last):
    # Svgbob serializes scaled f32 coordinates with slightly different rounding
    # for arc radii and endpoints. Allow subpixel noise, not visible gaps.
    tolerance = max(1e-4, abs(first) * 1e-6, abs(last) * 1e-6)
    return _covers(spans, first + tolerance, last - tolerance)


def RecoverSvgbobRoundedRectangles(root, all_rectangles=False):
    """Join four quarter-ellipse corners only when all four sides are closed."""
    elements = list(_elements(root))
    tags = []
    corners = defaultdict(list)
    horizontal, vertical = defaultdict(list), defaultdict(list)
    for parent, element in elements:
        corner = _corner(element)
        if corner:
            corners[corner[0]].append((parent, element, corner[1:]))
        line = _line(element)
        if line:
            axis, coordinate, start, end = line
            (horizontal if axis == 'horizontal' else vertical)[coordinate].append((start, end))
        if element.tag == SVG + 'text':
            tag = re.fullmatch(r'\{([A-Za-z_]\w*(?:,[A-Za-z_]\w*)*)\}', element.text or '')
            if tag:
                tags.append((parent, element, tag.group(1).split(',')))
    if not all_rectangles and not tags:
        return
    boxes = {}
    for tl in corners['tl']:
        left, top, _, _, rx, ry = tl[2]
        for tr in corners['tr']:
            _, trtop, right, _, trx, try_ = tr[2]
            if trtop != top or (trx, try_) != (rx, ry) or right - left <= 2 * rx:
                continue
            if not _rounded_covers(horizontal[top], left + rx, right - rx):
                continue
            for bl in corners['bl']:
                blleft, _, _, bottom, blrx, blry = bl[2]
                if blleft != left or (blrx, blry) != (rx, ry) or bottom - top <= 2 * ry:
                    continue
                if not (_rounded_covers(vertical[left], top + ry, bottom - ry)
                        and _rounded_covers(vertical[right], top + ry, bottom - ry)
                        and _rounded_covers(horizontal[bottom], left + rx, right - rx)):
                    continue
                for br in corners['br']:
                    _, _, brright, brbottom, brrx, brry = br[2]
                    if (brright, brbottom, brrx, brry) == (right, bottom, rx, ry):
                        boxes[(left, top, right, bottom, rx, ry)] = [tl, tr, bl, br]
    # Prefer the smallest closed contours if a layout admits competing cycles.
    selected, used_arcs = {}, set()
    for box in sorted(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1])):
        arcs = {arc for _, arc, _ in boxes[box]}
        if not arcs & used_arcs:
            selected[box] = boxes[box]
            used_arcs.update(arcs)
    boxes = selected
    classes = defaultdict(set)
    for parent, tag, names in tags:
        x, y = float(tag.get('x')), float(tag.get('y'))
        owners = [box for box in boxes if box[0] < x < box[2] and box[1] < y < box[3]]
        if owners:
            owner = min(owners, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
            classes[owner].update(names)
            parent.remove(tag)
    insertion = next((i + 1 for i, e in enumerate(root)
                      if 'backdrop' in e.get('class', '').split()), 0)
    for box in sorted(boxes, key=lambda b: -(b[2] - b[0]) * (b[3] - b[1])):
        if not all_rectangles and not classes[box]:
            continue
        left, top, right, bottom, rx, ry = box
        rectangle = ET.Element(SVG + 'rect', {
            'x': f'{left:g}', 'y': f'{top:g}', 'width': f'{right-left:g}', 'height': f'{bottom-top:g}',
            'rx': f'{rx:g}', 'ry': f'{ry:g}', 'class': 'solid nofill ' + ' '.join(sorted(classes[box])),
        })
        root.insert(insertion, rectangle)
        insertion += 1
        for parent, arc, _ in boxes[box]:
            parent.remove(arc)
        _remove_outline(root, left, top, right, bottom, rx, ry)
