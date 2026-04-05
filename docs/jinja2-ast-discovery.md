# Jinja2 AST for CSS Class Extraction — Discovery Notes

Research and proof-of-concept notes from exploring Jinja2's AST as a tool for
CSS class extraction. These findings are novel — no existing tool does this.

## The Problem

Every existing CSS usage analyzer (PurgeCSS, UnCSS, Chrome DevTools Coverage,
Stylelint plugins) was built for the React/Vue/Node ecosystem. When scanning
for CSS class references, they either:

- **Regex-scan** file contents for word-like tokens (PurgeCSS's default
  extractor is essentially `/[A-Za-z0-9-_:/]+/g`)
- **Parse HTML** with a DOM parser (UnCSS uses jsdom, BeautifulSoup works too)
- **Execute in a browser** and check which rules fire (Chrome Coverage)

None of these understand Jinja2 template syntax. The problems:

1. `class="growth-{{ stage|lower }}"` — the class name is split between literal
   HTML and a Jinja2 expression. Regex extractors see `growth-` and `stage` as
   separate tokens, missing the relationship.
2. `{% extends "base.html" %}` — template inheritance means classes in
   `base.html` are relevant to every child. No tool traces this.
3. `{% if active %}active{% endif %}` inside a class attribute — both branches
   need extraction. DOM parsers see mangled HTML.
4. `{% macro button(variant) %}<button class="btn-{{ variant }}">` — the actual
   class depends on call sites.

## Key Discovery: Jinja2 Has a Real AST

Jinja2's `Environment.parse()` returns a proper AST, not a token stream. The
critical node types for CSS extraction:

### `TemplateData` — Literal HTML

When Jinja2 parses a template, all literal (non-template) content becomes
`TemplateData` nodes. These contain raw HTML strings where you can regex for
`class="..."` patterns just like in plain HTML.

```python
from jinja2 import Environment, nodes

env = Environment(loader=FileSystemLoader("app/templates"))
ast = env.parse(source)

for td in ast.find_all(nodes.TemplateData):
    # td.data contains literal HTML — regex for class="..." works here
    for match in re.finditer(r'class="([^"]*)"', td.data):
        classes = match.group(1).split()
```

This handles the easy case — static classes in literal HTML.

### `Output` Nodes — The Key to Dynamic Classes

Here's the crucial insight. In Jinja2's AST, an `Output` node contains a
**sequence** of child nodes that, when concatenated, produce the output text.
These children are a mix of `TemplateData` (literal text) and expression nodes
(`Name`, `Filter`, `Getattr`, `Const`, etc.).

When a template has:
```html
<span class="growth-stage growth-{{ post.growth_stage|lower }}">
```

The AST represents this as an `Output` node with three children:
```
Output
  TemplateData → '<span class="growth-stage growth-'
  Filter (name="lower")
    Getattr (attr="growth_stage")
      Name (name="post")
  TemplateData → '">'
```

The `TemplateData` node ends mid-attribute (no closing `"`), which signals
that the next child node is a Jinja2 expression completing the attribute value.

### Detection Algorithm

To find dynamic CSS classes:

1. Walk all `Output` nodes
2. For each `TemplateData` child, check if it ends with an unclosed
   `class="...` attribute (regex: `class="([^"]*?)$`)
3. If it does, the last whitespace-separated token in the partial value is a
   **prefix** (e.g., `growth-`), and the next sibling node is the dynamic part
4. Continue scanning subsequent `TemplateData` siblings for the closing `"` to
   capture any static classes after the expression

This cleanly separates:
- **Static classes**: complete tokens inside fully-closed `class="..."` attrs
- **Prefix patterns**: partial tokens before a `{{ }}` expression → `growth-*`

### Template Inheritance Resolution

`jinja2.meta.find_referenced_templates()` returns all templates referenced via
`{% extends %}`, `{% include %}`, and `{% import %}`:

```python
import jinja2.meta

ast = env.parse(source)
refs = list(jinja2.meta.find_referenced_templates(ast))
# e.g., ['base.html'] for a child template
# e.g., ['base.html', 'partials/skills_list.html'] for skills.html
```

By recursively resolving these references, you can build the complete set of
classes available to a fully-rendered page. In our project, every template
extends `base.html`, so `base.html`'s classes (nav-bar, prompt-*, terminal-*,
etc.) are implicitly available everywhere.

## Proof of Concept Results

Running the PoC against the digital garden's 22 templates:

- **110+ static classes extracted** from `TemplateData` nodes
- **4 dynamic patterns detected**: `growth-*`, `nav-item*`, `rounded*`, `tag*`
- **Surfaced dead Tailwind classes** in `explore_landing.html` (`bg-garden-surface`,
  `flex`, `rounded-lg`, etc.) that have no backing CSS — these would appear in
  `jinja-refs` output but not `css-defs` output, making them trivially detectable
  via `comm -13`

### What the PoC Handles

| Pattern | Example | Detection |
|---------|---------|-----------|
| Static class in HTML | `class="content-item"` | Regex in `TemplateData` |
| Multiple classes | `class="growth-stage growth-seedling"` | Split on whitespace |
| Dynamic suffix | `class="growth-{{ stage\|lower }}"` | Prefix pattern `growth-*` |
| Conditional class | `{% if active %}active{% endif %}` | Both branches extracted |
| Template inheritance | `{% extends "base.html" %}` | `find_referenced_templates()` |
| Template includes | `{% include "partials/foo.html" %}` | Same mechanism |

### What Remains Unsolved

| Pattern | Example | Why it's hard |
|---------|---------|---------------|
| Macro call sites | `{{ button("primary") }}` → `btn-primary` | Need to trace variable flow |
| Python context vars | `render("t.html", css_class="foo")` | Cross-language, needs `py-refs` |
| Computed classes | `{{ "active" if x else "inactive" }}` | Need expression evaluation |
| Filters that transform | `{{ name\|slugify }}` in class attr | Need to model filter semantics |

The unsolved cases are all about **value flow** — tracing what a variable
contains at render time. The PoC deliberately avoids this and instead emits
wildcard patterns (`growth-*`), which is the right trade-off for a static
analysis tool. You flag the dynamic case for manual review rather than trying
to solve an intractable problem.

## Architecture Insight: Why `Output` Nodes Matter

The reason no existing tool handles Jinja2 well is that they all treat
templates as text. They either:

- Scan the raw source with regex (sees `{{ }}` as noise)
- Parse as HTML (the `{{ }}` breaks the parser or is treated as text content)

Jinja2's AST is the correct representation because it preserves the
**interleaving** of literal HTML and dynamic expressions. An `Output` node is
essentially a concat operation: `TemplateData + Expression + TemplateData`.
When a class attribute spans that boundary, the AST makes the boundary
explicit, which is exactly what you need to detect dynamic classes.

This is analogous to how tree-sitter handles template literals in JavaScript —
the AST has `TemplateString` nodes with interleaved `TemplateSubstitution`
children. Same pattern, same solution.

## Next Steps

1. Turn the PoC into a proper `jinja-refs` uv script with CLI argument handling
2. Build `css-defs` (the easy counterpart) so the two can be composed
3. Test the `comm -23` composition on the digital garden to verify it catches
   the same dead classes we found in the manual audit
4. Handle edge cases: malformed templates, deeply nested inheritance, macros
