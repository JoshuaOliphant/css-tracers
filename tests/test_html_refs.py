# ABOUTME: Tests for the html-refs tool using TDD.
# ABOUTME: Covers class extraction from plain HTML files via stdlib html.parser.

"""Tests for tools/html_refs.py."""

import textwrap
from pathlib import Path

import pytest

from tools import html_refs

FIXTURES = Path(__file__).parent / "fixtures"


def extract_classes(html: str) -> list[str]:
    """Helper: run extract_classes_from_html on an inline HTML string."""
    return sorted(html_refs.extract_classes_from_html(html))


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


def test_all_hash_token_yields_nothing():
    """A token that is only '#' strips to empty and contributes no class."""
    result = extract_classes('<div class="# foo"></div>')
    assert result == ["foo"]


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
# CLI tests — drive main() in-process via monkeypatched argv
# ---------------------------------------------------------------------------

def test_cli_with_fixture_file(monkeypatch, capsys):
    """Running main() against sample.html produces the expected classes."""
    fixture = FIXTURES / "sample.html"
    monkeypatch.setattr("sys.argv", ["html-refs", str(fixture)])
    html_refs.main()
    output_lines = capsys.readouterr().out.strip().splitlines()
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


def test_cli_help_flag(monkeypatch, capsys):
    """--help exits 0 and prints usage information."""
    monkeypatch.setattr("sys.argv", ["html-refs", "--help"])
    with pytest.raises(SystemExit) as exc:
        html_refs.main()
    assert exc.value.code == 0
    out = capsys.readouterr().out.lower()
    assert "html-refs" in out or "usage" in out


def test_cli_short_help_flag(monkeypatch, capsys):
    """-h exits 0, mirroring the other tools' short help flag."""
    monkeypatch.setattr("sys.argv", ["html-refs", "-h"])
    with pytest.raises(SystemExit) as exc:
        html_refs.main()
    assert exc.value.code == 0


def test_cli_no_args_exits_nonzero(monkeypatch, capsys):
    """Calling with no arguments exits with a non-zero status."""
    monkeypatch.setattr("sys.argv", ["html-refs"])
    with pytest.raises(SystemExit) as exc:
        html_refs.main()
    assert exc.value.code == 1
    assert "Usage" in capsys.readouterr().err


def test_cli_multi_file_accumulation(monkeypatch, capsys):
    """Classes from multiple files are merged, sorted, and deduplicated."""
    fixture = FIXTURES / "sample.html"
    # Pass the same file twice — classes should appear exactly once (deduplicated)
    monkeypatch.setattr("sys.argv", ["html-refs", str(fixture), str(fixture)])
    html_refs.main()
    output_lines = capsys.readouterr().out.strip().splitlines()
    assert output_lines == sorted(output_lines)
    assert output_lines.count("nav-bar") == 1
    assert output_lines.count("container") == 1


def test_cli_missing_file_exits_nonzero(monkeypatch, capsys, tmp_path):
    """A missing file path causes a non-zero exit with the path in stderr."""
    missing = tmp_path / "nope.html"
    monkeypatch.setattr("sys.argv", ["html-refs", str(missing)])
    with pytest.raises(SystemExit) as exc:
        html_refs.main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "nope.html" in err
    assert "No such file" in err


def test_cli_missing_file_continues_processing_other_files(monkeypatch, capsys, tmp_path):
    """A missing file does not prevent other valid files from being processed."""
    fixture = FIXTURES / "sample.html"
    missing = tmp_path / "nope.html"
    monkeypatch.setattr("sys.argv", ["html-refs", str(missing), str(fixture)])
    with pytest.raises(SystemExit) as exc:
        html_refs.main()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    # Classes from the valid file must still appear in stdout
    assert "container" in captured.out.splitlines()
    assert "nope.html" in captured.err


def test_cli_directory_arg_reports_error(monkeypatch, capsys, tmp_path):
    """A directory argument is reported and does not crash the tool."""
    monkeypatch.setattr("sys.argv", ["html-refs", str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        html_refs.main()
    assert exc.value.code == 1
    assert "Is a directory" in capsys.readouterr().err


def test_cli_binary_file_reports_error(monkeypatch, capsys, tmp_path):
    """A non-UTF-8 (binary) file is reported as such and skipped."""
    binary = tmp_path / "blob.html"
    binary.write_bytes(b"\xff\xfe\x00\x01not utf-8")
    monkeypatch.setattr("sys.argv", ["html-refs", str(binary)])
    with pytest.raises(SystemExit) as exc:
        html_refs.main()
    assert exc.value.code == 1
    assert "Not valid UTF-8" in capsys.readouterr().err


def test_cli_generic_oserror_reports_strerror(monkeypatch, capsys, tmp_path):
    """A generic OSError (e.g. permission denied) is reported via its strerror."""
    target = tmp_path / "blocked.html"
    target.write_text("<div class='x'></div>")

    def boom(*args, **kwargs):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr("builtins.open", boom)
    monkeypatch.setattr("sys.argv", ["html-refs", str(target)])
    with pytest.raises(SystemExit) as exc:
        html_refs.main()
    assert exc.value.code == 1
    assert "Permission denied" in capsys.readouterr().err
