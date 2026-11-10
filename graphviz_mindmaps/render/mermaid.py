"""Render Mermaid fences with Pele and rasterize their SVG for Graphviz."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from xml.etree import ElementTree

from PIL import Image

from graphviz_mindmaps.constants import nodetype, vrbtcolors
from graphviz_mindmaps.parser.attributes import NormalizeColorToken


def _diagram_color_tokens():
    """Use block fills, with regular-node fills for tokens blocks lack."""
    tokens = {}
    for name, attrs in nodetype.items():
        if re.fullmatch(r'c[a-z]+', name):
            fill = re.search(r'fillcolor="(#[0-9a-fA-F]{6}|transparent)"', attrs)
            if fill:
                tokens[name] = fill.group(1)
    tokens.update((name, value) for name, value in vrbtcolors.items()
                  if re.fullmatch(r'c[a-z]+', name))
    return tokens


def _static_svg(svg, colors=None, color_tokens=None):
    """Materialize Pele's CSS variables for SVG rasterizers without var()."""
    variable = re.compile(r'var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*))?\)')
    color_tokens = _diagram_color_tokens() if color_tokens is None else color_tokens
    color_properties = {'fill', 'stroke', 'color', 'stop-color', 'flood-color', 'lighting-color'}

    def resolve_color(key, value):
        if key.strip().lower() not in color_properties:
            return value
        match = re.fullmatch(r'\s*(c[a-z]+(?:-?\d+)?)(\s*!important)?\s*', value)
        if not match:
            return value
        token = NormalizeColorToken(match.group(1))
        shade = re.fullmatch(r'(c[a-z]+)(-?\d+)?', token)
        base, delta = shade.groups()
        resolved = color_tokens.get(base)
        if resolved is None:
            return value
        if delta:
            if not re.fullmatch(r'#[0-9a-fA-F]{6}', resolved):
                return value
            resolved = '#' + ''.join('%02x' % min(255, max(0, int(resolved[i:i + 2], 16) + int(delta)))
                                     for i in (1, 3, 5))
        return resolved + (match.group(2) or '')

    def expand(value, variables, seen=()):
        def substitute(match):
            name, fallback = match.groups()
            if name in seen:
                raise ValueError(f'cyclic Pele SVG variable: {name}')
            replacement = variables.get(name, fallback)
            if replacement is None:
                raise ValueError(f'undefined Pele SVG variable: {name}')
            return expand(replacement, variables, seen + (name,))
        while variable.search(value):
            value = variable.sub(substitute, value)
        return value

    def visit(element, inherited):
        declarations = [part.split(':', 1) for part in element.get('style', '').split(';')
                        if ':' in part]
        variables = dict(inherited)
        variables.update((key.strip(), value.strip()) for key, value in declarations
                         if key.strip().startswith('--'))
        if declarations:
            element.set('style', ';'.join(key + ':' + resolve_color(key, expand(value, variables))
                                         for key, value in declarations
                                         if not key.strip().startswith('--')))
        for key, value in list(element.attrib.items()):
            if key != 'style':
                element.set(key, resolve_color(key, expand(value, variables)))
        for child in element:
            visit(child, variables)

    try:
        root = ElementTree.fromstring(svg)
    except ElementTree.ParseError as exc:
        raise ValueError(f'Pele returned invalid SVG: {exc}') from exc
    visit(root, colors or {})
    return ElementTree.tostring(root, encoding='unicode')


def RenderMermaidImage(source, tmpdir, width=420, colors=None, face=None, size=None):
    """Use width=None for a natural-size diagram without a layout width limit."""
    node = shutil.which('node')
    rasterizer = shutil.which('rsvg-convert')
    if not node:
        raise ValueError('Pele rendering requires Node.js 20 or newer on PATH')
    if not rasterizer:
        raise ValueError('Pele rendering requires rsvg-convert on PATH (librsvg2-bin)')
    color_tokens = _diagram_color_tokens()
    payload = json.dumps({'source': source, 'width': width, 'colors': colors or {},
                          'color_tokens': color_tokens,
                          'face': face, 'size': float(size) if size is not None else None},
                         ensure_ascii=False, sort_keys=True)
    key = hashlib.sha256(payload.encode()).hexdigest()[:20]
    directory = Path(tmpdir) / 'mermaid'
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / (key + '.png')
    if output.exists():
        return output
    svgfile = directory / (key + '.svg')
    pending = directory / (key + '.rendering.png')
    try:
        result = subprocess.run([node, str(Path(__file__).with_name('pele.mjs'))],
                                input=payload, capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise ValueError('Pele rendering failed: ' + (result.stderr.strip() or
                             f'node exited {result.returncode}'))
        svgfile.write_text(_static_svg(result.stdout, colors, color_tokens), encoding='utf-8')
        result = subprocess.run([rasterizer, '-o', str(pending), str(svgfile)],
                                capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise ValueError('Pele SVG conversion failed: ' + (result.stderr.strip() or
                             f'rsvg-convert exited {result.returncode}'))
        with Image.open(pending) as image:
            image.verify()
        pending.replace(output)
    except subprocess.TimeoutExpired as exc:
        raise ValueError('Pele rendering or SVG conversion timed out after 30 seconds') from exc
    except OSError as exc:
        raise ValueError(f'cannot render Mermaid diagram: {exc}') from exc
    finally:
        pending.unlink(missing_ok=True)
    return output
