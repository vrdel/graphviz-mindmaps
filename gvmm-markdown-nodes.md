# Markdown nodes for GVMM: implementation proposal

Date: 2026-10-02. Status: design report; Markdown support has not been implemented.

I recommend **`markdown-it-py`**, using **CommonMark with explicitly selected extensions**, and a dedicated renderer that translates Markdown tokens into GVMM's Graphviz labels. Keep the proposed `: md` syntax. Solve the `#` collision in GVMM's outline parser before handing the body to the Markdown library.

The library choice is specific to this project: access to structured tokens matters more than convenient HTML generation. GVMM needs node layout, themes, Font Awesome icons, and Graphviz-compatible output. A generic Markdown-to-HTML call does not provide that integration.

## 1. How the proposed syntax should behave

Your example is a good interface:

```text
# node with markdown
	: md
	:
	: # header title 1
	:
	: i'm text of **bolded** text of paragraph.
	:
```

The indentation in this report's outline examples uses tabs, consistent with the current `.otl` parser. Spaces after the body marker belong to Markdown, not to outline indentation.

The outer heading identifies a GVMM node. Its label contains a GVMM title followed by a Markdown body. The body has one level-one heading and one paragraph containing bold text. A Markdown heading creates a heading **inside the node**, not another graph node.

For a complete mindmap, put the node under a root:

```text
# Markdown examples
	: fname=markdown-examples.jpg notitle theme=github-light
	# node with markdown
		: md
		:
		: # header title 1
		:
		: i'm text of **bolded** text of paragraph.
		:
	# ordinary sibling
		: node
```

No escaping of the inner `#` should be necessary. Requiring `\#` would change the Markdown content into a literal hash and push a parser implementation problem onto the author.

## 2. What the current code does, and why a new collector is necessary

These findings come from the current repository, rather than assumptions about a future implementation:

| Location                                                                         | Current behavior                                                              | Consequence for Markdown                                                                         |
| ---                                                                              | ---                                                                           | ---                                                                                              |
| [parser/outline.py](graphviz_mindmaps/parser/outline.py), `ExtractMindmapBlocks` | Uses substring checks such as `"# " in line` while scanning children.         | A colon-prefixed Markdown heading can enter the outline-heading path.                            |
| Same file, `ParLoc`                                                              | Searches for `#` before searching for `:`.                                    | It does not classify a line by its first structural marker.                                      |
| Same file, `_CollectVerbatimNodeLine` and `_CollectCodeNodeLine`                 | Stop when `'# '` appears anywhere in a body line.                             | Reusing these collectors unchanged would truncate headings and code comments.                    |
| Same file, body extraction                                                       | Uses character-set stripping such as `lstrip("\t:")`, followed by `rstrip()`. | Literal leading colons/tabs and trailing spaces can be lost.                                     |
| [cli.py](graphviz_mindmaps/cli.py), `read_input_lines`                           | File input uses `line.rstrip()`; stdin uses `splitlines()`.                   | File input loses Markdown's trailing-space hard breaks before parsing starts.                    |
| [render/label_html.py](graphviz_mindmaps/render/label_html.py)                   | Applies GVMM-specific inline and line-break conventions.                      | Running Markdown through this path can reinterpret backticks, asterisks, arrows, and semicolons. |
| [render/dot.py](graphviz_mindmaps/render/dot.py), `GenDot`                       | Detects outline children and special code payloads in strings.                | Markdown needs an explicit dispatch path, not incidental matching within its source.             |
| Root attribute collection                                                        | Collects consecutive attribute-looking lines after `fname=`.                  | Root Markdown requires a deliberate transition from attributes to body.                          |

I exercised `ExtractMindmapBlocks` with your example embedded under a root. The current result included the `: # header title 1` line among the extracted structural lines, while omitting the paragraph. This was an extraction probe, not a Markdown rendering test; it confirms the collision exists before any Markdown library is involved.

A small change to a heading regex alone would not address body preservation, scan-cursor ownership, or the renderer's later interpretation of those strings.

## 3. Make outline structure and Markdown content separate languages

### Classify the structural prefix first

Outside a body, an outline heading should match an anchored rule resembling:

```python
OUTLINE_HEADING = re.compile(r"^(?P<indent>\t*)#(?:[ \t]+|$)")
```

After `md` is detected as a complete attribute token, enter a Markdown-body state. At that point, consume the body's colon-prefixed lines before the general outline scanner sees them.

A line such as `\t\t: # heading` is a body line because its structural marker is `:`. Its payload starts with `#`, which the Markdown parser interprets later. This is the same separation needed for `: ## heading`, fenced Python comments, URLs containing fragments, and literal examples of `.otl` syntax.

The generic scanner should receive the first unconsumed line after the body. Do not continue incrementing the old scan index through body lines that another function has already collected. In the existing scanner, setting `cursor` alone is insufficient because the inner loop advances `scan_index`.

### Define the body boundary precisely

My proposed initial rules are:

1. The directive is the standalone token `md`; optionally accept `markdown` as an exact alias.
2. For an ordinary node, node attributes are on its existing attribute line, for example `: md commen bg="#f5f5f5"`.
3. Subsequent body lines must use `:` at the **same outline indentation as that attribute line**.
4. Strip exactly that indentation and one colon. Then strip at most one ASCII separator space. Preserve everything else.
5. `:` and `: ` contribute an empty Markdown line. A colon followed only by additional spaces preserves those spaces as payload.
6. A real unprefixed outline heading ends the body, regardless of whether it introduces a child, sibling, or ancestor. Reprocess it normally.
7. EOF closes the body, including an empty body.
8. An unexpected nonblank line inside this region produces a useful file/line diagnostic rather than silently losing content. Unprefixed blank lines may be skipped for outline readability; use `:` to insert a Markdown blank line reliably.
9. Do not parse attribute-looking content after entering the body: `: bg=red` is Markdown text.

Initially accept only `:` for Markdown body lines. Existing `|` and `;` body aliases can keep their old behavior elsewhere. Supporting every delimiter in the new grammar is optional and should not complicate pipe-table handling.

This prefix decoder illustrates the essential operation; it is not a complete parser:

```python
def decode_markdown_body_line(line, attribute_indent):
    prefix = attribute_indent + ":"
    if not line.startswith(prefix):
        return None
    payload = line[len(prefix):]
    if payload.startswith(" "):
        payload = payload[1:]
    return payload
```

An exact prefix check intentionally rejects a colon at a different indentation. Markdown list nesting and code indentation must go **after** the separator:

````text
	: md
	: - parent item
	:   - nested item
	:
	: ```python
	: # this remains a Python comment
	: if ready:
	:     run()
	: ```
````

The collector should not try to recognize Markdown fences. Every prefixed line remains body content, so Markdown itself can decide how fences and headings interact.

### Preserve input before any interpretation

Change raw file reading to remove newline terminators only, for example `rstrip("\r\n")`. Keep raw source available until the node mode is known. Apply legacy trimming in legacy paths if necessary to preserve old output.

Do not globally dedent Markdown, collapse tabs, normalize nonbreaking spaces, or strip trailing spaces. A body line ending in two spaces is semantically different from one ending in no spaces. Preserve leading colons as well: `: : literal colon` must produce `: literal colon`.

Keep source filename, original line number, and payload offset with each collected line. These are useful both for errors and for later selector support. Do not concatenate several input files into one undifferentiated body: a Markdown body must close at its source-file boundary.

## 4. Preferred Markdown flavour

I would publish the feature as **“CommonMark with GVMM-supported extensions”**, and document the exact supported set. My proposed mature profile adds tables, strikethrough, and task lists. Automatic bare-URL recognition can be optional; explicit Markdown links are sufficient initially.

GFM is a defined extension of CommonMark. Supporting some familiar GitHub features does not establish complete GFM conformance, and a visual renderer for graph nodes will have its own limitations. The formal reference is the [GitHub Flavored Markdown specification](https://github.github.com/gfm/).

For this project I would choose the following behavior:

| Feature                                   | Initial release | Proposed rendering or policy                                                     |
| ---                                       | ---             | ---                                                                              |
| ATX and Setext headings                   | Yes             | Theme-relative heading sizes; no new graph nodes.                                |
| Paragraphs, strong, emphasis              | Yes             | Text runs with explicit styles.                                                  |
| Inline code                               | Yes             | Monospace, with literal contents.                                                |
| Ordered and unordered lists               | Yes             | Indented blocks with explicit markers; preserve ordered-list start values.       |
| Blockquotes                               | Yes             | Indentation and a theme-derived border/accent.                                   |
| Thematic breaks                           | Yes             | Separator block, interpreted by Markdown context.                                |
| Fenced and indented code                  | Yes             | Preserve source; use the existing code-image infrastructure initially.           |
| Explicit and reference links              | Yes, visually   | Display link text and styling; clickable output is a separate export capability. |
| Strikethrough                             | Yes             | Explicit extension and styled runs.                                              |
| Pipe tables                               | Next stage      | Bounded-width table layout and alignment rules.                                  |
| Task lists                                | Next stage      | Static checked/unchecked markers, not interactive controls.                      |
| Images                                    | Next stage      | Local files, with sizing and alt-text behavior defined.                          |
| Raw HTML                                  | Disabled        | Render it as literal text.                                                       |
| Footnotes, math, alerts, definition lists | Deferred        | Enable only with a specified rendering contract.                                 |
| Front matter, includes, executable code   | Disabled        | No metadata parsing or execution inside a node.                                  |

Soft line breaks should become spaces by default. Markdown hard breaks remain hard breaks. This differs deliberately from ordinary GVMM multiline labels. Do not enable automatic typography substitutions: punctuation in technical notes should remain predictable.

A line of `---` may be a thematic break or a Setext heading underline depending on context. Let the Markdown parser decide; do not run GVMM's separator replacement over raw Markdown.

## 5. Library comparison and recommendation

| Library             | Relevant strengths                                                                 | Fit for GVMM                                                          |
| ---                 | ---                                                                                | ---                                                                   |
| **markdown-it-py**  | CommonMark baseline, configurable syntax rules, tokens, optional syntax-tree view. | Preferred: good input to a dedicated graph-label renderer.            |
| **Mistune**         | Custom renderers and AST/token output; extension support.                          | Credible alternative if its API is preferred after a small prototype. |
| **Python-Markdown** | Established extension system and Markdown-to-HTML workflow.                        | Less suitable when CommonMark behavior is the intended contract.      |

`markdown-it-py` exposes block and inline tokens, including block source-line maps, and offers `SyntaxTreeNode` for tree traversal. Its presets include `commonmark`, `gfm-like`, and, in current documentation, `gfm-like2`. `gfm-like` is approximate GFM and requires `linkify-it-py`; `gfm-like2` adds further features. I prefer explicit rules so installed-version defaults do not define GVMM's public syntax. [Parser documentation](https://markdown-it-py.readthedocs.io/en/latest/using.html).

Mistune is a real alternative, not a library to dismiss: it supports `create_markdown(renderer='ast')` and custom renderers. Its convenience HTML function and a custom parser instance have different defaults, so configure it explicitly if chosen. I have not benchmarked either library on this repository. [Mistune guide](https://mistune.lepture.com/en/latest/guide.html).

Python-Markdown explicitly does not target CommonMark. It can be an excellent choice for applications built around its own extension ecosystem, but that is not the contract I recommend here. [Python-Markdown project goals](https://python-markdown.github.io/).

For GVMM, I would spend the prototype budget on correct collection, layout, and source preservation before parser speed. Whether parsing dominates total time is unmeasured; Graphviz and image generation are also part of the workload.

### Initial parser configuration

A proposed first-stage configuration is:

```python
from markdown_it import MarkdownIt

parser = MarkdownIt("commonmark", {
    "html": False,
    "linkify": False,
    "typographer": False,
    "breaks": False,
}).enable("strikethrough")

tokens = parser.parse(markdown_source, env={})
```

Create a fresh environment for each node so reference-link definitions do not leak between nodes. Cache parser configuration if useful, but keep per-document state separate. Enable `table` when the table renderer is ready.

Do not blindly reuse task-list plugin output as Graphviz markup. The available plugin is useful, but its representation must be adapted to static markers in the renderer. Audit the installed plugin's tokens before selecting the adapter. [Task-list plugin documentation](https://mdit-py-plugins.readthedocs.io/en/latest/#task-lists).

### Python compatibility and dependencies

There is a packaging decision to make before installation. The project's `pyproject.toml` declares Python `>=3.9`. The checked current `markdown-it-py` release is **4.2.0**, requiring Python **>=3.10**; **3.0.0** requires **>=3.8**. Current `mdit-py-plugins` also requires Python **>=3.10**. [Current parser metadata](https://pypi.org/project/markdown-it-py/), [3.0.0 metadata](https://pypi.org/project/markdown-it-py/3.0.0/), [plugin metadata](https://pypi.org/project/mdit-py-plugins/).

My initial dependency proposal preserves the declared Python floor:

```toml
# Proposed additions to the existing dependencies, subject to CI validation:
"markdown-it-py>=3,<4; python_version < '3.10'",
"markdown-it-py>=4.2,<5; python_version >= '3.10'",
```

This creates two supported parser branches and therefore requires the same syntax fixtures on both. An alternative is an explicit project-wide Python-floor increase, but it should be a separate decision. Audit the project's actual runtime compatibility too; metadata alone is not proof that every module works on 3.9.

Defer plugin dependencies until their features are enabled. Do not install a broad collection of plugins merely to parse the first heading-and-bold example. These version bounds are a proposal, not a tested dependency change.

## 6. Rendering strategy

Graphviz labels accept a specialized HTML-like grammar, not browser HTML or CSS. A typical Markdown renderer produces elements such as paragraphs, headings, lists, and code blocks that cannot simply be inserted into DOT. Graphviz supports its own table, cell, font, emphasis, image, and break constructs. [Graphviz label grammar](https://graphviz.org/doc/info/shapes.html#html).

I recommend this pipeline:

```text
raw .otl lines
  -> outline/body classification
  -> preserved Markdown source + source locations
  -> Markdown tokens
  -> GVMM rich-text blocks and styled runs
  -> layout and theme resolution
  -> Graphviz-compatible label
  -> existing DOT/image output
```

The intermediate representation is a proposed GVMM design, not something the Markdown library supplies. It should distinguish paragraph, heading, list, quote, separator, code, and table blocks. Inline runs carry text, emphasis, font, color, and optional link destination. Keeping these structured until serialization makes wrapping and future formatting overrides much easier.

For the user's first example, the renderer would assemble an outer label containing the ordinary node title, a larger bold heading row, and a paragraph row with a bold run around `bolded`. The title and Markdown heading are separate elements. Retain the title initially; a body-only display option can be added later under a clearly documented name.

### Proposed layout rules

Use theme font and foreground defaults for prose. Derive heading sizes from the body size rather than hard-coding a separate palette. Inline code uses the project's monospace font. Quote accents, table borders, code backgrounds, and link colors should come from the active theme or explicit node overrides.

Use a bounded content width to keep paragraphs from producing extremely wide mindmaps. A proposed `md_width` attribute could express this in points; its default needs visual trials. Graphviz should receive explicit line breaks produced by a layout step that measures styled runs. A table width alone is not a text-wrapping implementation.

Wrap at ordinary word boundaries, carry styles across wraps, and keep inline-code runs together where possible. For a run longer than the width, choose a documented policy such as allowing overflow initially. Lists need hanging indentation; wrapped text should align with the item text, not its bullet. Table columns need shared widths across rows, not independent paragraph wrapping.

This layout code should be tested with the actual font backend. Pillow and Graphviz may measure fonts differently; leaving a modest width allowance is preferable to assuming their metrics match exactly. Heading-size ratios and spacing should be treated as visual design choices to validate, not standards requirements.

### Code, links, and images

Reuse `RenderCodeImage` for fenced and indented code in the first renderer. Pass the fence language through the existing lexer selection and use the chosen code theme. An unknown language should fall back to plain text. This fits the existing Pygments/Pillow pipeline, but code remains raster content in an otherwise vector label. A later token-based native code renderer could improve SVG text fidelity.

JPG output cannot preserve clickable links. Start with readable styled labels, optionally showing destinations in a compact form. For future SVG or image-map exports, map links deliberately to supported Graphviz attributes; arbitrary inline browser anchors are not a ready-made solution.

When images are added, resolve relative paths against the owning `.otl` file, not an accidental process working directory. Keep dimensions bounded and show alt text or a clear error for missing files. Initial Markdown rendering should not download remote image URLs implicitly.

An alternative backend could render an entire Markdown node to an image using browser HTML/CSS. That would make complex document layout easier but adds a browser/runtime dependency and sacrifices native label text and selector integration. I would reserve it for a later explicit backend if browser-level fidelity becomes a requirement.

## 7. Integrating with the current code

| File or proposed module                     | Work                                                                                                                                                     |
| ---                                         | ---                                                                                                                                                      |
| `cli.py`                                    | Preserve raw line contents and file provenance.                                                                                                          |
| `parser/outline.py`                         | Anchored structural classification; exact `md` detection; body collection with an authoritative next index.                                              |
| `model/document.py`                         | Add a node-content record containing title lines, attributes, body kind/source, and source location. Existing runtime/session classes do not model this. |
| Proposed `parser/markdown.py`               | Configure the parser and translate tokens into the rich-text representation.                                                                             |
| Proposed `render/markdown.py`               | Resolve theme styles, lay out blocks, and serialize supported Graphviz labels.                                                                           |
| `render/dot.py`                             | Dispatch Markdown content explicitly and attach its completed label to the normal node/edge pipeline.                                                    |
| `model/graph.py` and `render/label_html.py` | Share appropriate style helpers while avoiding legacy string mutation of an already rendered Markdown body.                                              |
| `pyproject.toml`                            | Add tested parser dependencies and compatibility bounds.                                                                                                 |

The clean long-term route is typed node content. For a smaller migration, an explicit encoded Markdown payload can follow the existing code-block transport pattern, provided the body is fully consumed first and later scanners cannot inspect it as outline text. Encoding is only transport; it is not parsing or escaping for the final label.

Do not make a new feature depend on recovering Markdown from partially processed HTML. Preserve the source from the start. Likewise, avoid feeding Markdown through `ApplyInlineBacktickBold`, `ConvertLinebreakMarkers`, or `_EscapeVerbatimBodyLine`: those functions implement existing GVMM conventions.

Preserve ordinary node styling such as background, border, and edges. Define `md`, `code`, `block`, and `draw` as mutually exclusive body modes, rejecting conflicts on the attribute line. Text that happens to contain those words inside the body remains ordinary Markdown.

The collector must work after both a single-line title and a multiline GVMM title. Consolidate or cover both extraction branches rather than implementing Markdown in only the first one.

## 8. Root Markdown and formatting selectors

### Root bodies require an explicit transition

I would initially implement Markdown on ordinary nodes, then add root bodies with the same renderer. The root-specific syntax needs care because root attribute lines can span several lines.

A coherent proposed syntax is:

```text
# Root title
# another title line
	: fname=notes.jpg notitle
	: theme=github-light root_bg=seagreen1
	: md
	: # Heading inside the root
	:
	: A **Markdown** paragraph.
```

The line containing `md` is the last root attribute line. Tokens on that line are still attributes; all following colon-prefixed lines are body content. Do not use the first blank line as a delimiter: your example may include or omit it, and blank lines are meaningful Markdown.

Root title lines retain their existing formatting and symbol behavior. The Markdown body must never participate in root theme, output filename, or icon-attribute lookup. Root body support is a second implementation step, not an automatic consequence of adding child Markdown.

### Existing line and word selectors need a stated contract

Markdown source lines, semantic blocks, and wrapped display lines are different things. A three-line Markdown paragraph may display on two or five lines. Table delimiters and link definitions may produce no visible text. Reusing the legacy HTML-fragment counters would make selector behavior depend on layout details.

My recommendation for the first release:

- Keep existing selectors unchanged on all non-Markdown nodes.
- Allow explicitly header-scoped selectors such as `hl1w2fmld` on the GVMM title of a Markdown node.
- Use Markdown syntax for body emphasis and code font.
- Reject body-scoped `l...`/`w...` selectors on Markdown nodes with an explanatory diagnostic until their semantics are implemented. Do not silently apply them to arbitrary generated rows.

For a later release, define body selectors over **logical text lines before wrapping**, with provenance retained in the intermediate representation. Heading text and hard breaks would contribute logical lines; soft breaks would not. Generated list markers and icons would not count as words. Tables and code need separate explicit rules before they can participate.

Source-line selectors are another viable design, but would require mapping inline content back to exact source spans. Block token line maps do not provide full word-level locations automatically. That work should not be hidden in an estimate for basic Markdown rendering.

A useful eventual precedence would be: theme defaults, node defaults, Markdown semantic styles, explicit GVMM overrides. Apply overrides to runs before serialization, not by inserting tags into finished HTML.

## 9. Escaping, diagnostics, and reproducibility

Disabling raw HTML is appropriate for this renderer because browser HTML is outside its output grammar. `markdown-it-py` documents that its default CommonMark configuration enables HTML, so set the option explicitly. [Parser security guidance](https://markdown-it-py.readthedocs.io/en/latest/security.html).

The serializer should escape literal text and attribute values at their output boundary, exactly once. Treat code text as literal. Do not let body strings inject DOT, Graphviz tags, or image directives. This is a correctness requirement even for trusted notes containing `<`, `&`, or quotes.

Keep normal local rendering offline. If clickable links or remote image fetching are introduced later, define allowed schemes and fetch policy at that point. Never execute fenced code.

For unsupported rendering constructs, return a diagnostic with the file, outer node title, and source line. Unknown tokens from an enabled extension should not vanish silently. Markdown's own treatment of incomplete emphasis or an unclosed fence can remain the parser's standard behavior; a missing colon prefix is an outline-grammar problem and deserves a different message.

If caching is worthwhile, include source, parser/profile version, theme, font settings, content width, code style, and referenced image identity in the key. Do not reuse a light-theme render for a dark-theme node. Scope temporary code/image files to the existing render-session lifecycle.

## 10. Test plan and delivery sequence

### Phase 1: correct extraction

Add tests before the rendering code. They should compare the collected source exactly, including spaces and blank lines. Required cases:

- Your heading-and-bold example, followed by a normal sibling.
- All heading levels and headings inside quotes or lists.
- Fenced Python comments containing `# ` and literal `.otl` examples.
- Nested list indentation after the colon prefix.
- Two trailing spaces, trailing backslashes, literal colons, tabs, and nonbreaking spaces.
- EOF, empty bodies, child nodes after a body, multiline outer titles, and multiple mindmaps.
- Multiple input files with no body leakage across files.
- Misindented body lines and missing prefixes with meaningful diagnostics.
- Regression fixtures for existing `block`, `code`, root multiline attributes, and image continuation behavior.

### Phase 2: first useful renderer

Implement the initial feature matrix with one Markdown configuration and a small rich-text representation. Test nested emphasis, inline code, paragraphs, list nesting, ordered-list starts, quotes, hard/soft breaks, Unicode, and code fallback. Verify that raw HTML remains literal and reference links remain node-local.

Render representative generated DOT through both `dot -Tsvg` and the normal JPG path. Validate labels and inspect light/dark output for spacing, width, title/body separation, clipping, and font selection. Token tests alone cannot establish visual correctness.

### Phase 3: richer document features

Add tables, static task lists, and local images only when their layout and fallback behavior have tests. Add root Markdown after changing the root attribute/body boundary. Evaluate body selectors separately, with explicit examples of how numbering works.

### Acceptance criteria for the initial feature

The exact requested example must render one GVMM node with its title, a Markdown heading, and a paragraph containing bold text. The following outline node must remain separate. Markdown source whitespace must survive extraction. Existing node modes must retain their behavior. Generated labels must pass Graphviz validation, and ordinary use must not require a browser or network access.

The highest-risk work is the outline/body boundary and layout integration. The Markdown parser itself is a relatively small component once those contracts are clear.

## 11. Evidence and limits of this report

I inspected the local parsing, rendering, model, code-image, and dependency files, and ran the extraction probe described above. I checked the linked primary documentation and package metadata on the report date. The design choices, module split, profile, feature stages, dependency bounds, and selector policy are recommendations.

No Markdown library was installed or benchmarked for this report. No renderer prototype was built, and no application files were changed. The proposed dependency matrix and visual behavior still need implementation-time validation.
