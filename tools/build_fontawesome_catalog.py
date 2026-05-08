#!/usr/bin/env python3

import argparse
import html
import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "graphviz_mindmaps" / "fontawesome.py"
DEFAULT_OUTPUT = ROOT / "fontawesome-codes.html"
DEFAULT_FONT = "graphviz_mindmaps/assets/fontawesome/FontAwesome.otf"


def parse_items(source: pathlib.Path) -> list[tuple[str, int, str]]:
    text = source.read_text()
    matches = re.findall(r"\s*'([^']+)':\s*\"&#(?:x)?([0-9a-fA-F]+);\",", text)
    items = [(name, *parse_code(raw)) for name, raw in matches]
    return sorted(items, key=lambda item: item[0].lower())


def parse_code(raw: str) -> tuple[int, str]:
    if raw.lower().startswith("f") or any(char in raw.lower() for char in "abcdef"):
        return int(raw, 16), "0x%s" % raw.lower()
    return int(raw, 10), raw


def render_rows(items: list[tuple[str, int, str]]) -> str:
    rows = []
    for name, codepoint, display_code in items:
        icon_class = "icon fallback" if name == "smile" else "icon"
        rows.append(
            '      <tr><td class="%s"><span>&#x%x;</span></td>'
            '<td class="name">%s</td><td class="code">%s</td>'
            '<td class="entity">&amp;#x%x;</td></tr>'
            % (
                icon_class,
                codepoint,
                html.escape(name),
                html.escape(display_code),
                codepoint,
            )
        )
    return "\n".join(rows)


def render_html(items: list[tuple[str, int, str]], font_path: str) -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Font Awesome Codes</title>
  <style>
    @font-face {
      font-family: "FontAwesomeLocal";
      src: url("%s") format("opentype");
      font-weight: normal;
      font-style: normal;
    }
    :root {
      color-scheme: light dark;
      --bg: #f6f6f4;
      --fg: #202020;
      --muted: #666;
      --panel: #ffffff;
      --line: #d8d8d2;
      --icon: #1e6f7a;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --bg: #202124;
        --fg: #eeeeec;
        --muted: #b3b3ad;
        --panel: #292a2d;
        --line: #45464a;
        --icon: #8ad5df;
      }
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--fg);
      font-family: DejaVu Sans, Arial, sans-serif;
      font-size: 15px;
      line-height: 1.45;
    }
    main {
      max-width: 1180px;
      margin: 0 auto;
      padding: 28px 18px 40px;
    }
    h1 {
      margin: 0 0 6px;
      font-size: 28px;
      line-height: 1.15;
    }
    .meta {
      margin: 0 0 18px;
      color: var(--muted);
    }
    table {
      width: 100%%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
    }
    th, td {
      padding: 8px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: middle;
    }
    th {
      position: sticky;
      top: 0;
      z-index: 1;
      background: var(--panel);
      color: var(--muted);
      font-weight: 700;
    }
    tr:last-child td { border-bottom: 0; }
    .icon {
      width: 58px;
      text-align: center;
    }
    .icon span {
      color: var(--icon);
      font-family: "FontAwesomeLocal";
      font-size: 24px;
      line-height: 1;
    }
    .icon.fallback span {
      font-family: DejaVu Sans, Arial, sans-serif;
    }
    .name { font-weight: 600; }
    .code, .entity {
      font-family: DejaVu Sans Mono, Consolas, monospace;
      white-space: nowrap;
    }
    @media (max-width: 620px) {
      main { padding: 18px 10px 28px; }
      th, td { padding: 7px 6px; }
      .entity { display: none; }
    }
  </style>
</head>
<body>
  <main>
    <h1>Font Awesome Codes</h1>
    <p class="meta">Generated from the bundled Font Awesome 4.7.0 Free font. Total icons: %d.</p>
    <table>
      <thead>
        <tr><th>Icon</th><th>Name</th><th>Code</th><th>HTML entity</th></tr>
      </thead>
      <tbody>
%s
      </tbody>
    </table>
  </main>
</body>
</html>
""" % (html.escape(font_path), len(items), render_rows(items))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        default=str(DEFAULT_SOURCE),
        help="fontawesome.py source file",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="HTML catalog output path",
    )
    parser.add_argument(
        "--font-path",
        default=DEFAULT_FONT,
        help="Font path written into the generated HTML",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    source = pathlib.Path(args.source)
    output = pathlib.Path(args.output)
    items = parse_items(source)
    output.write_text(render_html(items, args.font_path))
    print("Wrote %d icons to %s" % (len(items), output))


if __name__ == "__main__":
    main()
