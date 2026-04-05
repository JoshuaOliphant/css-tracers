# Jinja2 AST for CSS Extraction — Novelty Assessment

Prior art research conducted 2026-04-04 to verify that using Jinja2's AST for
CSS class extraction is genuinely novel before publishing.

## Verdict: Novel

Two independent research passes (broad web/PyPI/SO search + targeted GitHub
code search) found **zero instances** of anyone combining Jinja2's AST with CSS
class extraction.

## What We Searched

### Direct searches (all returned zero results)
- "jinja2 AST CSS", "jinja2 parse CSS classes", "jinja2.meta CSS"
- "jinja2 TemplateData CSS", "jinja2 unused CSS", "flask unused CSS"
- "flask purge CSS", "jinja2 static analysis CSS"
- GitHub code search: `jinja2.meta` + `class`, `env.parse` + `css`,
  `TemplateData` + `class=`, `find_referenced_templates` + `css`
- PyPI: "jinja2 CSS", "jinja2 lint CSS", "template CSS analysis"

### Tools that exist but don't do this

| Tool | Approach | Handles Jinja2 AST? | Extracts CSS classes? |
|------|----------|--------------------|-----------------------|
| PurgeCSS | Regex on file content | No | Yes (regex) |
| Tailwind content scanner | Regex on file content | No | Yes (regex) |
| UnCSS | Headless browser (jsdom) | No (needs rendered HTML) | Yes (querySelector) |
| Chrome DevTools Coverage | Runtime instrumentation | No (needs running app) | Yes (byte ranges) |
| curlylint | Custom parser (parsy) | No (builds own parser) | No |
| djLint | Custom regex parser | No | No |
| jinjalint | Custom parser | No | No |
| j2lint | Jinja2 lexer | No | No |
| django-template-analyzer | Django template nodelist | No | No |
| stylelint-no-unused-selectors | TypeScript compiler API | No | Yes (JSX/TSX only) |
| PurifyCSS | Regex | No | Yes (regex) |

### Adjacent work using Jinja2's AST (but not for CSS)

| Project | What it extracts | Technique |
|---------|-----------------|-----------|
| Jinja2 built-in (`jinja2.meta`) | Undeclared variables, referenced templates | `find_undeclared_variables()`, `find_referenced_templates()` |
| Jinja2 built-in (i18n) | Translatable strings | `extract_from_ast()` for Babel |
| webassets | Asset bundle definitions (`{% assets %}` tags) | Walks AST with `iter_child_nodes()` |
| jinja-to-js | Full template structure for JS conversion | AST walk |
| TypeJinja (ICSE 2026) | Type information | MiniJinja IR (not `jinja2.Environment.parse()`) |

**webassets** is the most architecturally similar — it walks Jinja2 AST nodes
using the same `iter_child_nodes()` and `isinstance()` pattern. But it extracts
asset bundle definitions, not CSS classes.

### PurgeCSS extractor ecosystem

PurgeCSS ships extractors for: HTML, Pug, JS (archived), Lit. Community
extractors exist for Vue, Svelte, etc.

**No Jinja2 extractor exists** — not shipped, not community-contributed, not
even discussed in their issue tracker as a feature request.

### Tailwind's explicit statement

Tailwind's docs say: *"Tailwind treats all of your source files as plain text,
and doesn't attempt to actually parse your files as code in any way."*

Every guide for using Tailwind with Flask/Jinja2 (Waylon Walker, Flowbite,
fluix) says the same thing: just point `content` at your templates directory
and let the regex scanner find class-like tokens.

### Django community

The only documented approach for unused CSS in Django is: run PurgeCSS with a
manually-maintained safelist for dynamically-constructed classes. A Medium
article by Bevan Steele explicitly calls out that *"there isn't an industry
standard solution"* for this.

## Three Layers of Novelty

1. **Using Jinja2's own AST** for CSS extraction — the AST has been used for
   i18n, variable detection, template deps, asset bundles, and type checking,
   but never CSS.

2. **Recognizing that `TemplateData` nodes contain parseable HTML** — everyone
   else treats them as opaque strings. We regex into them for `class="..."`
   patterns, and detect when a class attribute is split across a `TemplateData`
   → expression node boundary (the key insight for dynamic classes).

3. **Composing template-aware parsing with CSS analysis via unix tools** —
   every existing tool is monolithic. Our approach separates extraction from
   comparison, making each stage debuggable and reusable.

## Blog Post Angles

- *"Every CSS purging tool ignores your templates — here's how Jinja2's own
  AST solves it"*
- *"Tailwind says it treats files as plain text. Here's what you get when you
  don't."*
- *"The Jinja2 AST nobody uses: extracting CSS classes from template structure"*
- Technical deep-dive into `Output` node interleaving and why it's the key
  to detecting `growth-{{ stage|lower }}` patterns

## Sources Consulted

- PurgeCSS docs and GitHub (extractors, issues, PRs)
- Tailwind CSS content configuration docs
- UnCSS, PurifyCSS, Chrome DevTools Coverage documentation
- curlylint, djLint, jinjalint, j2lint GitHub repos
- django-template-analyzer, django-compressor-purgecss-filter
- webassets GitHub (Jinja2 AST walker implementation)
- TypeJinja (ICSE 2026 paper)
- Stigler et al. 2018 (XSS via multi-stage AST, Athens Journal)
- Karol Kuczmarski's "CSS class helper for Jinja" blog post
- Medium: "Removing unused CSS in Django" (Bevan Steele)
- GitHub code search across 6 query patterns
- PyPI package search
- Stack Overflow / web search across 12+ query combinations
