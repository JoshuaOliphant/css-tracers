#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["jinja2"]
# ///
# ABOUTME: Extract CSS class names referenced in Jinja2 templates via AST walk.
# ABOUTME: Outputs one class name per line, with dynamic expressions as prefix patterns.

"""jinja-refs — extract CSS class references from Jinja2 templates.

Usage:
    jinja-refs [--search-path DIR] <file>...
    jinja-refs --search-path app/templates app/templates/*.html

Walks the Jinja2 AST to find class="" attributes in TemplateData nodes.
Detects dynamic class construction (e.g., growth-{{ stage }}) and outputs
them as prefix patterns (growth-*).

Resolves {% extends %} and {% include %} to trace template inheritance.

Outputs one class name per line to stdout, sorted and deduplicated.
Dynamic patterns are prefixed with # to distinguish them from static classes.
"""

import os
import re
import sys

import jinja2
import jinja2.meta
from jinja2 import nodes


def extract_classes_from_ast(ast):
    """Extract CSS class names from a parsed Jinja2 AST.

    Returns:
        (static, patterns): sets of definite class names and prefix patterns
    """
    static = set()
    patterns = set()

    for output in ast.find_all(nodes.Output):
        children = list(output.iter_child_nodes())

        for i, child in enumerate(children):
            if not isinstance(child, nodes.TemplateData):
                continue

            text = child.data

            # Extract complete class="..." attributes within this text node
            for match in re.finditer(r'class="([^"]*)"', text):
                for cls in match.group(1).split():
                    static.add(cls)

            # Also check single-quoted class attributes
            for match in re.finditer(r"class='([^']*)'", text):
                for cls in match.group(1).split():
                    static.add(cls)

            # Detect class attributes split across nodes (dynamic classes)
            # Pattern: class="prefix-  followed by a Jinja2 expression
            open_match = re.search(r'class="([^"]*?)$', text)
            if not open_match:
                open_match = re.search(r"class='([^']*?)$", text)

            if open_match:
                partial = open_match.group(1)
                parts = partial.split()
                if parts:
                    # All but the last token are complete class names
                    for cls in parts[:-1]:
                        static.add(cls)
                    # The last token is a prefix for a dynamic class
                    last = parts[-1]
                    if last:
                        patterns.add(f"{last}*")

                # Scan forward for the closing quote to capture trailing classes
                for j in range(i + 1, len(children)):
                    if isinstance(children[j], nodes.TemplateData):
                        closing = children[j].data
                        close_match = re.match(r'([^"\']*)["\']', closing)
                        if close_match:
                            remaining = close_match.group(1)
                            for cls in remaining.split():
                                if cls:
                                    static.add(cls)
                        break

    return static, patterns


def resolve_templates(env, template_names):
    """Resolve all templates in inheritance/include chains.

    Returns set of all template names that are part of the chain.
    """
    resolved = set()
    to_process = list(template_names)

    while to_process:
        name = to_process.pop()
        if name in resolved:
            continue
        resolved.add(name)

        try:
            source = env.loader.get_source(env, name)[0]
            ast = env.parse(source)
            refs = list(jinja2.meta.find_referenced_templates(ast))
            to_process.extend(refs)
        except Exception:
            pass

    return resolved


def find_templates(paths, search_path):
    """Resolve file paths to template names relative to search_path."""
    templates = []
    for path in paths:
        if os.path.isfile(path):
            rel = os.path.relpath(path, search_path)
            templates.append(rel)
        elif os.path.isdir(path):
            for root, _, files in os.walk(path):
                for f in files:
                    if f.endswith((".html", ".jinja", ".jinja2", ".j2")):
                        full = os.path.join(root, f)
                        rel = os.path.relpath(full, search_path)
                        templates.append(rel)
    return templates


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__.strip())
        sys.exit(0)

    # Parse --search-path argument
    args = sys.argv[1:]
    search_path = "."

    if "--search-path" in args:
        idx = args.index("--search-path")
        if idx + 1 >= len(args):
            print("jinja-refs: --search-path requires a directory", file=sys.stderr)
            sys.exit(1)
        search_path = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    if not args:
        print("Usage: jinja-refs [--search-path DIR] <file|dir>...", file=sys.stderr)
        sys.exit(1)

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(search_path))

    # Collect template names
    template_names = find_templates(args, search_path)

    if not template_names:
        print("jinja-refs: no templates found", file=sys.stderr)
        sys.exit(1)

    # Resolve inheritance chains to get all related templates
    all_templates = resolve_templates(env, template_names)

    # Extract classes from all templates
    all_static = set()
    all_patterns = set()

    for name in sorted(all_templates):
        try:
            source = env.loader.get_source(env, name)[0]
            ast = env.parse(source)
            static, dynamic = extract_classes_from_ast(ast)
            all_static |= static
            all_patterns |= dynamic
        except Exception as e:
            print(f"jinja-refs: {name}: {e}", file=sys.stderr)

    # Output static classes
    for cls in sorted(all_static):
        print(cls)

    # Output dynamic patterns (prefixed with # so they're distinguishable)
    for pat in sorted(all_patterns):
        print(f"# {pat}")


if __name__ == "__main__":
    main()
