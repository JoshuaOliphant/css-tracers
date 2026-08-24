# ABOUTME: Read CSS class names out of class="" attributes in raw text.
# ABOUTME: Shared by the tools that meet HTML inside strings or template data.

"""The class-attribute scanner.

Some tools hold HTML as raw text with no parser in reach, so they read the
attribute with a regex and accept what that costs in precision.
"""

import re


_CLASS_ATTR_PATTERNS = (
    re.compile(r'class="([^"]*)"'),
    re.compile(r"class='([^']*)'"),
)


def scan_class_attrs(text):
    """Return the whitespace-separated tokens of every quoted class= value.

    A regex, not a parser, so the tokens are not guaranteed to be class names.
    `class=` matches without a left boundary, so `superclass="x"` yields `x`;
    an unterminated `class="` pairs with the next quote of the same style
    anywhere later in the text, so malformed input yields junk. Callers that
    need exactness parse instead.
    """
    classes = set()
    for pattern in _CLASS_ATTR_PATTERNS:
        for match in pattern.finditer(text):
            classes.update(match.group(1).split())
    return classes
