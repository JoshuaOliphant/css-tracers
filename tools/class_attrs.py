# ABOUTME: Read CSS class names out of class="" attributes in raw text.
# ABOUTME: Shared by the tools that meet HTML inside strings or template data.

"""The class-attribute scanner.

Some tools meet HTML as raw text — embedded in a JavaScript string, embedded in
a Python string, or sitting in a Jinja2 `TemplateData` node — with no parser to
hand them the attributes. This module owns the rule they share: read the class
names out of a complete, quoted `class` attribute.
"""

import re


_CLASS_ATTR_PATTERNS = (
    re.compile(r'class="([^"]*)"'),
    re.compile(r"class='([^']*)'"),
)


def scan_class_attrs(text):
    """Return the CSS class names in every complete class="" attribute in text.

    Both quoting styles are read, whitespace-separated names are split apart,
    and an attribute whose closing quote is missing contributes nothing.
    """
    classes = set()
    for pattern in _CLASS_ATTR_PATTERNS:
        for match in pattern.finditer(text):
            classes.update(match.group(1).split())
    return classes
