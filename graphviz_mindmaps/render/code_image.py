import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.styles import get_style_by_name
from pygments.util import ClassNotFound


def _load_font(size):
    for name in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf",
    ):
        path = Path(name)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _style_color(style, token_type, fallback):
    while token_type is not None:
        style_def = style.style_for_token(token_type)
        color = style_def.get("color")
        if color:
            return "#" + color
        token_type = token_type.parent
    return fallback


def RenderCodeImage(source, language, tmpdirs, style_name="default"):
    tmpdir = Path(tmpdirs[-1]) if tmpdirs else Path.cwd()
    code_dir = tmpdir / "code"
    code_dir.mkdir(parents=True, exist_ok=True)

    try:
        lexer = get_lexer_by_name(language)
    except ClassNotFound:
        lexer = get_lexer_by_name("text")

    try:
        style = get_style_by_name(style_name)
    except ClassNotFound:
        style = get_style_by_name("default")

    font = _load_font(18)
    line_height = max(22, font.getbbox("Mg")[3] - font.getbbox("Mg")[1] + 8)
    padding_x = 16
    padding_y = 14

    lines = source.splitlines() or [""]
    token_lines = [[]]
    for token_type, value in lex(source, lexer):
        parts = value.split("\n")
        for index, part in enumerate(parts):
            if part:
                token_lines[-1].append((token_type, part))
            if index < len(parts) - 1:
                token_lines.append([])
    while len(token_lines) < len(lines):
        token_lines.append([])

    max_width = 1
    for line_tokens in token_lines:
        x = 0
        for _, text in line_tokens:
            bbox = font.getbbox(text)
            x += bbox[2] - bbox[0]
        max_width = max(max_width, x)

    width = max_width + padding_x * 2
    height = padding_y * 2 + line_height * len(token_lines)

    background = "#f8f8f8"
    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)

    y = padding_y
    for line_tokens in token_lines:
        x = padding_x
        for token_type, text in line_tokens:
            fill = _style_color(style, token_type, "#222222")
            draw.text((x, y), text, font=font, fill=fill)
            bbox = font.getbbox(text)
            x += bbox[2] - bbox[0]
        y += line_height

    digest = hashlib.sha256(
        "\0".join([language, source, style_name]).encode("utf-8")
    ).hexdigest()[:16]
    output = code_dir / ("code-%s.png" % digest)
    image.save(output)
    return str(output)
