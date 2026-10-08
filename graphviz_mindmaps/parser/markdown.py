"""Isolate Markdown bodies before the legacy outline parser sees their contents."""
import base64
from dataclasses import asdict, dataclass, field, replace
import json
import re

from graphviz_mindmaps.model.document import MarkdownBody

HEADING = re.compile(r"^(\t*)#(?:[ \t]+|$)(.*)$")
PAYLOAD = re.compile(r'<GVMM_MARKDOWN data="([A-Za-z0-9+/=]+)"/>$')


def _tokens(line):
    return re.findall(r'''(?:[^\s"']|"[^"]*"|'[^']*')+''', line)


def DecodeMarkdownBody(title):
    match = PAYLOAD.search(title)
    if not match:
        return title, None
    data = json.loads(base64.b64decode(match.group(1)).decode('utf-8'))
    data['locations'] = [tuple(location) for location in data['locations']]
    return title[:match.start()], MarkdownBody(**data)


def PrepareMarkdownBodies(lines):
    """Return legacy outline lines with bodies carried in an opaque payload.

    Only a heading's attribute line (or a root's attribute group) can select md.
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
            if {'md', 'markdown'} & set(_tokens(lines[end])):
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
        for attr in lines[j:end]:
            for token in _tokens(attr):
                if token in {'block', 'verbatim', 'verbat', 'draw'} or re.match(r'^code(?:$|[=:])', token):
                    raise body.error('md, code, block, and draw are mutually exclusive body modes')
                if re.match(r'^(?:E?l|E?w)(?:\d|\[)', token):
                    raise body.error('body line/word selectors are not supported; use hl/h header selectors or Markdown emphasis')
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


def ParseMarkdown(body):
    """CommonMark plus tables, strikethrough and ==marks==, without HTML."""
    from markdown_it import MarkdownIt
    from markdown_it.tree import SyntaxTreeNode

    parser = MarkdownIt('commonmark', {'html': False, 'linkify': False,
                                      'typographer': False, 'breaks': False})
    parser.enable(['strikethrough', 'table'])
    parser.inline.ruler.before('emphasis', 'highlight', _highlight_tokenize)
    parser.inline.ruler2.before('emphasis', 'highlight', _highlight_postprocess)
    tree = SyntaxTreeNode(parser.parse(body.source, env={}))

    def inline(nodes, style=Run('')):
        result = []
        for node in nodes:
            kind = node.type
            if kind == 'text':
                result.append(replace(style, text=node.content))
            elif kind == 'code_inline':
                result.append(replace(style, text=node.content, code=True))
            elif kind in {'strong', 'em', 's', 'link', 'mark'}:
                changes = {'strong': {'bold': True}, 'em': {'italic': True},
                           'mark': {'highlight': True},
                           's': {'strike': True}, 'link': {'link': node.attrs.get('href', '')}}[kind]
                result.extend(inline(node.children, replace(style, **changes)))
            elif kind == 'softbreak':
                result.append(replace(style, text=' '))
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
        elif node.type in {'fence', 'code_block'}:
            result.source = node.content
            result.language = node.info.split()[0] if node.info.strip() else 'text'
        elif node.type in {'bullet_list', 'ordered_list', 'list_item', 'blockquote',
                           'table', 'thead', 'tbody', 'tr'}:
            result.children = [convert(child) for child in node.children]
            if node.type == 'ordered_list':
                result.start = int(node.attrs.get('start', 1))
        elif node.type != 'hr':
            raise body.error(f'unsupported Markdown block: {node.type}', line)
        return result

    return [convert(node) for node in tree.children]
