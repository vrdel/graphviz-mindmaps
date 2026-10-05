"""Render structured Markdown into Graphviz's restricted label grammar."""
from dataclasses import replace
from functools import lru_cache
from html import escape
import hashlib
import math
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import unquote, urlparse

from PIL import Image, ImageFont

from graphviz_mindmaps.constants import font, fontcolor
from graphviz_mindmaps.parser.markdown import ParseMarkdown
from graphviz_mindmaps.render.code_image import RenderCodeImage


@lru_cache(maxsize=128)
def _font(face, size, bold, italic):
    # Ask fontconfig for the same family/style Graphviz will resolve.
    pattern = face + (':weight=bold' if bold else '') + (':slant=italic' if italic else '')
    try:
        path = subprocess.run(['fc-match', '-f', '%{file}', pattern],
                              capture_output=True, text=True, check=True).stdout
        return ImageFont.truetype(path, size * 4)
    except (OSError, subprocess.CalledProcessError):
        return ImageFont.truetype('DejaVuSans.ttf', size * 4)


def _measure(text, face, size, bold=False, italic=False):
    metric = _font(face, max(1, round(size)), bold, italic)
    return metric.getlength(text) / 4


def AppendMarkdownLabel(label, body_label):
    """Append a nested table after legacy title formatting has finished."""
    head, closing = label.rsplit('</TABLE>', 1)
    return head + '<TR><TD ALIGN="LEFT" CELLPADDING="6">' + body_label + '</TD></TR></TABLE>' + closing


def RenderMarkdown(body, tmpdirs, width=420, face=None, foreground=None, size=18, code_theme='default'):
    try:
        width = float(width)
    except (TypeError, ValueError):
        raise body.error('md_width must be a positive finite number of points') from None
    if not math.isfinite(width) or width <= 0:
        raise body.error('md_width must be a positive finite number of points')
    face = face or font['comic']
    foreground = foreground or fontcolor['def']
    size = max(1, float(size))
    blocks = ParseMarkdown(body)

    def temporary():
        if not tmpdirs:
            tmpdirs.append(tempfile.mkdtemp(prefix='gvmm-markdown-'))
        return Path(tmpdirs[-1])

    def run_html(run, text, points, bold=False):
        value = escape(text, quote=True).replace('\t', '&#160;' * 4)
        if run.code:
            value = value.replace(' ', '&#160;')
        for enabled, tag in ((run.bold or bold, 'B'), (run.italic, 'I'), (run.strike, 'S')):
            if enabled:
                value = f'<{tag}>{value}</{tag}>'
        color = fontcolor['b'] if run.link else foreground
        family = font['mono'] if run.code else face
        return f'<FONT FACE="{escape(family, quote=True)}" POINT-SIZE="{points:g}" COLOR="{escape(color, quote=True)}">{value}</FONT>'

    def wrapped(runs, available, points, bold=False, align='LEFT'):
        # Preserve styling across adjacent runs within the same word. Split only
        # at ordinary spaces; a nonbreaking space and inline code stay intact.
        groups = []
        word = []
        pending_space = False
        for run in runs:
            if run.hardbreak:
                if word:
                    groups.append(('word', word))
                    word = []
                groups.append(('break', []))
                pending_space = False
                continue
            if run.image:
                raise body.error('images must occupy their own paragraph')
            pieces = [run.text] if run.code else re.findall(r'[ \t\r\n]+|[^ \t\r\n]+', run.text)
            for piece in pieces:
                if not run.code and piece.isspace():
                    if word:
                        groups.append(('word', word))
                        word = []
                    pending_space = True
                else:
                    if pending_space:
                        groups.append(('space', [replace(run, text=' ')]))
                        pending_space = False
                    word.append(replace(run, text=piece))
        if word:
            groups.append(('word', word))
        rows, row, used, space = [], '', 0.0, False
        for kind, parts in groups:
            if kind == 'break':
                rows.append(row or '&#160;')
                row, used, space = '', 0.0, False
            elif kind == 'space':
                space = bool(row)
            else:
                length = sum(_measure(r.text, font['mono'] if r.code else face, points,
                                      r.bold or bold, r.italic) for r in parts)
                gap = _measure(' ', face, points) if space else 0
                # A little slack accounts for differences in Graphviz/Pillow metrics.
                if row and used + gap + length > available * .94:
                    rows.append(row)
                    row, used, space = '', 0.0, False
                    gap = 0
                if space:
                    row += ' '
                row += ''.join(run_html(r, r.text, points, bold) for r in parts)
                used += gap + length
                space = False
        if row or not rows:
            rows.append(row or '&#160;')
        # Graphviz aligns the line *preceding* BR, including the final line.
        return ''.join(row + f'<BR ALIGN="{align}"/>' for row in rows)

    def table(rows, border=0):
        return f'<TABLE BORDER="{border}" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3" ALIGN="LEFT">' + ''.join(rows) + '</TABLE>'

    def textrow(value):
        return '<TR><TD ALIGN="LEFT">' + value + '</TD></TR>'

    def image(path, available, line):
        try:
            with Image.open(path) as img:
                img.load()
                if img.width > available or img.height > 900:
                    img.thumbnail((max(1, int(available)), 900))
                    # Copy into the session: never resize an author's source image.
                    key = hashlib.sha256((str(path) + str(available)).encode()).hexdigest()[:16]
                    target = temporary() / ('md-image-' + key + '.png')
                    img.save(target)
                    path = target
        except (OSError, ValueError) as exc:
            raise body.error(f'cannot read image {path}: {exc}', line) from exc
        return '<IMG SRC="%s"/>' % escape(str(path), quote=True)

    def render(items, available):
        rows = []
        for block in items:
            kind = block.kind
            if kind == 'heading':
                gap = max(4, round(size * 0.5))
                rows.append(f'<TR><TD HEIGHT="{gap}" CELLPADDING="0"><FONT POINT-SIZE="1">&#160;</FONT></TD></TR>')
            if kind in {'paragraph', 'heading'}:
                images = [r for r in block.runs if r.image]
                if images:
                    if len(images) != 1 or any(r.text.strip() for r in block.runs if not r.image):
                        raise body.error('images must occupy their own paragraph', block.source_line)
                    url = urlparse(images[0].image)
                    if url.scheme or url.netloc:
                        raise body.error('only local Markdown images are supported; remote images are not downloaded', block.source_line)
                    path = Path(unquote(url.path)).expanduser()
                    if not path.is_absolute():
                        base = Path(body.filename).resolve().parent if not body.filename.startswith('<') else Path.cwd()
                        path = base / path
                    rows.append('<TR><TD ALIGN="LEFT" CELLPADDING="0">' + image(path, available, block.source_line) + '</TD></TR>')
                else:
                    ratio = (1.65, 1.4, 1.2, 1.1, 1.0, 1.0)[block.level - 1] if kind == 'heading' else 1
                    rows.append(textrow(wrapped(block.runs, available, round(size * ratio), kind == 'heading')))
            elif kind == 'hr':
                # A separate tiny table guarantees legal HR placement even at EOF.
                rows.append(textrow('<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0"><TR><TD HEIGHT="1"> </TD></TR><HR/><TR><TD HEIGHT="1"> </TD></TR></TABLE>'))
            elif kind in {'fence', 'code_block'}:
                temporary()
                path = RenderCodeImage(block.source.expandtabs(4), block.language, tmpdirs, code_theme)
                rows.append('<TR><TD ALIGN="LEFT" CELLPADDING="0">' + image(Path(path), available, block.source_line) + '</TD></TR>')
            elif kind == 'blockquote':
                inner = render(block.children, max(1, available - 22))
                accent = escape(fontcolor['b'], quote=True)
                rows.append(textrow(f'<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" ALIGN="LEFT"><TR><TD BORDER="3" SIDES="L" COLOR="{accent}" CELLPADDING="8" ALIGN="LEFT">{inner}</TD></TR></TABLE>'))
            elif kind in {'bullet_list', 'ordered_list'}:
                listrows = []
                markers = [f'{block.start + index}.' if kind == 'ordered_list' else '•'
                           for index in range(len(block.children))]
                marker_width = max([_measure(m, face, size) for m in markers] + [size]) + 2
                for index, item in enumerate(block.children):
                    children = list(item.children)
                    marker = markers[index]
                    if children and children[0].kind == 'paragraph' and children[0].runs:
                        first = children[0].runs[0]
                        task = re.match(r'^\[([ xX])\][ \t]+', first.text)
                        if task and kind == 'bullet_list' and not any((first.code, first.bold, first.italic, first.strike, first.link)):
                            marker = '☑' if task.group(1).lower() == 'x' else '☐'
                            children[0] = replace(children[0], runs=[replace(first, text=first.text[task.end():])] + children[0].runs[1:])
                    content = render(children, max(1, available - marker_width - 6))
                    content_width = max(1, math.ceil(available - marker_width - 6))
                    listrows.append(f'<TR><TD VALIGN="TOP" ALIGN="RIGHT" WIDTH="{math.ceil(marker_width)}">{escape(marker)}</TD><TD ALIGN="LEFT" CELLPADDING="0" WIDTH="{content_width}">{content}</TD></TR>')
                rows.append(textrow(table(listrows)))
            elif kind == 'table':
                matrix = [row for section in block.children for row in section.children]
                columns = max((len(row.children) for row in matrix), default=1)
                column_width = max(1, (available - 12 * columns) / columns)
                tablerows = []
                for row in matrix:
                    cells = []
                    for cell in row.children:
                        alignment = cell.align.upper() if cell.align in {'left', 'right', 'center'} else 'LEFT'
                        content = wrapped(cell.runs, column_width, size, cell.kind == 'th', alignment)
                        cells.append(f'<TD ALIGN="{alignment}">{content}</TD>')
                    tablerows.append('<TR>' + ''.join(cells) + '</TR>')
                border = escape(foreground, quote=True)
                rows.append(textrow(f'<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="5" COLOR="{border}">' + ''.join(tablerows) + '</TABLE>'))
            else:
                raise body.error(f'unsupported layout block: {kind}', block.source_line)
        if not rows:
            rows.append(textrow('&#160;'))
        return table(rows)

    # Inherit explicit node defaults for markers as well as prose runs.
    return '<FONT FACE="%s" POINT-SIZE="%g" COLOR="%s">%s</FONT>' % (
        escape(face, quote=True), size, escape(foreground, quote=True), render(blocks, width))
