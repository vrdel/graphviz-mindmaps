import hashlib
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.styles import get_style_by_name
from pygments.token import Token
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
    while token_type not in {None, Token}:
        try:
            style_def = style.style_for_token(token_type)
        except KeyError:
            token_type = token_type.parent
            continue
        color = style_def.get("color")
        if color:
            return "#" + color
        token_type = token_type.parent
    try:
        color = style.style_for_token(Token).get("color")
        if color:
            return "#" + color
    except KeyError:
        pass
    return fallback


def ExtractCodeHighlights(attrline):
    """Extract one-based selectors, using negative indices for end-relative lines."""
    selected = set()

    def consume(match):
        end_relative = bool(match.group(1))
        spec = match.group(2).strip("[]")
        for part in spec.split(","):
            bounds = part.split("-")
            start = int(bounds[0])
            end = int(bounds[-1])
            if start < 1 or end < start:
                raise ValueError("invalid code line selector: %s" % match.group(0))
            selected.update(-line if end_relative else line for line in range(start, end + 1))
        return ""

    remaining = re.sub(
        r"(?<!\S)(E?)l([0-9]+|\[[0-9]+(?:-[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?)*\])(?!\S)",
        consume,
        attrline,
    )
    return sorted(selected), remaining


def RenderCodeImage(source, language, tmpdirs, style_name="default", highlight_lines=None):
    highlight_lines = sorted(set(highlight_lines or []))
    tmpdir = Path(tmpdirs[-1]) if tmpdirs else Path.cwd()
    code_dir = tmpdir / "code"
    code_dir.mkdir(parents=True, exist_ok=True)

    try:
        lexer = get_lexer_by_name(language, stripnl=False, ensurenl=False)
    except ClassNotFound:
        lexer = get_lexer_by_name("text", stripnl=False, ensurenl=False)

    try:
        style = get_style_by_name(style_name)
    except ClassNotFound:
        style = get_style_by_name("default")

    font = _load_font(18)
    line_height = max(22, font.getbbox("Mg")[3] - font.getbbox("Mg")[1] + 8)
    padding_x = 16
    padding_y = 14

    lines = source.splitlines() or [""]
    content_rows = [index for index, line in enumerate(lines, start=1) if line.strip()]
    highlighted_rows = set()
    if content_rows:
        first, last = content_rows[0], content_rows[-1]
        for line in highlight_lines:
            row = first + line - 1 if line > 0 else last + line + 1
            if line != 0 and first <= row <= last:
                highlighted_rows.add(row)
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
    for line_number, line_tokens in enumerate(token_lines, start=1):
        if line_number in highlighted_rows:
            draw.rectangle(
                (0, y, width - 1, y + line_height - 1),
                fill=style.highlight_color or "#ffffcc",
            )
        x = padding_x
        for token_type, text in line_tokens:
            fill = _style_color(style, token_type, "#222222")
            draw.text((x, y), text, font=font, fill=fill)
            bbox = font.getbbox(text)
            x += bbox[2] - bbox[0]
        y += line_height

    digest = hashlib.sha256(
        "\0".join([language, source, style_name, repr(highlight_lines)]).encode("utf-8")
    ).hexdigest()[:16]
    output = code_dir / ("code-%s.png" % digest)
    image.save(output)
    return str(output)
