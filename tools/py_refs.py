#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# ABOUTME: Extract CSS class names referenced in Python files via stdlib ast.
# ABOUTME: Finds class="" in HTML strings, f-string class patterns, and known generators.

"""py-refs — extract CSS class references from Python source files.

Usage:
    py-refs <file>...
    py-refs app/services/*.py app/routers/*.py

Parses Python with stdlib ast and extracts CSS class names from:
- class="" attributes in string literals (HTML-in-Python)
- f-strings containing class="" or "class-{...}" patterns
- Known CSS-generating patterns (markdown extensions, f"prefix-{enum}")

Outputs one class name per line to stdout, sorted and deduplicated.
Dynamic patterns (f-strings) are output as prefix patterns prefixed with #.
"""

import ast
import re
import sys


def extract_classes_from_html_string(text):
    """Extract CSS class names from class="" patterns in HTML strings."""
    classes = set()
    for match in re.finditer(r'class="([^"]*)"', text):
        for cls in match.group(1).split():
            classes.add(cls)
    for match in re.finditer(r"class='([^']*)'", text):
        for cls in match.group(1).split():
            classes.add(cls)
    return classes


class CSSClassVisitor(ast.NodeVisitor):
    """AST visitor that extracts CSS class references from Python code."""

    def __init__(self):
        self.static_classes = set()
        self.patterns = set()

    def visit_Constant(self, node):
        """Check string constants for class="" patterns (HTML in Python)."""
        if isinstance(node.value, str) and "class=" in node.value:
            self.static_classes |= extract_classes_from_html_string(node.value)
        self.generic_visit(node)

    def visit_JoinedStr(self, node):
        """Check f-strings for CSS class patterns.

        Handles patterns like:
        - f'growth-{stage.value}' → pattern "growth-*"
        - f'<div class="growth-{stage}">' → pattern "growth-*"
        """
        # Reconstruct the f-string to find class= patterns and f-string boundaries
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(("str", value.value))
            else:
                parts.append(("expr", "{...}"))

        # Join the string parts to look for patterns
        full_text = "".join(p[1] for p in parts)

        # Check for class="" in the reconstructed f-string
        if "class=" in full_text:
            self.static_classes |= extract_classes_from_html_string(full_text)

        # Check for CSS prefix patterns like f"growth-{expr}"
        # Walk through parts looking for string ending with prefix + expression
        for i, (kind, text) in enumerate(parts):
            if kind == "str" and i + 1 < len(parts) and parts[i + 1][0] == "expr":
                # Check if this string ends with a CSS-class-like prefix
                # Pattern: word characters ending with a hyphen before an expression
                prefix_match = re.search(r'([a-zA-Z][\w-]*-)$', text)
                if prefix_match:
                    self.patterns.add(f"{prefix_match.group(1)}*")

        self.generic_visit(node)

    def visit_Call(self, node):
        """Detect known CSS class generators.

        Catches patterns like:
        - markdown.Markdown(extensions=['markdown.extensions.codehilite'])
          → implies codehilite CSS classes will be generated
        """
        # Check for markdown extension registration
        for keyword in getattr(node, 'keywords', []):
            if keyword.arg == 'extensions' and isinstance(keyword.value, ast.List):
                for elt in keyword.value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        ext_name = elt.value
                        # Map known markdown extensions to the CSS classes they generate
                        if 'codehilite' in ext_name:
                            self.static_classes.add('codehilite')
                        if 'admonition' in ext_name:
                            self.static_classes.update([
                                'admonition', 'admonition-title',
                                'note', 'warning', 'aside',
                            ])
                        if 'toc' in ext_name:
                            self.static_classes.add('toc')

        self.generic_visit(node)


def extract_classes(source_text, filename="<unknown>"):
    """Parse Python source and extract CSS class references."""
    try:
        tree = ast.parse(source_text, filename=filename)
    except SyntaxError as e:
        print(f"py-refs: {filename}: syntax error: {e}", file=sys.stderr)
        return set(), set()

    visitor = CSSClassVisitor()
    visitor.visit(tree)
    return visitor.static_classes, visitor.patterns


def main():
    if len(sys.argv) < 2:
        print("Usage: py-refs <file>...", file=sys.stderr)
        sys.exit(1)

    all_static = set()
    all_patterns = set()

    for path in sys.argv[1:]:
        try:
            with open(path) as f:
                source = f.read()
            static, patterns = extract_classes(source, filename=path)
            all_static |= static
            all_patterns |= patterns
        except FileNotFoundError:
            print(f"py-refs: {path}: No such file", file=sys.stderr)
            sys.exit(1)

    for cls in sorted(all_static):
        print(cls)

    for pat in sorted(all_patterns):
        print(f"# {pat}")


if __name__ == "__main__":
    main()
