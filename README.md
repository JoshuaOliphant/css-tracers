# css-tracers

Composable unix tools for tracing CSS class usage across the full web stack: CSS definitions, HTML/Jinja2 templates, JavaScript, and Python.

## The Problem

Existing CSS purging tools (PurgeCSS, UnCSS, Tailwind) were built for the React/Vue/Node ecosystem. None understand Jinja2 templates, Python string construction, or template inheritance. The Python/Flask/FastAPI world is a complete blind spot.

`css-tracers` fixes this with four small tools that each do one thing and compose with standard unix utilities.

## The Novel Part

`jinja-refs` walks Jinja2's own AST (`Environment.parse()`) to extract CSS classes from templates. It detects dynamic class construction like `growth-{{ stage }}` by recognizing node boundaries in `Output` nodes. No existing tool does this. See [docs/jinja2-ast-discovery.md](docs/jinja2-ast-discovery.md) and [docs/novelty-assessment.md](docs/novelty-assessment.md) for details.

## Tools

| Tool | Parser | What it finds |
|------|--------|---------------|
| `css-defs` | tinycss2 | CSS class names defined in stylesheets |
| `jinja-refs` | jinja2 AST | Class refs in Jinja2 templates |
| `js-refs` | tree-sitter | Class refs in JavaScript |
| `py-refs` | stdlib ast | Class-like strings in Python |

Each tool outputs one class name per line to stdout, sorted and deduplicated. Dynamic patterns (from f-strings or Jinja2 expressions) are output as `# prefix-*` comments.

## Install

```bash
# From GitHub (preferred)
uv tool install git+https://github.com/JoshuaOliphant/css-tracers

# From a local clone
git clone https://github.com/JoshuaOliphant/css-tracers.git
cd css-tracers
uv tool install .

# No install needed (standalone scripts)
uv run --script tools/css_defs.py app/static/css/*.css
```

## Usage

```bash
# What CSS classes are defined?
css-defs app/static/css/*.css

# What classes do your Jinja2 templates reference?
jinja-refs --search-path app/templates app/templates/*.html

# What classes does your JavaScript use?
js-refs app/static/js/*.js

# What classes does your Python generate?
py-refs app/services/*.py app/routers/*.py
```

## Composition

The tools are designed to compose with `sort`, `comm`, `diff`, and other unix utilities.

```bash
# Find dead CSS: defined but never referenced anywhere
comm -23 \
  <(css-defs app/static/css/*.css) \
  <(cat \
    <(jinja-refs --search-path app/templates app/templates/**/*.html) \
    <(js-refs app/static/js/*.js) \
    <(py-refs app/**/*.py) \
  | sort -u)

# Find phantom classes: referenced in templates but no CSS rule exists
comm -13 \
  <(css-defs app/static/css/*.css) \
  <(jinja-refs --search-path app/templates app/templates/**/*.html)

# What classes does a single template use?
jinja-refs --search-path app/templates app/templates/index.html
```

## Design Principles

- **Unix philosophy**: each tool does one thing, outputs newline-delimited class names to stdout
- **PEP 723 scripts**: each tool is a single Python file with inline dependency declarations, runnable via `uv run --script`
- **No configuration**: tools take file paths as arguments, nothing else
- **Err toward false positives in refs**: better to report a class as "used" than miss it

## License

MIT
