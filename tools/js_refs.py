#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["tree-sitter", "tree-sitter-javascript"]
# ///
# ABOUTME: Extract CSS class names referenced in JavaScript files via tree-sitter AST.
# ABOUTME: Handles className assignments, classList operations, and class="" in string literals.

"""js-refs — extract CSS class references from JavaScript files.

Usage:
    js-refs <file>...
    js-refs app/static/js/*.js

Parses JavaScript with tree-sitter and extracts CSS class names from:
- className assignments: el.className = "foo bar"
- classList operations: el.classList.add("foo"), .remove(), .toggle(), .contains()
- class="" attributes in string literals and template literals
- setAttribute("class", "foo bar")

Outputs one class name per line to stdout, sorted and deduplicated.
"""

import re
import sys

import tree_sitter_javascript as tsjs
from tree_sitter import Language, Parser


JS_LANGUAGE = Language(tsjs.language())


def walk(node):
    """Yield all nodes in a tree-sitter tree."""
    yield node
    for child in node.children:
        yield from walk(child)


def get_text(node, source):
    """Get the source text for a node."""
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def extract_classes_from_string(text):
    """Extract CSS class names from class="" patterns in an HTML string."""
    classes = set()
    for match in re.finditer(r'class="([^"]*)"', text):
        for cls in match.group(1).split():
            classes.add(cls)
    for match in re.finditer(r"class='([^']*)'", text):
        for cls in match.group(1).split():
            classes.add(cls)
    return classes


def extract_classes_from_classname_value(text):
    """Extract class names from a className assignment value string."""
    classes = set()
    for cls in text.split():
        # Filter out empty strings and things that look like JS, not CSS
        if cls and not cls.startswith("(") and not cls.startswith("+"):
            classes.add(cls)
    return classes


def extract_classes(source_bytes):
    """Parse JS and extract all CSS class references.

    Uses tree-sitter for structural patterns and regex for HTML-in-strings.
    """
    parser = Parser(JS_LANGUAGE)
    tree = parser.parse(source_bytes)
    classes = set()
    nodes = list(walk(tree.root_node))

    for i, node in enumerate(nodes):
        # Pattern 1: el.className = "foo bar"
        # AST: assignment_expression where left is member_expression with property "className"
        if node.type == "assignment_expression":
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            if (
                left
                and left.type == "member_expression"
                and left.child_by_field_name("property")
                and get_text(left.child_by_field_name("property"), source_bytes) == "className"
            ):
                # Extract classes from all string fragments in the right side
                for child in walk(right):
                    if child.type == "string_fragment":
                        text = get_text(child, source_bytes)
                        classes |= extract_classes_from_classname_value(text)

        # Pattern 2: el.classList.add("foo") / .remove("foo") / .toggle("foo") / .contains("foo")
        # AST: call_expression where function is member_expression with classList
        if node.type == "call_expression":
            func = node.child_by_field_name("function")
            if func and func.type == "member_expression":
                obj = func.child_by_field_name("object")
                prop = func.child_by_field_name("property")
                if (
                    obj
                    and obj.type == "member_expression"
                    and obj.child_by_field_name("property")
                    and get_text(obj.child_by_field_name("property"), source_bytes) == "classList"
                    and prop
                    and get_text(prop, source_bytes) in ("add", "remove", "toggle", "contains")
                ):
                    # Extract class names from arguments
                    args = node.child_by_field_name("arguments")
                    if args:
                        for child in walk(args):
                            if child.type == "string_fragment":
                                text = get_text(child, source_bytes)
                                classes |= extract_classes_from_classname_value(text)

        # Pattern 3: setAttribute("class", "foo bar")
        if node.type == "call_expression":
            func = node.child_by_field_name("function")
            if func and func.type == "member_expression":
                prop = func.child_by_field_name("property")
                if prop and get_text(prop, source_bytes) == "setAttribute":
                    args = node.child_by_field_name("arguments")
                    if args:
                        arg_nodes = [c for c in args.children if c.type in ("string", "template_string")]
                        if len(arg_nodes) >= 2:
                            first_arg = get_text(arg_nodes[0], source_bytes).strip("\"'`")
                            if first_arg == "class":
                                for child in walk(arg_nodes[1]):
                                    if child.type == "string_fragment":
                                        text = get_text(child, source_bytes)
                                        classes |= extract_classes_from_classname_value(text)

        # Pattern 4: class="foo" in string literals and template literals
        # This catches HTML-in-JS patterns like innerHTML, template strings, etc.
        if node.type == "string_fragment":
            text = get_text(node, source_bytes)
            if "class=" in text:
                classes |= extract_classes_from_string(text)

    return classes


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__.strip())
        sys.exit(0)

    if len(sys.argv) < 2:
        print("Usage: js-refs <file>...", file=sys.stderr)
        sys.exit(1)

    all_classes = set()

    for path in sys.argv[1:]:
        try:
            with open(path, "rb") as f:
                source = f.read()
            all_classes |= extract_classes(source)
        except FileNotFoundError:
            print(f"js-refs: {path}: No such file", file=sys.stderr)
            sys.exit(1)

    for cls in sorted(all_classes):
        print(cls)


if __name__ == "__main__":
    main()
