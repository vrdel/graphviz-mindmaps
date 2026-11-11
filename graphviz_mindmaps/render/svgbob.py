"""Render ASCII diagrams with the optional Svgbob CLI and librsvg."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from xml.etree import ElementTree

from PIL import Image

from graphviz_mindmaps.constants import font
from graphviz_mindmaps.render.diagram_colors import DiagramColorTokens
from graphviz_mindmaps.render.svgbob_styles import StyleSvgbobSvg


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


def RenderSvgbobImage(source, tmpdir, foreground='#000000', stroke_width=2):
    stroke_width = ParseSvgbobStrokeWidth(stroke_width)
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
                              'stroke_width': stroke_width,
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
            svgfile.write_text(StyleSvgbobSvg(root, color_tokens), encoding='utf-8')
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
