"""Replace Pele's visible SVG outlines with deterministic Rough.js strokes."""
import json
import math
import re
import shutil
import subprocess
from xml.etree import ElementTree as ET

from graphviz_mindmaps.render.svgbob_sketch import HELPER, SVG, _shape


def _multiply(a, b):
    x, y, z, w, u, v = a
    X, Y, Z, W, U, V = b
    return (x*X+z*Y, y*X+w*Y, x*Z+z*W, y*Z+w*W, x*U+z*V+u, y*U+w*V+v)


def _transform(value):
    result = (1, 0, 0, 1, 0, 0)
    for name, args in re.findall(r'(\w+)\(([^)]*)\)', value):
        n = [float(x) for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?', args)]
        if name == 'translate':
            step = (1, 0, 0, 1, n[0], n[1] if len(n) > 1 else 0)
        elif name == 'scale':
            step = (n[0], 0, 0, n[1] if len(n) > 1 else n[0], 0, 0)
        elif name == 'matrix':
            step = tuple(n)
        elif name == 'rotate':
            c, s = math.cos(math.radians(n[0])), math.sin(math.radians(n[0]))
            step = (c, s, -s, c, 0, 0)
            if len(n) == 3:
                step = _multiply(_multiply((1,0,0,1,n[1],n[2]), step), (1,0,0,1,-n[1],-n[2]))
        elif name in {'skewX', 'skewY'}:
            t = math.tan(math.radians(n[0]))
            step = (1, 0, t, 1, 0, 0) if name == 'skewX' else (1, t, 0, 1, 0, 0)
        else:
            raise ValueError(f'unsupported Pele SVG transform: {name}')
        result = _multiply(result, step)
    return result


def ApplyMermaidSketch(root, roughness=1):
    items = []

    def visit(parent, inherited, matrix):
        for child in list(parent):
            if child.tag in {SVG+x for x in ('defs', 'text', 'style', 'clipPath', 'mask', 'marker')}:
                continue
            paint = dict(inherited)
            paint.update(child.attrib)
            paint.update((key.strip(), value.strip().removesuffix('!important').strip())
                         for part in child.get('style', '').split(';') if ':' in part
                         for key, value in [part.split(':', 1)])
            transform = _multiply(matrix, _transform(child.get('transform', '')))
            shape = _shape(child)
            stroke = paint.get('stroke', 'none')
            width = float(paint.get('stroke-width', '1').removesuffix('px'))
            if (shape and stroke not in {'none', 'transparent'} and width > 0
                    and 'pele-marker' not in child.get('class', '').split()):
                # CSS rx is used for Pele's default rounded rectangles.
                if child.tag == SVG+'rect' and 'rx' in paint and 'rx' not in child.attrib:
                    geometry = ET.Element(child.tag, child.attrib)
                    geometry.set('rx', paint['rx'].removesuffix('px'))
                    shape = _shape(geometry)
                shape['strokeWidth'] = width
                items.append((parent, child, shape, paint, transform))
            visit(child, paint, transform)

    root_paint = dict(root.attrib)
    root_paint.update((key.strip(), value.strip())
                      for part in root.get('style', '').split(';') if ':' in part
                      for key, value in [part.split(':', 1)])
    visit(root, root_paint, _transform(root.get('transform', '')))
    if not items:
        return
    result = subprocess.run([shutil.which('node') or 'node', str(HELPER)],
        input=json.dumps({'shapes': [item[2] for item in items], 'roughness': roughness,
                          'strokeWidth': 1}), text=True, capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError('Mermaid sketch rendering failed: ' + result.stderr.strip())
    try:
        sketches = json.loads(result.stdout)
        if len(sketches) != len(items):
            raise ValueError('shape count mismatch')
    except (ValueError, TypeError) as exc:
        raise ValueError('Rough.js returned invalid sketch data') from exc
    x, y, w, h = map(float, root.get('viewBox').split())
    left, top, right, bottom = x, y, x+w, y+h
    for (parent, original, shape, paint, matrix), sketch in zip(items, sketches):
        original.set('style', original.get('style', '') + ';stroke:none !important')
        attrs = {key: paint[key] for key in ('stroke', 'stroke-width', 'stroke-dasharray',
                 'stroke-dashoffset', 'stroke-linecap', 'stroke-linejoin', 'stroke-opacity') if key in paint}
        # These properties are already inherited from the parent; copy only local values.
        local = dict(original.attrib)
        local.update((key.strip(), value.strip())
                     for part in original.get('style', '').split(';') if ':' in part
                     for key, value in [part.split(':', 1)])
        for key in ('transform', 'opacity', 'clip-path', 'mask'):
            if key in local:
                attrs[key] = local[key]
        attrs['fill'] = 'none'
        index = list(parent).index(original) + 1
        for path in sketch['paths']:
            parent.insert(index, ET.Element(SVG+'path', dict(attrs, d=path)))
            index += 1
        if sketch['bounds']:
            x1, y1, x2, y2 = sketch['bounds']
            a,b,c,d,e,f = matrix
            pad = shape['strokeWidth'] * max(math.hypot(a,b), math.hypot(c,d))
            for px, py in ((x1,y1), (x1,y2), (x2,y1), (x2,y2)):
                X, Y = a*px+c*py+e, b*px+d*py+f
                left,top,right,bottom = min(left,X-pad),min(top,Y-pad),max(right,X+pad),max(bottom,Y+pad)
    left,top,right,bottom = math.floor(left),math.floor(top),math.ceil(right),math.ceil(bottom)
    root.set('viewBox', f'{left} {top} {right-left} {bottom-top}')
    # Expand the canvas without changing the diagram's scale.
    root.set('width', str(float(root.get('width')) * (right-left)/w))
    root.set('height', str(float(root.get('height')) * (bottom-top)/h))
