import pytest

from tools import css_defs


def test_extract_simple_class():
    out = css_defs.extract_classes_from_css(".foo { color: red; }")
    assert out == {"foo"}


def test_extract_multiple_and_compound():
    css = ".a, .b .c { color: red; } .d.e { color: blue; }"
    assert css_defs.extract_classes_from_css(css) == {"a", "b", "c", "d", "e"}


def test_extract_inside_at_rule_media():
    css = "@media (max-width: 600px) { .resp { color: red; } }"
    assert css_defs.extract_classes_from_css(css) == {"resp"}


def test_at_rule_skips_non_qualified_children():
    # comments and parse errors inside @media have no .prelude attribute
    css = "@media (max-width: 600px) { .ok { color: red; } /* comment */ ; @bogus; }"
    assert "ok" in css_defs.extract_classes_from_css(css)


def test_at_rule_without_content():
    # @charset has no content block - rule.content is None branch
    css = '@charset "UTF-8"; .x { color: red; }'
    assert css_defs.extract_classes_from_css(css) == {"x"}


def test_recurses_into_block_tokens():
    # An attribute selector is parsed as a [] block; the recursion path
    # into token.content must walk it without errors. The string content
    # ".foo" inside the brackets is a StringToken, not a class selector,
    # so nothing should be picked up from there.
    css = '[data-x=".foo"].real { color: red; }'
    assert css_defs.extract_classes_from_css(css) == {"real"}


def test_dot_not_followed_by_ident_is_ignored():
    # ".5em" parses as a single dimension token, not a literal '.' + ident.
    css = "div { margin: .5em; } .real { color: red; }"
    assert css_defs.extract_classes_from_css(css) == {"real"}


def test_dot_at_end_of_prelude_does_not_crash():
    # A literal '.' with nothing after it must not crash the extractor.
    # Combine with a real class so we still verify normal extraction.
    css = ".real { color: red; } .* { color: blue; }"
    assert css_defs.extract_classes_from_css(css) == {"real"}


def test_main_help_flag(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["css-defs", "--help"])
    with pytest.raises(SystemExit) as exc:
        css_defs.main()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "css-defs" in out


def test_main_short_help_flag(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["css-defs", "-h"])
    with pytest.raises(SystemExit) as exc:
        css_defs.main()
    assert exc.value.code == 0


def test_main_no_args_errors(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["css-defs"])
    with pytest.raises(SystemExit) as exc:
        css_defs.main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Usage" in err


def test_main_missing_file_errors(monkeypatch, capsys, tmp_path):
    missing = tmp_path / "nope.css"
    monkeypatch.setattr("sys.argv", ["css-defs", str(missing)])
    with pytest.raises(SystemExit) as exc:
        css_defs.main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "No such file" in err


def test_main_reads_file_and_prints_sorted(monkeypatch, capsys, tmp_path):
    f = tmp_path / "a.css"
    f.write_text(".zeta {} .alpha {} .alpha {}")
    monkeypatch.setattr("sys.argv", ["css-defs", str(f)])
    css_defs.main()
    out = capsys.readouterr().out.splitlines()
    assert out == ["alpha", "zeta"]
