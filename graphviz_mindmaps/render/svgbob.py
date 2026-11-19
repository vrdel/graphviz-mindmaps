"""Render ASCII diagrams with the optional Svgbob CLI and librsvg."""
from functools import lru_cache
import hashlib
import json
import math
import os
import re
from pathlib import Path
import shutil
import subprocess
from xml.etree import ElementTree

from PIL import Image, ImageColor, ImageFont

from graphviz_mindmaps.constants import font
from graphviz_mindmaps.render.diagram_colors import DiagramColorTokens, ResolveDiagramColor
from graphviz_mindmaps.render.svgbob_styles import StyleSvgbobSvg
from graphviz_mindmaps.render.svgbob_shapes import RecoverSvgbobRectangles, RecoverSvgbobRoundedRectangles


@lru_cache(maxsize=64)
def _text_font(family, size):
    try:
        path = subprocess.run(['fc-match', '-f', '%{file}', family],
                              capture_output=True, text=True, check=True, timeout=5).stdout.strip()
        return ImageFont.truetype(path, size)
    except (OSError, subprocess.SubprocessError):
        return ImageFont.truetype('DejaVuSansMono.ttf', size)


def ExpandSvgbobTextBounds(root, family, size):
    """Include quoted labels omitted from Svgbob's geometry-based viewport."""
    width, height = float(root.get('width')), float(root.get('height'))
    right, bottom = width, height
    metric = None
    for element in root.iter('{http://www.w3.org/2000/svg}text'):
        text = ''.join(element.itertext()).rstrip()
        if not text:
            continue
        if metric is None:
            metric = _text_font(family, size)
        bounds = metric.getbbox(text, anchor='ls')
        right = max(right, float(element.get('x', 0)) + bounds[2] + 2)
        bottom = max(bottom, float(element.get('y', 0)) + bounds[3] + 2)
    if right > width:
        root.set('width', str(math.ceil(right)))
    if bottom > height:
        root.set('height', str(math.ceil(bottom)))
    for rect in root.findall('{http://www.w3.org/2000/svg}rect'):
        if 'backdrop' in rect.get('class', '').split():
            rect.set('width', root.get('width'))
            rect.set('height', root.get('height'))


def FindSvgbob():
    for root in (Path(__file__).resolve().parents[2], Path.cwd()):
        for name in ('svgbob_cli', 'svgbob'):
            executable = root / '.tools' / 'svgbob' / 'bin' / name
            if executable.is_file() and os.access(executable, os.X_OK):
                return str(executable)
    for name in ('svgbob', 'svgbob_cli'):
        executable = shutil.which(name)
        if executable:
            return executable
    return None


def ParseSvgbobStrokeWidth(value):
    try:
        width = 2.0 if value is None else float(value)
    except (TypeError, ValueError):
        raise ValueError('svgbob_stroke_width must be a nonnegative finite number') from None
    if not math.isfinite(width) or width < 0:
        raise ValueError('svgbob_stroke_width must be a nonnegative finite number')
    return width


def ParseSvgbobFontSize(value):
    try:
        size = 14.0 if value is None else float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError('svgbob_font_size must be a positive integer') from None
    if not math.isfinite(size) or size < 1 or not size.is_integer():
        raise ValueError('svgbob_font_size must be a positive integer')
    return int(size)


def ParseSvgbobFill(value):
    if value is None:
        return None
    value = str(value).strip()
    tokens = DiagramColorTokens()
    try:
        if re.match(r'(?:linear|radial)-gradient\b', value, re.I):
            root = ElementTree.Element('{http://www.w3.org/2000/svg}svg')
            ElementTree.SubElement(root, '{http://www.w3.org/2000/svg}rect', fill=value)
            StyleSvgbobSvg(root, tokens)
        else:
            color = ResolveDiagramColor(value, tokens)
            if color.lower() not in {'none', 'transparent'}:
                ImageColor.getcolor(color, 'RGBA')
    except (ValueError, TypeError) as exc:
        raise ValueError(f'svgbob_fill must be a valid color, mindmap color token, or gradient: {value!r}') from exc
    return value


def RenderSvgbobImage(source, tmpdir, foreground='#000000', stroke_width=2, font_size=14, fill=None):
    stroke_width = ParseSvgbobStrokeWidth(stroke_width)
    font_size = ParseSvgbobFontSize(font_size)
    fill = ParseSvgbobFill(fill)
    executable = FindSvgbob()
    rasterizer = shutil.which('rsvg-convert')
    if not executable:
        raise ValueError('Svgbob is not installed; run python3 tools/install_svgbob.py '
                         'in the repository or install svgbob_cli on PATH')
    if not rasterizer:
        raise ValueError('Svgbob rendering requires rsvg-convert on PATH (librsvg2-bin)')
    try:
        stamp = Path(executable).stat()
        color_tokens = DiagramColorTokens()
        payload = json.dumps({'source': source, 'foreground': foreground, 'font': font['mono'],
                              'render_version': 5,
                              'fill': fill,
                              'stroke_width': stroke_width,
                              'font_size': font_size,
                              'color_tokens': color_tokens,
                              'executable': executable, 'mtime': stamp.st_mtime_ns,
                              'size': stamp.st_size}, sort_keys=True, ensure_ascii=False)
        key = hashlib.sha256(payload.encode()).hexdigest()[:20]
        directory = Path(tmpdir) / 'svgbob'
        directory.mkdir(parents=True, exist_ok=True)
        output = directory / (key + '.png')
        if output.exists():
            return output
        svgfile = directory / (key + '.svg')
        pending = directory / (key + '.rendering.png')
        try:
            result = subprocess.run([
                executable, '--background', 'transparent', '--font-family', font['mono'],
                '--stroke-color', foreground, '--fill-color', foreground,
                '--stroke-width', str(stroke_width),
                '--font-size', str(font_size), '--scale', str(font_size / 14),
            ], input=source, text=True, capture_output=True, timeout=30)
            if result.returncode:
                raise ValueError('Svgbob rendering failed: ' + (result.stderr.strip() or
                                 f'exited {result.returncode}'))
            try:
                root = ElementTree.fromstring(result.stdout)
            except ElementTree.ParseError as exc:
                raise ValueError(f'Svgbob returned invalid SVG: {exc}') from exc
            if root.tag != '{http://www.w3.org/2000/svg}svg':
                raise ValueError('Svgbob returned invalid SVG: missing SVG root')
            RecoverSvgbobRectangles(root, all_rectangles=fill is not None)
            RecoverSvgbobRoundedRectangles(root, all_rectangles=fill is not None)
            ExpandSvgbobTextBounds(root, font['mono'], font_size)
            svgfile.write_text(StyleSvgbobSvg(root, color_tokens, default_fill=fill), encoding='utf-8')
            result = subprocess.run([rasterizer, '-o', str(pending), str(svgfile)],
                                    text=True, capture_output=True, timeout=30)
            if result.returncode:
                raise ValueError('Svgbob SVG conversion failed: ' + (result.stderr.strip() or
                                 f'exited {result.returncode}'))
            with Image.open(pending) as image:
                image.verify()
            pending.replace(output)
        finally:
            pending.unlink(missing_ok=True)
    except subprocess.TimeoutExpired as exc:
        raise ValueError('Svgbob rendering or SVG conversion timed out after 30 seconds') from exc
    except OSError as exc:
        raise ValueError(f'cannot render Svgbob diagram: {exc}') from exc
    return output
