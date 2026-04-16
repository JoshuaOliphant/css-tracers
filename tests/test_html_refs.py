# ABOUTME: Tests for the html-refs tool using TDD.
# ABOUTME: Covers class extraction from plain HTML files via stdlib html.parser.

"""Tests for tools/html_refs.py."""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
TOOL = Path(__file__).parent.parent / "tools" / "html_refs.py"


def extract_classes(html: str) -> list[str]:
    """Helper: run extract_classes_from_html on an inline HTML string."""
    from tools.html_refs import extract_classes_from_html
    return sorted(extract_classes_from_html(html))


# ---------------------------------------------------------------------------
# Unit tests — extract_classes_from_html
# ---------------------------------------------------------------------------

def test_single_class():
    """Single class attribute yields that one class."""
    result = extract_classes('<div class="foo"></div>')
    assert result == ["foo"]


def test_multiple_classes_on_one_element():
    """Multiple space-separated classes are split and returned sorted."""
    result = extract_classes('<div class="foo bar baz"></div>')
    assert result == ["bar", "baz", "foo"]


def test_multiple_elements():
    """Classes are extracted from all elements in the document."""
    html = '<div class="alpha"><span class="beta"></span></div>'
    result = extract_classes(html)
    assert result == ["alpha", "beta"]


def test_deduplication():
    """The same class appearing on multiple elements is emitted only once."""
    html = '<div class="foo"><p class="foo"></p></div>'
    result = extract_classes(html)
    assert result == ["foo"]


def test_empty_class_attribute():
    """An empty class="" attribute contributes no class names."""
    result = extract_classes('<div class=""></div>')
    assert result == []


def test_nested_elements():
    """Classes are extracted recursively from nested elements."""
    html = textwrap.dedent("""\
        <section class="outer">
          <div class="middle">
            <span class="inner"></span>
          </div>
        </section>
    """)
    result = extract_classes(html)
    assert result == ["inner", "middle", "outer"]


def test_hash_prefix_stripped():
    """Leading # characters on a class value are stripped defensively."""
    result = extract_classes('<div class="#foo #bar"></div>')
    assert result == ["bar", "foo"]


def test_no_class_attribute():
    """Elements without a class attribute contribute nothing."""
    result = extract_classes('<div id="main"><p>Text</p></div>')
    assert result == []


def test_mixed_elements_deduplication_and_sort():
    """Combined extraction across mixed elements is sorted and deduplicated."""
    html = textwrap.dedent("""\
        <ul class="nav-list">
          <li class="nav-item active"></li>
          <li class="nav-item"></li>
        </ul>
    """)
    result = extract_classes(html)
    assert result == ["active", "nav-item", "nav-list"]


# ---------------------------------------------------------------------------
# CLI test — subprocess round-trip
# ---------------------------------------------------------------------------

def test_cli_with_fixture_file():
    """Running the tool as a script against sample.html produces the expected classes."""
    fixture = FIXTURES / "sample.html"
    result = subprocess.run(
        [sys.executable, str(TOOL), str(fixture)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    output_lines = result.stdout.strip().splitlines()
    # spot-check a few expected classes
    assert "container" in output_lines
    assert "nav-bar" in output_lines
    assert "site-header" in output_lines
    assert "post-title" in output_lines
    # empty class value must NOT appear
    assert "" not in output_lines
    # output must be sorted
    assert output_lines == sorted(output_lines)
    # output must be deduplicated (nav-bar appears twice in fixture)
    assert output_lines.count("nav-bar") == 1


def test_cli_help_flag():
    """--help exits 0 and prints usage information."""
    result = subprocess.run(
        [sys.executable, str(TOOL), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "html-refs" in result.stdout.lower() or "usage" in result.stdout.lower()


def test_cli_no_args_exits_nonzero():
    """Calling with no arguments exits with a non-zero status."""
    result = subprocess.run(
        [sys.executable, str(TOOL)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
