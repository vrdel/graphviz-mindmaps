"""Typeset TeX equations through local MathJax SVG output for Graphviz."""
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
from xml.etree import ElementTree

from PIL import Image


HELPER = Path(__file__).with_name('mathjax.mjs')
MATH_PIXELS_PER_POINT = 96 / 72


def RenderMathImage(source, tmpdir, size=18, color='#000000', display=False):
    try:
        size = float(size)
    except (TypeError, ValueError, OverflowError):
        raise ValueError('math font size must be positive and finite') from None
    if not math.isfinite(size) or size <= 0:
        raise ValueError('math font size must be positive and finite')
    node, rasterizer = shutil.which('node'), shutil.which('rsvg-convert')
    if not node:
        raise ValueError('math rendering requires Node.js on PATH and MathJax; run npm ci')
    if not rasterizer:
        raise ValueError('math rendering requires rsvg-convert on PATH (librsvg2-bin)')
    payload = json.dumps({'source': source, 'size': size, 'color': color, 'display': bool(display),
                          'mathjax': '4.1.3', 'helper': hashlib.sha256(HELPER.read_bytes()).hexdigest()},
                         sort_keys=True, ensure_ascii=False)
    key = hashlib.sha256(payload.encode()).hexdigest()[:20]
    directory = Path(tmpdir) / 'math'
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / (key + '.png')
    if output.exists():
        return output
    svgfile = output.with_suffix('.svg')
    pending = directory / (key + '.rendering.png')
    try:
        result = subprocess.run([node, str(HELPER)], input=payload, capture_output=True,
                                text=True, timeout=30)
        if result.returncode:
            raise ValueError('MathJax rendering failed: ' + (result.stderr.strip() or f'node exited {result.returncode}'))
        try:
            svg = ElementTree.fromstring(result.stdout)
        except ElementTree.ParseError as exc:
            raise ValueError(f'MathJax returned invalid SVG: {exc}') from exc
        if svg.tag != '{http://www.w3.org/2000/svg}svg':
            raise ValueError('MathJax returned invalid SVG: missing SVG root')
        svgfile.write_text(result.stdout, encoding='utf-8')
        result = subprocess.run([rasterizer, '-o', str(pending), str(svgfile)],
                                capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise ValueError('MathJax SVG conversion failed: ' + (result.stderr.strip() or f'rsvg-convert exited {result.returncode}'))
        with Image.open(pending) as image:
            image.verify()
        pending.replace(output)
    except subprocess.TimeoutExpired as exc:
        raise ValueError('MathJax rendering or SVG conversion timed out after 30 seconds') from exc
    except OSError as exc:
        raise ValueError(f'cannot render math equation: {exc}') from exc
    finally:
        pending.unlink(missing_ok=True)
    return output
