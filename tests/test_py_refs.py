import pytest

from tools import py_refs


def test_extract_classes_from_html_string_double_and_single():
    assert py_refs.extract_classes_from_html_string('<div class="a b"></div>') == {"a", "b"}
    assert py_refs.extract_classes_from_html_string("<div class='c d'></div>") == {"c", "d"}


def test_string_constant_with_class_attribute():
    src = 's = "<div class=\\"foo bar\\"></div>"'
    static, patterns = py_refs.extract_classes(src)
    assert static == {"foo", "bar"}
    assert patterns == set()


def test_string_constant_without_class_is_ignored():
    src = 's = "no class attribute"'
    static, patterns = py_refs.extract_classes(src)
    assert static == set()
    assert patterns == set()


def test_non_string_constants_are_ignored():
    src = "x = 1\ny = 3.14\nz = True\nq = None"
    static, patterns = py_refs.extract_classes(src)
    assert static == set()
    assert patterns == set()


def test_fstring_with_class_attribute_static():
    src = 'name = "x"\ns = f"<div class=\\"static-only\\">{name}</div>"'
    static, patterns = py_refs.extract_classes(src)
    assert "static-only" in static


def test_fstring_with_prefix_pattern():
    src = 'stage = "x"\ns = f"growth-{stage}"'
    static, patterns = py_refs.extract_classes(src)
    assert patterns == {"growth-*"}


def test_fstring_class_attribute_with_dynamic_prefix():
    # f-string substitution turns into "{...}" placeholder; the
    # reconstructed text contains class="growth-{...}" which the regex
    # treats as a static class "growth-{...}" (no whitespace splits).
    # We only assert the prefix pattern detection works.
    src = 'stage = "x"\ns = f"<div class=\\"growth-{stage}\\">x</div>"'
    static, patterns = py_refs.extract_classes(src)
    assert "growth-*" in patterns


def test_fstring_without_class_or_prefix_yields_nothing():
    src = 'name = "x"\ns = f"hello {name}"'
    static, patterns = py_refs.extract_classes(src)
    assert static == set()
    assert patterns == set()


def test_fstring_prefix_requires_trailing_hyphen():
    # "name{x}" has no trailing hyphen, so no prefix pattern is added.
    src = 'x = 1\ns = f"name{x}"'
    static, patterns = py_refs.extract_classes(src)
    assert patterns == set()


def test_fstring_str_followed_by_str_no_pattern():
    # When two string parts are adjacent (no expression between), the
    # prefix-pattern check must not fire.
    src = 'x = "y"\ns = f"prefix-suffix"'
    static, patterns = py_refs.extract_classes(src)
    assert patterns == set()


def test_markdown_extension_codehilite():
    src = (
        "import markdown\n"
        "md = markdown.Markdown(extensions=['markdown.extensions.codehilite'])\n"
    )
    static, patterns = py_refs.extract_classes(src)
    assert "codehilite" in static


def test_markdown_extension_admonition():
    src = (
        "import markdown\n"
        "md = markdown.Markdown(extensions=['markdown.extensions.admonition'])\n"
    )
    static, _ = py_refs.extract_classes(src)
    assert {"admonition", "admonition-title", "note", "warning", "aside"} <= static


def test_markdown_extension_toc():
    src = (
        "import markdown\n"
        "md = markdown.Markdown(extensions=['markdown.extensions.toc'])\n"
    )
    static, _ = py_refs.extract_classes(src)
    assert "toc" in static


def test_call_with_non_extensions_keyword_ignored():
    src = "func(other='markdown.extensions.codehilite')"
    static, _ = py_refs.extract_classes(src)
    assert static == set()


def test_call_extensions_with_non_string_element_ignored():
    src = "func(extensions=[some_var])"
    static, _ = py_refs.extract_classes(src)
    assert static == set()


def test_call_extensions_unknown_name_ignored():
    src = "func(extensions=['markdown.extensions.unknown'])"
    static, _ = py_refs.extract_classes(src)
    assert static == set()


def test_call_extensions_not_a_list_ignored():
    src = "func(extensions='markdown.extensions.codehilite')"
    static, _ = py_refs.extract_classes(src)
    assert static == set()


def test_call_with_no_keywords_ignored():
    src = "len([1, 2, 3])"
    static, _ = py_refs.extract_classes(src)
    assert static == set()


def test_extract_classes_syntax_error(capsys):
    static, patterns = py_refs.extract_classes("def broken(", filename="bad.py")
    assert static == set()
    assert patterns == set()
    err = capsys.readouterr().err
    assert "bad.py" in err
    assert "syntax error" in err


def test_main_help(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["py-refs", "--help"])
    with pytest.raises(SystemExit) as exc:
        py_refs.main()
    assert exc.value.code == 0
    assert "py-refs" in capsys.readouterr().out


def test_main_short_help(monkeypatch):
    monkeypatch.setattr("sys.argv", ["py-refs", "-h"])
    with pytest.raises(SystemExit) as exc:
        py_refs.main()
    assert exc.value.code == 0


def test_main_no_args(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["py-refs"])
    with pytest.raises(SystemExit) as exc:
        py_refs.main()
    assert exc.value.code == 1
    assert "Usage" in capsys.readouterr().err


def test_main_missing_file(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("sys.argv", ["py-refs", str(tmp_path / "nope.py")])
    with pytest.raises(SystemExit) as exc:
        py_refs.main()
    assert exc.value.code == 1
    assert "No such file" in capsys.readouterr().err


def test_main_reads_and_prints(monkeypatch, capsys, tmp_path):
    f = tmp_path / "a.py"
    f.write_text(
        'stage = "x"\n'
        's = f"<div class=\\"alpha zeta\\">growth-{stage}</div>"\n'
    )
    monkeypatch.setattr("sys.argv", ["py-refs", str(f)])
    py_refs.main()
    out = capsys.readouterr().out.splitlines()
    assert "alpha" in out
    assert "zeta" in out
    assert "# growth-*" in out
