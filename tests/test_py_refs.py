import pytest

from tools import py_refs


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
    src = 'stage = "x"\ns = f"<div class=\\"growth-{stage}\\">x</div>"'
    static, patterns = py_refs.extract_classes(src)
    assert patterns == {"growth-*"}
    # The reconstructed f-string still carries the {...} placeholder, so the
    # scanner reports it as a class name too.
    assert static == {"growth-{...}"}


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


def test_main_missing_file_continues_processing(monkeypatch, capsys, tmp_path):
    good = tmp_path / "good.py"
    good.write_text('s = "<div class=\\"real\\"></div>"\n')
    monkeypatch.setattr("sys.argv", ["py-refs", str(tmp_path / "nope.py"), str(good)])
    with pytest.raises(SystemExit) as exc:
        py_refs.main()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "real" in captured.out.splitlines()
    assert "No such file" in captured.err


def test_main_directory_arg_reports_error(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("sys.argv", ["py-refs", str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        py_refs.main()
    assert exc.value.code == 1
    assert "Is a directory" in capsys.readouterr().err


def test_main_binary_file_reports_error(monkeypatch, capsys, tmp_path):
    blob = tmp_path / "blob.py"
    blob.write_bytes(b"\xff\xfes = 1")
    monkeypatch.setattr("sys.argv", ["py-refs", str(blob)])
    with pytest.raises(SystemExit) as exc:
        py_refs.main()
    assert exc.value.code == 1
    assert "Not valid UTF-8" in capsys.readouterr().err


def test_main_generic_oserror_reports_message(monkeypatch, capsys, tmp_path):
    target = tmp_path / "blocked.py"
    target.write_text('s = "x"\n')

    # An OSError carrying no errno has strerror=None; the message must still
    # be reported (str(exc)), never the literal "None".
    def boom(*args, **kwargs):
        raise OSError("simulated read failure")

    monkeypatch.setattr("builtins.open", boom)
    monkeypatch.setattr("sys.argv", ["py-refs", str(target)])
    with pytest.raises(SystemExit) as exc:
        py_refs.main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "simulated read failure" in err
    assert "None" not in err
