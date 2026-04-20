import re


def ResolveColorNodeTypeToken(token, nodetype):
    if token in nodetype:
        return token

    aliases = {"nodes": "node"}
    match = re.match(
        r"^(c(?:green|cyan|blue|pink|red|yello|orang|black|grey)|impor|impog|impob|quest|commen|check|todo|title|node|nodes)(-?[0-9]+)$",
        token,
    )
    if not match:
        return None

    base = aliases.get(match.group(1), match.group(1))
    if base not in nodetype:
        return None

    delta = int(match.group(2))
    fill_match = re.search(r'fillcolor="(#?[0-9A-Fa-f]{6})"', nodetype[base])
    if not fill_match:
        return None

    rgb = fill_match.group(1).lstrip("#")
    channels = [int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)]
    shifted = [min(255, max(0, channel + delta)) for channel in channels]
    newfill = "#%02x%02x%02x" % (shifted[0], shifted[1], shifted[2])

    nodetype[token] = nodetype[base].replace(fill_match.group(1), newfill, 1)
    return token


def ResolveVerbatimFillColorToken(token, vrbtcolors):
    if token in vrbtcolors:
        return vrbtcolors[token]

    match = re.match(
        r"^(c(?:green|cyan|blue|pink|red|yello|orang|white))(-?[0-9]+)$",
        token,
    )
    if not match:
        return None

    base = match.group(1)
    if base not in vrbtcolors:
        return None

    delta = int(match.group(2))
    rgb = vrbtcolors[base].lstrip("#")
    channels = [int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)]
    shifted = [min(255, max(0, channel + delta)) for channel in channels]
    newfill = "#%02x%02x%02x" % (shifted[0], shifted[1], shifted[2])

    vrbtcolors[token] = newfill
    return newfill


def ResolveBaseNodeTypeToken(token):
    match = re.match(r"^(impor|impog|impob|quest|date|title|link|saying)(-?[0-9]+)$", token)
    if match:
        return match.group(1)
    return token


def ResolveSymbolNames(spec, symbol_map):
    aliases = {
        "info": "info-circle",
        "quest": "question-circle",
        "warn": "warning",
    }

    resolved = []
    for name in spec.split(':'):
        name = name.strip()
        if not name:
            continue
        if name in symbol_map:
            resolved.append(name)
            continue
        aliased = aliases.get(name)
        if aliased and aliased in symbol_map:
            resolved.append(aliased)
    return resolved
