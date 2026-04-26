import pytest
import jinja2

from tools import jinja_refs


def parse(source):
    env = jinja2.Environment()
    return env.parse(source)


def test_static_double_quoted():
    static, patterns = jinja_refs.extract_classes_from_ast(parse('<div class="a b c"></div>'))
    assert static == {"a", "b", "c"}
    assert patterns == set()


def test_static_single_quoted():
    static, patterns = jinja_refs.extract_classes_from_ast(parse("<div class='x y'></div>"))
    assert static == {"x", "y"}
    assert patterns == set()


def test_dynamic_double_quoted_prefix():
    src = '<div class="growth-{{ stage }}"></div>'
    static, patterns = jinja_refs.extract_classes_from_ast(parse(src))
    assert patterns == {"growth-*"}
    assert static == set()


def test_dynamic_single_quoted_prefix():
    src = "<div class='growth-{{ stage }}'></div>"
    static, patterns = jinja_refs.extract_classes_from_ast(parse(src))
    assert patterns == {"growth-*"}


def test_dynamic_with_static_prefix_classes():
    # First two tokens are complete classes, last is a dynamic prefix
    src = '<div class="card big growth-{{ stage }}"></div>'
    static, patterns = jinja_refs.extract_classes_from_ast(parse(src))
    assert static == {"card", "big"}
    assert patterns == {"growth-*"}


def test_dynamic_with_trailing_static_classes():
    # The closing portion after the expression contributes static classes
    src = '<div class="growth-{{ stage }} done extra"></div>'
    static, patterns = jinja_refs.extract_classes_from_ast(parse(src))
    assert "done" in static
    assert "extra" in static
    assert patterns == {"growth-*"}


def test_dynamic_unterminated_quote_no_close_match():
    # No closing quote inside any later TemplateData; the inner regex
    # for the closing quote should not match and the loop should bail.
    src = '<div class="prefix-{{ stage }}'
    static, patterns = jinja_refs.extract_classes_from_ast(parse(src))
    assert patterns == {"prefix-*"}


def test_dynamic_with_only_one_token_treats_it_as_prefix():
    # `class="foo {{ stage }}"`: the single token "foo" is the prefix.
    src = '<div class="foo {{ stage }}"></div>'
    static, patterns = jinja_refs.extract_classes_from_ast(parse(src))
    assert static == set()
    assert patterns == {"foo*"}


def test_dynamic_followed_by_template_data_with_no_close_quote():
    # After the expression, the next TemplateData has no quote at all,
    # so close_match returns None and the inner add is skipped.
    src = '<div class="prefix-{{ stage }} no closing quote here'
    static, patterns = jinja_refs.extract_classes_from_ast(parse(src))
    assert patterns == {"prefix-*"}
    # Nothing extra should bleed in from the unmatched tail
    assert static == set()


def test_find_templates_skips_nonexistent_paths(tmp_path):
    # A path that is neither a file nor a dir should be silently skipped.
    real = tmp_path / "real.html"
    real.write_text("x")
    names = jinja_refs.find_templates(
        [str(tmp_path / "ghost.html"), str(real)], str(tmp_path)
    )
    assert names == ["real.html"]


def test_dynamic_partial_only_whitespace_no_parts():
    # `class=" {{ stage }}"`: partial is whitespace only, split() returns []
    # so the inner block is skipped (no static, no pattern from this side).
    src = '<div class=" {{ stage }}"></div>'
    static, patterns = jinja_refs.extract_classes_from_ast(parse(src))
    assert static == set()
    assert patterns == set()


def test_non_template_data_children_are_skipped():
    # Plain expression at top level produces an Output containing a Name node,
    # not a TemplateData. The loop must skip it cleanly.
    static, patterns = jinja_refs.extract_classes_from_ast(parse("{{ foo }}"))
    assert static == set()
    assert patterns == set()


def test_resolve_templates_follows_extends_and_include(tmp_path):
    base = tmp_path / "base.html"
    base.write_text('<html><body>{% block body %}{% endblock %}</body></html>')
    page = tmp_path / "page.html"
    page.write_text('{% extends "base.html" %}{% block body %}{% include "frag.html" %}{% endblock %}')
    frag = tmp_path / "frag.html"
    frag.write_text('<div class="frag-class"></div>')

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(tmp_path)))
    resolved = jinja_refs.resolve_templates(env, ["page.html"])
    assert {"page.html", "base.html", "frag.html"} <= resolved


def test_resolve_templates_handles_missing(tmp_path):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(tmp_path)))
    # No exception even though template does not exist
    resolved = jinja_refs.resolve_templates(env, ["nope.html"])
    assert resolved == {"nope.html"}


def test_resolve_templates_dedupes(tmp_path):
    a = tmp_path / "a.html"
    a.write_text('{% include "b.html" %}')
    b = tmp_path / "b.html"
    b.write_text('{% include "a.html" %}')
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(tmp_path)))
    resolved = jinja_refs.resolve_templates(env, ["a.html", "a.html"])
    assert resolved == {"a.html", "b.html"}


def test_find_templates_file(tmp_path):
    f = tmp_path / "t.html"
    f.write_text("<div></div>")
    names = jinja_refs.find_templates([str(f)], str(tmp_path))
    assert names == ["t.html"]


def test_find_templates_directory_filters_extensions(tmp_path):
    (tmp_path / "a.html").write_text("a")
    (tmp_path / "b.jinja").write_text("b")
    (tmp_path / "c.jinja2").write_text("c")
    (tmp_path / "d.j2").write_text("d")
    (tmp_path / "skip.txt").write_text("skip")
    names = jinja_refs.find_templates([str(tmp_path)], str(tmp_path))
    assert set(names) == {"a.html", "b.jinja", "c.jinja2", "d.j2"}


def test_main_help(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["jinja-refs", "--help"])
    with pytest.raises(SystemExit) as exc:
        jinja_refs.main()
    assert exc.value.code == 0
    assert "jinja-refs" in capsys.readouterr().out


def test_main_short_help(monkeypatch):
    monkeypatch.setattr("sys.argv", ["jinja-refs", "-h"])
    with pytest.raises(SystemExit) as exc:
        jinja_refs.main()
    assert exc.value.code == 0


def test_main_search_path_missing_value(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["jinja-refs", "--search-path"])
    with pytest.raises(SystemExit) as exc:
        jinja_refs.main()
    assert exc.value.code == 1
    assert "--search-path requires" in capsys.readouterr().err


def test_main_no_args_after_search_path(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("sys.argv", ["jinja-refs", "--search-path", str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        jinja_refs.main()
    assert exc.value.code == 1
    assert "Usage" in capsys.readouterr().err


def test_main_no_templates_found(monkeypatch, capsys, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr("sys.argv", ["jinja-refs", str(empty)])
    with pytest.raises(SystemExit) as exc:
        jinja_refs.main()
    assert exc.value.code == 1
    assert "no templates" in capsys.readouterr().err


def test_main_extracts_and_prints(monkeypatch, capsys, tmp_path):
    base = tmp_path / "base.html"
    base.write_text('<html><body>{% block body %}{% endblock %}</body></html>')
    page = tmp_path / "page.html"
    page.write_text(
        '{% extends "base.html" %}{% block body %}'
        '<div class="alpha zeta growth-{{ stage }}"></div>'
        '{% endblock %}'
    )

    monkeypatch.setattr(
        "sys.argv",
        ["jinja-refs", "--search-path", str(tmp_path), str(page)],
    )
    jinja_refs.main()
    out = capsys.readouterr().out.splitlines()
    assert "alpha" in out
    assert "zeta" in out
    assert "# growth-*" in out
    # Static classes are printed before the dynamic-pattern lines
    assert out.index("alpha") < out.index("# growth-*")


def test_main_reports_parse_errors_per_template(monkeypatch, capsys, tmp_path):
    bad = tmp_path / "bad.html"
    # Unmatched {% will raise a TemplateSyntaxError when env.parse runs
    bad.write_text("{% if foo %}")
    monkeypatch.setattr(
        "sys.argv",
        ["jinja-refs", "--search-path", str(tmp_path), str(bad)],
    )
    jinja_refs.main()
    err = capsys.readouterr().err
    assert "bad.html" in err
