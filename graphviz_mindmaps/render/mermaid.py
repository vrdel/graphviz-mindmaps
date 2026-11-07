"""Render Mermaid fences with Pele and rasterize their SVG for Graphviz."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from xml.etree import ElementTree

from PIL import Image


def _static_svg(svg, colors=None):
    """Materialize Pele's CSS variables for SVG rasterizers without var()."""
    variable = re.compile(r'var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*))?\)')

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
            element.set('style', ';'.join(key + ':' + expand(value, variables)
                                         for key, value in declarations
                                         if not key.strip().startswith('--')))
        for key, value in list(element.attrib.items()):
            if key != 'style':
                element.set(key, expand(value, variables))
        for child in element:
            visit(child, variables)

    try:
        root = ElementTree.fromstring(svg)
    except ElementTree.ParseError as exc:
        raise ValueError(f'Pele returned invalid SVG: {exc}') from exc
    visit(root, colors or {})
    return ElementTree.tostring(root, encoding='unicode')


def RenderMermaidImage(source, tmpdir, width=420, colors=None):
    node = shutil.which('node')
    rasterizer = shutil.which('rsvg-convert')
    if not node:
        raise ValueError('Pele rendering requires Node.js 20 or newer on PATH')
    if not rasterizer:
        raise ValueError('Pele rendering requires rsvg-convert on PATH (librsvg2-bin)')
    payload = json.dumps({'source': source, 'width': width, 'colors': colors or {}},
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
        svgfile.write_text(_static_svg(result.stdout, colors), encoding='utf-8')
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
