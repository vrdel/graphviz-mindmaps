"""Resolve mindmap colors and gradient paints in Svgbob's SVG styles."""
import math
import re
from xml.etree import ElementTree as ET

from PIL import ImageColor

from graphviz_mindmaps.render.diagram_colors import ResolveDiagramColor


SVG = '{http://www.w3.org/2000/svg}'
COLOR_PROPERTIES = {'fill', 'stroke', 'color', 'stop-color', 'flood-color', 'lighting-color'}


def _arguments(value):
    parts, start, depth = [], 0, 0
    for index, char in enumerate(value):
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif char == ',' and depth == 0:
            parts.append(value[start:index].strip())
            start = index + 1
        if depth < 0:
            raise ValueError('invalid Svgbob gradient parentheses')
    if depth:
        raise ValueError('invalid Svgbob gradient parentheses')
    parts.append(value[start:].strip())
    return parts


def StyleSvgbobSvg(root, color_tokens):
    """Transform only paint declarations, never labels, class names, or geometry."""
    gradients = {}
    ids = {element.get('id') for element in root.iter()}

    def gradient(value):
        if value in gradients:
            return gradients[value]
        match = re.fullmatch(r'(linear|radial)-gradient\((.*)\)', value, re.I | re.S)
        if not match:
            raise ValueError(f'invalid Svgbob gradient: {value}')
        kind, content = match.groups()
        stops = _arguments(content)
        angle = 180.0
        directions = {'to top': 0, 'to right': 90, 'to bottom': 180, 'to left': 270,
                      'to top right': 45, 'to bottom right': 135,
                      'to bottom left': 225, 'to top left': 315}
        if kind.lower() == 'linear' and stops:
            direction = stops[0].lower()
            if direction in directions:
                angle = directions[direction]
                stops.pop(0)
            elif direction.endswith('deg'):
                try:
                    angle = float(direction[:-3])
                except ValueError:
                    raise ValueError(f'invalid Svgbob gradient angle: {direction}') from None
                if not math.isfinite(angle):
                    raise ValueError('Svgbob gradient angle must be finite')
                stops.pop(0)
        if len(stops) < 2 or any(not stop for stop in stops):
            raise ValueError('Svgbob gradients require at least two colors')
        paints = []
        for stop in stops:
            color = ResolveDiagramColor(stop, color_tokens).strip()
            if color.lower() == 'transparent':
                paints.append((0, 0, 0, 0))
                continue
            try:
                paints.append(ImageColor.getcolor(color, 'RGBA'))
            except (ValueError, TypeError):
                raise ValueError(f'invalid Svgbob gradient color: {stop}') from None
        identifier = f'gvmm-svgbob-gradient-{len(gradients)}'
        while identifier in ids:
            identifier += '-g'
        ids.add(identifier)
        if kind.lower() == 'linear':
            radians = math.radians(angle % 360)
            dx, dy = math.sin(radians), -math.cos(radians)
            extent = max(abs(dx), abs(dy))
            dx, dy = dx / extent * 50, dy / extent * 50
            attributes = {'x1': f'{50 - dx:g}%', 'y1': f'{50 - dy:g}%',
                          'x2': f'{50 + dx:g}%', 'y2': f'{50 + dy:g}%'}
            element = ET.Element(SVG + 'linearGradient', id=identifier, **attributes)
        else:
            element = ET.Element(SVG + 'radialGradient', id=identifier, cx='50%', cy='50%', r='50%')
        opaque = [(index, color) for index, color in enumerate(paints) if color[3]]
        for index, (red, green, blue, alpha) in enumerate(paints):
            if not alpha and opaque:
                # Keep transparent fades from interpolating toward black.
                _, nearest = min(opaque, key=lambda item: abs(item[0] - index))
                red, green, blue = nearest[:3]
            ET.SubElement(element, SVG + 'stop', {
                'offset': f'{100 * index / (len(paints) - 1):g}%',
                'stop-color': f'#{red:02x}{green:02x}{blue:02x}',
                'stop-opacity': f'{alpha / 255:g}',
            })
        definitions = root.find(SVG + 'defs')
        if definitions is None:
            definitions = ET.SubElement(root, SVG + 'defs')
        definitions.append(element)
        paint = f'url(#{identifier})'
        gradients[value] = paint
        return paint

    def paint(property, value):
        if property.lower() not in COLOR_PROPERTIES:
            return value
        stripped = value.strip()
        important = re.search(r'\s*!important\s*$', stripped, re.I)
        if important:
            stripped = stripped[:important.start()].strip()
        if re.match(r'(?:linear|radial)-gradient\b', stripped, re.I):
            if property.lower() not in {'fill', 'stroke'}:
                raise ValueError('Svgbob gradients can be used for fill or stroke')
            return gradient(stripped) + (' !important' if important else '')
        return ResolveDiagramColor(value, color_tokens)

    declaration = re.compile(
        r'(?P<prefix>(?:^|[;{])\s*(?P<property>[\w-]+)\s*:\s*)(?P<value>[^;{}]*)(?=[;}]|$)',
        re.M,
    )

    def styles(value):
        return declaration.sub(lambda match: match['prefix'] + paint(match['property'], match['value']), value)

    # Snapshot the elements before adding gradient definitions during traversal.
    for element in list(root.iter()):
        if element.tag == SVG + 'style' and element.text:
            element.text = styles(element.text)
        if 'style' in element.attrib:
            element.set('style', styles(element.get('style')))
        for property in COLOR_PROPERTIES & element.attrib.keys():
            element.set(property, paint(property, element.get(property)))
    return ET.tostring(root, encoding='unicode')
