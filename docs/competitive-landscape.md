# CSS Usage Tracer — Competitive Landscape Research

Research on existing unused-CSS detection tools, their approaches, and gaps.
Conducted 2026-04-03 to inform the design of composable CSS class tracing tools.

## Existing Tools

### PurgeCSS (Static Analysis, Regex-Based)

**Approach**: PostCSS parses the CSS side. "Extractors" scan content files for
potential class names. The default extractor is a regex (`/[A-Za-z0-9-_:/]+/g`)
that treats every word-like token as a potential class name.

**Extractors shipped**: Default (regex, any file type), `purgecss-from-html`
(HTML parser), `purgecss-from-js` (string extraction, archived/unmaintained),
`purgecss-from-js-experimental` (Prepack-based, abandoned).

**What it handles well**: Fast, no browser needed. Tailwind CSS integration is
excellent (Tailwind v3+ has PurgeCSS built in). Plugin architecture is clean.

**What it misses**:
- No Jinja2 extractor exists (shipped or community)
- Dynamic class construction in any language (`f"card-{variant}"`)
- Template inheritance (`{% extends %}`, `{% block %}`)
- The JS extractor is dead — neither handles template literal interpolation
- Cannot distinguish `.foo .bar` (descendant) from `.foo.bar` (compound)

### UnCSS (Headless Browser, DOM-Based)

**Approach**: Loads HTML into jsdom, executes `<script>` tags, runs
`document.querySelector(selector)` for each CSS selector. If querySelector
returns null, the selector is unused.

**What it handles well**: More accurate for JS-heavy SPAs because it executes
JS and sees the resulting DOM. Correctly handles complex selectors.

**What it misses**:
- Only sees initial page load state (no interactions)
- jsdom is not a real browser (no CSS rendering, media queries)
- No template engine support — needs fully rendered HTML
- Much slower than PurgeCSS
- Largely unmaintained

### Chrome DevTools CSS Coverage (Runtime Instrumentation)

**Approach**: Chrome DevTools Protocol instruments CSS rule usage at runtime.
Tracks which rules are applied to rendered elements. Can be automated via
Puppeteer (`page.coverage.startCSSCoverage()`).

**What it handles well**: 100% accurate for what was actually rendered. Real
browser, real rendering.

**What it misses**:
- Only covers observed states (unhovered buttons = unused hover styles)
- No source mapping to template files
- Cannot detect classes that should exist but don't
- Session-dependent — miss a route, miss its CSS
- Slow for full coverage (script every interaction path)

### Stylelint Plugins

**stylelint-no-unused-selectors**: Uses convention-based file mapping (e.g.,
`FooComponent.css` → `FooComponent.tsx`). TSX plugin uses TypeScript Compiler
API for real AST analysis. No Jinja2 plugin. Requires 1:1 CSS-to-template
mapping, which doesn't work for global stylesheets.

## The Python/Jinja2 Ecosystem Gap

**There are zero tools that understand Jinja2 templates when scanning for CSS
usage.**

- **Django community**: Manual PurgeCSS + safelist. Blog posts describe
  fragile workflows with Python scripts generating PurgeCSS configs.
- **Flask/Jinja2 community**: Nothing. No tools, no plugins, no documented
  approaches.

### What Specifically Breaks with Jinja2

1. **Template inheritance**: `{% extends "base.html" %}` makes parent classes
   relevant to children. No tool traces this.
2. **Dynamic classes via expressions**: `class="{{ 'active' if x else '' }}"`
   — invisible to regex extractors.
3. **Macros**: `{% macro button(v) %}<button class="btn-{{ v }}">` — class
   depends on call site.
4. **Includes with context**: partial templates use classes from parent context.
5. **Python-side construction**: route handlers building class strings.
6. **Filters**: `{{ title|slugify }}` in class attributes requires understanding
   filter semantics.

## Building Block Libraries

### CSS Parsing

| Library | Language | Approach | Best for |
|---------|----------|----------|----------|
| tinycss2 | Python | Token stream | Simple class extraction (`.` + IDENT walk) |
| cssutils | Python | Full CSS DOM | Structured selector access, but lags on modern CSS |
| tree-sitter-css | C/Python | Concrete syntax tree | Structural queries, error-tolerant |
| postcss + postcss-selector-parser | Node | AST | Gold standard for CSS selectors, but requires Node |

### HTML/Template Parsing

| Library | Language | Approach | Best for |
|---------|----------|----------|----------|
| BeautifulSoup4 | Python | Lenient HTML DOM | Extracting class attrs, handles `{{ }}` as text |
| lxml | Python/C | Fast HTML parser | Large files, but less tolerant of template syntax |
| tree-sitter-html | C/Python | Syntax tree | Structural queries, error-tolerant |
| Jinja2 `env.parse()` | Python | Template AST | **The novel approach** — sees the interleaving of HTML and expressions |

### JavaScript Parsing

| Library | Language | Approach | Best for |
|---------|----------|----------|----------|
| tree-sitter-javascript | C/Python | Syntax tree | AST queries for classList, className, template literals |
| Python stdlib `re` | Python | Regex | Quick-and-dirty word extraction (PurgeCSS-style) |
| pyjsesprima | Python | ESTree AST | Dead, doesn't support modern JS |

### Python Parsing

| Library | Language | Approach | Best for |
|---------|----------|----------|----------|
| `ast.parse()` | Python stdlib | AST | Finding string literals, f-strings, zero deps |
| tree-sitter-python | C/Python | Syntax tree | Consistent with tree-sitter for other languages |

## Key Insight: The Extractor Pattern

PurgeCSS's best architectural idea is the **extractor plugin pattern**: a
function that takes file content and returns a list of potential class names.
Language-specific extractors can be more precise than the default regex.

Our composable tools are essentially standalone extractors that output to
stdout instead of returning arrays. Same pattern, unix-composable.

## Sources

- PurgeCSS Extractors Documentation: purgecss.com/extractors
- PurgeCSS Comparison Page: purgecss.com/comparison
- Chrome DevTools CSS Coverage: developer.chrome.com/docs/devtools/coverage
- stylelint-no-unused-selectors: github.com/nodaguti/stylelint-no-unused-selectors
- tree-sitter grammars: github.com/tree-sitter
- Jinja2 meta module: jinja.palletsprojects.com/en/stable/api/
- Django unused CSS approaches: paleblueapps.com, medium.com/rocknnull
