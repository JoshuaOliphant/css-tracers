#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# ABOUTME: Extract CSS class names referenced in plain HTML files.
# ABOUTME: Outputs one class name per line, sorted and deduplicated.

"""html-refs — extract CSS class references from plain HTML files.

Usage:
    html-refs <file>...
    html-refs templates/*.html static/partials/*.html

Parses HTML with stdlib html.parser and extracts class attribute values
from all elements. Handles multi-class attributes (class="foo bar baz")
and strips leading # characters defensively.

Outputs one class name per line to stdout, sorted and deduplicated.
"""

import html.parser
import sys


class _ClassExtractor(html.parser.HTMLParser):
    """HTMLParser subclass that collects CSS class names from all elements."""

    def __init__(self):
        super().__init__()
        self.classes: set[str] = set()

    def handle_starttag(self, tag, attrs):
        for attr_name, attr_value in attrs:
            if attr_name == "class" and attr_value:
                for token in attr_value.split():
                    # Strip leading # defensively
                    token = token.lstrip("#")
                    if token:
                        self.classes.add(token)


def extract_classes_from_html(html_text: str) -> set[str]:
    """Extract all CSS class names from an HTML string.

    Returns a set of class name strings found in class="" attributes.
    """
    extractor = _ClassExtractor()
    extractor.feed(html_text)
    return extractor.classes


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print((__doc__ or "").strip())
        sys.exit(0)

    if len(sys.argv) < 2:
        print("Usage: html-refs <file>...", file=sys.stderr)
        sys.exit(1)

    all_classes: set[str] = set()
    had_error = False

    for path in sys.argv[1:]:
        try:
            with open(path, encoding="utf-8") as f:
                html_text = f.read()
            all_classes |= extract_classes_from_html(html_text)
        except FileNotFoundError:
            print(f"html-refs: {path}: No such file", file=sys.stderr)
            had_error = True
        except IsADirectoryError:
            print(f"html-refs: {path}: Is a directory", file=sys.stderr)
            had_error = True
        except PermissionError:
            print(f"html-refs: {path}: Permission denied", file=sys.stderr)
            had_error = True
        except UnicodeDecodeError:
            print(f"html-refs: {path}: Not valid UTF-8 text (binary file?)", file=sys.stderr)
            had_error = True
        except OSError as exc:
            print(f"html-refs: {path}: {exc.strerror}", file=sys.stderr)
            had_error = True

    for cls in sorted(all_classes):
        print(cls)

    if had_error:
        sys.exit(1)


if __name__ == "__main__":
    main()
