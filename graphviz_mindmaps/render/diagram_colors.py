"""Mindmap palette tokens shared by diagram renderers."""
import re

from graphviz_mindmaps.constants import nodetype, vrbtcolors
from graphviz_mindmaps.parser.attributes import NormalizeColorToken


def DiagramColorTokens():
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


def ResolveDiagramColor(value, color_tokens):
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
