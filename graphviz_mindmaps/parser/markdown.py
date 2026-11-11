"""Isolate Markdown bodies before the legacy outline parser sees their contents."""
import base64
from dataclasses import asdict, dataclass, field, replace
import json
import re

from graphviz_mindmaps.model.document import MarkdownBody
from graphviz_mindmaps.constants import CALLOUT_COLORS
from graphviz_mindmaps.parser.emoticons import MatchEmoticon, ReplaceEmoticons

HEADING = re.compile(r"^(\t*)#(?:[ \t]+|$)(.*)$")
PAYLOAD = re.compile(r'<GVMM_MARKDOWN data="([A-Za-z0-9+/=]+)"/>$')


def _tokens(line):
    return re.findall(r'''(?:[^\s"']|"[^"]*"|'[^']*')+''', line)


def ParseMarkdownTitleColors(attributes):
    """Select titles by document position; later selectors win."""
    colors = []
    for token in _tokens(attributes or ''):
        if not token.startswith('mt'):
            continue
        match = re.fullmatch(r'mt(\d+|\[\d+(?:[,-]\d+)?\])([rgbycpkt])', token)
        if not match:
            raise ValueError(f'invalid Markdown title color {token!r}; use mt[1,5]r or mt[1-3]r')
        selector, color = match.groups()
        bounds = re.split(r'[,-]', selector.strip('[]'))
        start, end = int(bounds[0]), int(bounds[-1])
        if start < 1 or end < 1:
            raise ValueError('Markdown title positions must be positive integers')
        colors.append((range(min(start, end), max(start, end) + 1), color))
    return colors


def DecodeMarkdownBody(title):
    match = PAYLOAD.search(title)
    if not match:
        return title, None
    data = json.loads(base64.b64decode(match.group(1)).decode('utf-8'))
    data['locations'] = [tuple(location) for location in data['locations']]
    return title[:match.start()], MarkdownBody(**data)


def PrepareMarkdownBodies(lines):
    """Return legacy outline lines with bodies carried in an opaque payload.

    Only a heading's attribute line (or a root's attribute group) can select md
    or a standalone mermaid/svgbob body.
    Body text is never tested for directives, fname, or outline headings by the
    downstream parser. Raw whitespace survives in the payload.
    """
    output = []
    i = 0
    while i < len(lines):
        heading = HEADING.match(lines[i])
        if not heading:
            output.append(lines[i].rstrip())
            i += 1
            continue
        j = i + 1
        while j < len(lines):
            following = HEADING.match(lines[j])
            if not following or following.group(1) != heading.group(1):
                break
            j += 1
        indent = heading.group(1) + '\t'
        attr_pattern = re.compile(r'^' + re.escape(indent) + r'[:;|](?:\s|$)')
        if j == len(lines) or not attr_pattern.match(lines[j]):
            output.extend(line.rstrip() for line in lines[i:j])
            i = j
            continue
        root = bool(re.match(r'^\t*[:;|]\s*fname\s*=', lines[j]))
        end = j
        md_index = None
        while end < len(lines) and attr_pattern.match(lines[end]):
            if {'md', 'markdown', 'mermaid', 'svgbob'} & set(_tokens(lines[end])):
                md_index = end
                end += 1
                break
            end += 1
            if not root:
                break
        if md_index is None:
            output.extend(line.rstrip() for line in lines[i:end])
            i = end
            continue
        title = '; '.join(HEADING.match(line).group(2).rstrip() for line in lines[i:j])
        body = MarkdownBody('', getattr(lines[md_index], 'filename', '<input>'), title,
                            getattr(lines[md_index], 'number', md_index + 1))
        body.rawmarkers = 'rawmarkers' in _tokens(lines[md_index])
        body.mermaid = 'mermaid' in _tokens(lines[md_index])
        body.svgbob = 'svgbob' in _tokens(lines[md_index])
        body_modes = set()
        for attr in lines[j:end]:
            for token in _tokens(attr):
                if token in {'md', 'markdown', 'mermaid', 'svgbob'}:
                    body_modes.add('md' if token == 'markdown' else token)
                if token in {'block', 'verbatim', 'verbat', 'draw'} or re.match(r'^code(?:$|[=:])', token):
                    raise body.error('md, mermaid, svgbob, code, block, and draw are mutually exclusive body modes')
                if re.match(r'^(?:E?l|E?w)(?:\d|\[)', token):
                    raise body.error('body line/word selectors are not supported; use hl/h header selectors or Markdown emphasis')
        if len(body_modes) > 1:
            raise body.error('md, mermaid, and svgbob are mutually exclusive body modes')
        source = []
        k = end
        prefix = indent + ':'
        while k < len(lines) and not HEADING.match(lines[k]):
            line = lines[k]
            if line.startswith(prefix):
                payload = line[len(prefix):]
                separator = int(payload.startswith(' '))
                source.append(payload[separator:])
                body.locations.append((getattr(line, 'number', k + 1), len(prefix) + separator + 1))
            elif line.strip():
                number = getattr(line, 'number', k + 1)
                raise ValueError(f"{body.filename}:{number}: Markdown node {title!r}: "
                                 'expected a colon body line at the attribute indentation')
            k += 1
        body.source = '\n'.join(source) + ('\n' if source else '')
        encoded = base64.b64encode(json.dumps(asdict(body), ensure_ascii=False).encode()).decode()
        output.append(heading.group(1) + '# ' + title + f'<GVMM_MARKDOWN data="{encoded}"/>')
        output.extend(line.rstrip() for line in lines[j:end])
        i = k
    return output


@dataclass(frozen=True)
class Run:
    text: str
    bold: bool = False
    italic: bool = False
    strike: bool = False
    code: bool = False
    link: str = ''
    hardbreak: bool = False
    image: str = ''
    highlight: bool = False


@dataclass
class Block:
    kind: str
    runs: list = field(default_factory=list)
    children: list = field(default_factory=list)
    level: int = 0
    start: int = 1
    source_line: int = 0
    source: str = ''
    language: str = ''
    align: str = 'left'
    callout: str = ''
    bullet_marker: str = ''


CONTAINER_COLORS = {
    'note': '#B4E4E3', 'info': '#B4E4E3',
    'tip': '#B8E3B4', 'success': '#B8E3B4',
    'warning': '#F1E6A8', 'danger': '#F2B8B8', 'error': '#F2B8B8',
}


def _container(state, start_line, end_line, silent):
    """Parse colon fences using the current list/quote indentation context."""
    if state.is_code_block(start_line):
        return False

    def text(line):
        return state.src[state.bMarks[line] + state.tShift[line]:state.eMarks[line]]

    opening = re.fullmatch(r'(:{3,})[ \t]*([\w-]+)(?:[ \t]+(.*?))?[ \t]*', text(start_line))
    if not opening:
        return False
    if silent:
        return True
    markup, name, title = opening.groups()
    next_line = start_line + 1
    closed = False
    code_fence = None
    while next_line < end_line:
        line = text(next_line)
        if line and state.sCount[next_line] < state.blkIndent:
            break
        if not state.is_code_block(next_line):
            fence = re.match(r'(`{3,}|~{3,})(.*)$', line)
            if code_fence:
                if (fence and fence[1][0] == code_fence[0]
                        and len(fence[1]) >= len(code_fence) and not fence[2].strip()):
                    code_fence = None
            elif fence and not (fence[1][0] == '`' and '`' in fence[2]):
                code_fence = fence[1]
            elif re.fullmatch(r':{' + str(len(markup)) + r',}[ \t]*', line):
                closed = True
                break
        next_line += 1

    old_parent, old_max = state.parentType, state.lineMax
    state.parentType, state.lineMax = 'container', next_line
    token = state.push('container_open', 'div', 1)
    token.markup = markup
    token.info = name
    token.meta = {'title': title or name.replace('-', ' ').capitalize()}
    token.map = [start_line, next_line + int(closed)]
    try:
        state.md.block.tokenize(state, start_line + 1, next_line)
    finally:
        state.parentType, state.lineMax = old_parent, old_max
    token = state.push('container_close', 'div', -1)
    token.markup = markup
    state.line = next_line + int(closed)
    return True


def _highlight_tokenize(state, silent):
    """Pair exact == delimiters using Markdown's normal flanking rules."""
    if silent or state.src[state.pos] != '=':
        return False
    from markdown_it.rules_inline.state_inline import Delimiter

    scanned = state.scanDelims(state.pos, True)
    token = state.push('text', '', 0)
    token.content = '=' * scanned.length
    if scanned.length == 2:
        state.delimiters.append(Delimiter(
            marker=ord('='), length=0, token=len(state.tokens) - 1,
            end=-1, open=scanned.can_open, close=scanned.can_close))
    state.pos += scanned.length
    return True


def _highlight_postprocess(state):
    groups = [state.delimiters] + [meta['delimiters'] for meta in state.tokens_meta
                                 if meta and 'delimiters' in meta]
    for delimiters in groups:
        for delimiter in delimiters:
            if delimiter.marker != ord('=') or delimiter.end == -1:
                continue
            closing = delimiters[delimiter.end]
            for index, suffix, nesting in ((delimiter.token, 'open', 1),
                                           (closing.token, 'close', -1)):
                token = state.tokens[index]
                token.type = 'mark_' + suffix
                token.tag = 'mark'
                token.nesting = nesting
                token.markup = '=='
                token.content = ''


def ParseMarkdown(body, preserve_newlines=False):
    """CommonMark plus tables, strikethrough and ==marks==, without HTML."""
    from markdown_it import MarkdownIt
    from markdown_it.tree import SyntaxTreeNode

    parser = MarkdownIt('commonmark', {'html': False, 'linkify': False,
                                      'typographer': False, 'breaks': False})
    # Local-file links are useful in mindmaps. Retain the default validation
    # for every other scheme; image URLs are checked separately by the renderer.
    validate_link = parser.validateLink
    parser.validateLink = lambda url: url.lower().startswith('file://') or validate_link(url)
    parser.enable(['strikethrough', 'table'])
    parser.block.ruler.before('fence', 'container', _container,
                              {'alt': ['paragraph', 'reference', 'blockquote', 'list']})
    parser.inline.ruler.before('emphasis', 'highlight', _highlight_tokenize)
    parser.inline.ruler2.before('emphasis', 'highlight', _highlight_postprocess)
    if not body.rawmarkers:
        def emoticon(state, silent):
            match = MatchEmoticon(state.src, state.pos)
            if not match:
                return False
            if not silent:
                token = state.push('text', '', 0)
                token.content = ReplaceEmoticons(match.group(0))
            state.pos = match.end()
            return True
        # Before text consumes letter/number prefixes, and before emphasis can
        # interpret the star in a kiss. Code and link destinations stay opaque.
        parser.inline.ruler.before('text', 'emoticon', emoticon)
    tree = SyntaxTreeNode(parser.parse(body.source, env={}))

    def inline(nodes, style=Run('')):
        result = []
        for node in nodes:
            kind = node.type
            if kind == 'text':
                text = node.content if body.rawmarkers else ReplaceEmoticons(node.content)
                result.append(replace(style, text=text))
            elif kind == 'code_inline':
                result.append(replace(style, text=node.content, code=True))
            elif kind in {'strong', 'em', 's', 'link', 'mark'}:
                changes = {'strong': {'bold': True}, 'em': {'italic': True},
                           'mark': {'highlight': True},
                           's': {'strike': True}, 'link': {'link': node.attrs.get('href', '')}}[kind]
                result.extend(inline(node.children, replace(style, **changes)))
            elif kind == 'softbreak':
                result.append(replace(style, text='' if preserve_newlines else ' ',
                                      hardbreak=preserve_newlines))
            elif kind == 'hardbreak':
                result.append(replace(style, text='', hardbreak=True))
            elif kind == 'image':
                alt = ''.join(run.text for run in inline(node.children))
                result.append(replace(style, text=alt, image=node.attrs.get('src', '')))
            else:
                raise body.error(f'unsupported inline Markdown token: {kind}')
        return result

    def convert(node):
        line = node.map[0] if node.map else 0
        result = Block(node.type, source_line=line)
        if node.type in {'paragraph', 'heading', 'th', 'td'}:
            result.runs = inline([child for item in node.children for child in item.children])
            if node.type == 'heading':
                result.level = int(node.tag[1:])
            if node.type in {'th', 'td'}:
                result.align = node.attrs.get('style', 'text-align:left').split(':')[-1]
        elif node.type == 'container':
            title_tree = SyntaxTreeNode(parser.parseInline(node.meta['title']))
            result.runs = inline(title_tree.children[0].children)
            result.callout = CONTAINER_COLORS.get(node.info.lower(), '#E0E0E0')
            result.children = [convert(child) for child in node.children]
        elif node.type in {'fence', 'code_block'}:
            result.source = node.content
            result.language = node.info.split()[0] if node.info.strip() else 'text'
        elif node.type in {'bullet_list', 'ordered_list', 'list_item', 'blockquote',
                           'table', 'thead', 'tbody', 'tr'}:
            result.children = [convert(child) for child in node.children]
            if node.type == 'ordered_list':
                result.start = int(node.attrs.get('start', 1))
            if node.type == 'bullet_list':
                result.bullet_marker = node.markup
            if (node.type == 'list_item' and node.parent.type == 'bullet_list'
                    and not body.rawmarkers and node.children
                    and node.children[0].type == 'paragraph'):
                paragraph = node.children[0]
                source = paragraph.children[0].content
                marker = re.match(r'^([!?$@])(?=\s|$)', source)
                if marker and result.children[0].runs:
                    first = result.children[0].runs[0]
                    result.children[0].runs[0] = replace(
                        first, text=re.sub(r'^[!?$@][ \t]*', '', first.text, count=1))
                    result.callout = CALLOUT_COLORS[marker.group(1)]
        elif node.type != 'hr':
            raise body.error(f'unsupported Markdown block: {node.type}', line)
        return result

    return [convert(node) for node in tree.children]
