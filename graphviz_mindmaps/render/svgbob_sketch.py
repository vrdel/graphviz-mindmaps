"""Optional deterministic Rough.js strokes, preserving SVG fills and labels."""
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
from xml.etree import ElementTree as ET

SVG = '{http://www.w3.org/2000/svg}'
HELPER = Path(__file__).with_suffix('.mjs')


def ParseSvgbobSketch(value=None, roughness=None):
    enabled = False
    if isinstance(value, bool):
        enabled = value
    elif value is not None:
        if str(value).lower() not in {'on', 'off'}:
            raise ValueError('svgbob_sketch must be on or off')
        enabled = str(value).lower() == 'on'
    try:
        amount = 1.0 if roughness is None else float(roughness)
    except (TypeError, ValueError):
        raise ValueError('svgbob_roughness must be a finite number between 0 and 5') from None
    if not math.isfinite(amount) or not 0 <= amount <= 5:
        raise ValueError('svgbob_roughness must be a finite number between 0 and 5')
    return enabled, amount


def SketchProfile():
    if not shutil.which('node'):
        raise ValueError('svgbob_sketch=on requires Node.js on PATH and Rough.js; run npm ci')
    return {'helper': hashlib.sha256(HELPER.read_bytes()).hexdigest(), 'roughjs': '4.6.6', 'seed': 17}


def _shape(element):
    def n(key, default=0):
        return float(element.get(key, default))
    if element.tag == SVG + 'line':
        return {'kind': 'path', 'path': f"M{n('x1')},{n('y1')} L{n('x2')},{n('y2')}"}
    if element.tag == SVG + 'path':
        return {'kind': 'path', 'path': element.get('d', '')}
    if element.tag in {SVG + 'circle', SVG + 'ellipse'}:
        rx = n('r') if element.tag == SVG + 'circle' else n('rx')
        ry = n('r') if element.tag == SVG + 'circle' else n('ry')
        return {'kind': 'ellipse', 'coordinates': [n('cx'), n('cy'), 2*rx, 2*ry]}
    if element.tag == SVG + 'rect':
        x, y, w, h = n('x'), n('y'), n('width'), n('height')
        rx, ry = min(n('rx'), w/2), min(n('ry', element.get('rx', 0)), h/2)
        if rx and ry:
            path = (f'M{x+rx},{y} H{x+w-rx} A{rx},{ry} 0 0 1 {x+w},{y+ry} '
                    f'V{y+h-ry} A{rx},{ry} 0 0 1 {x+w-rx},{y+h} H{x+rx} '
                    f'A{rx},{ry} 0 0 1 {x},{y+h-ry} V{y+ry} A{rx},{ry} 0 0 1 {x+rx},{y} Z')
        else:
            path = f'M{x},{y} H{x+w} V{y+h} H{x} Z'
        return {'kind': 'path', 'path': path}
    if element.tag in {SVG + 'polygon', SVG + 'polyline'}:
        return {'kind': 'path', 'path': 'M' + element.get('points', '') + (' Z' if element.tag == SVG + 'polygon' else '')}
    return None


def ApplySvgbobSketch(root, roughness=1, stroke_width=2):
    items = []
    def visit(parent):
        for child in list(parent):
            if child.tag in {SVG+'defs', SVG+'text', SVG+'style'}:
                continue
            classes = set(child.get('class', '').split())
            if not classes & {'backdrop', 'filled', 'bg_filled'}:
                shape = _shape(child)
                if shape:
                    items.append((parent, child, shape))
            visit(child)
    visit(root)
    if not items or stroke_width == 0:
        return
    result = subprocess.run([shutil.which('node') or 'node', str(HELPER)],
        input=json.dumps({'shapes': [s for _, _, s in items], 'roughness': roughness,
                          'strokeWidth': stroke_width}), text=True, capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError('Svgbob sketch rendering failed: ' + result.stderr.strip())
    try:
        sketches = json.loads(result.stdout)
        if len(sketches) != len(items):
            raise ValueError('shape count mismatch')
    except (ValueError, TypeError) as exc:
        raise ValueError('Rough.js returned invalid sketch data') from exc
    left, top, right, bottom = 0, 0, float(root.get('width')), float(root.get('height'))
    for (parent, original, _), sketch in zip(items, sketches):
        # Keep each original fill exactly as it was; only replace the outline.
        style = original.get('style', '')
        original.set('style', style + ';stroke:none !important')
        insertion = list(parent).index(original) + 1
        for path in sketch['paths']:
            attrs = {key: value for key, value in original.attrib.items()
                     if key not in {'id','d','x','y','x1','y1','x2','y2','width','height','rx','ry','cx','cy','r','points',
                                    'style','marker-start','marker-end','marker-mid'}}
            attrs['class'] = ' '.join(c for c in attrs.get('class', '').split()
                                      if not c.startswith(('end_marked_', 'start_marked_')))
            attrs.update(d=path, style=style + ';fill:none !important')
            parent.insert(insertion, ET.Element(SVG+'path', attrs))
            insertion += 1
        if sketch['bounds']:
            x1,y1,x2,y2 = sketch['bounds']
            left,top = min(left,x1-stroke_width), min(top,y1-stroke_width)
            right,bottom = max(right,x2+stroke_width), max(bottom,y2+stroke_width)
    left,top,right,bottom = math.floor(left),math.floor(top),math.ceil(right),math.ceil(bottom)
    root.set('viewBox', f'{left} {top} {right-left} {bottom-top}')
    root.set('width', str(right-left))
    root.set('height', str(bottom-top))
