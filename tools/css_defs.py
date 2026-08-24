#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["tinycss2", "css-tracers"]
#
# [tool.uv.sources]
# css-tracers = { path = "..", editable = true }
# ///
# ABOUTME: Extract CSS class names defined in stylesheets.
# ABOUTME: Outputs one class name per line, sorted and deduplicated.

"""css-defs — extract CSS class selector names from CSS files.

Usage:
    css-defs <file>...
    css-defs app/static/css/*.css

Outputs one class name per line to stdout, sorted and deduplicated.
Handles nested selectors, media queries, and all at-rules.
"""

import tinycss2

from tools.tracer import run


def extract_classes_from_tokens(tokens):
    """Walk a token list and yield class names (tokens after '.')."""
    classes = set()
    i = 0
    while i < len(tokens):
        token = tokens[i]
        # A class selector is a DELIM('.') followed by an IDENT
        if token.type == "literal" and token.value == ".":
            if i + 1 < len(tokens) and tokens[i + 1].type == "ident":
                classes.add(tokens[i + 1].value)
                i += 2
                continue
        # Recurse into blocks (media queries, nested rules, etc.)
        if hasattr(token, "content") and token.content is not None:
            classes |= extract_classes_from_tokens(token.content)
        i += 1
    return classes


def extract_classes_from_css(css_text):
    """Parse CSS and extract all class selector names."""
    classes = set()
    rules = tinycss2.parse_stylesheet(css_text, skip_whitespace=True)

    for rule in rules:
        if rule.type == "qualified-rule":
            # The prelude contains the selector
            classes |= extract_classes_from_tokens(rule.prelude)
        elif rule.type == "at-rule" and rule.content is not None:
            # Recurse into at-rules (@media, @supports, etc.)
            nested_rules = tinycss2.parse_rule_list(rule.content, skip_whitespace=True)
            for nested in nested_rules:
                if hasattr(nested, "prelude"):
                    classes |= extract_classes_from_tokens(nested.prelude)

    return classes


def main():
    run(name="css-defs", doc=__doc__, extract=extract_classes_from_css)


if __name__ == "__main__":
    main()
