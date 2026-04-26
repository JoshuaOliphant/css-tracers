import pytest

from tools import js_refs


def extract(src):
    return js_refs.extract_classes(src.encode("utf-8"))


def test_extract_classes_from_string_double_and_single():
    assert js_refs.extract_classes_from_string('<div class="a b"></div>') == {"a", "b"}
    assert js_refs.extract_classes_from_string("<div class='c d'></div>") == {"c", "d"}


def test_extract_classes_from_classname_value_filters_js_artifacts():
    out = js_refs.extract_classes_from_classname_value("foo bar (something) +concat")
    assert out == {"foo", "bar"}


def test_extract_classes_from_classname_value_drops_empty():
    assert js_refs.extract_classes_from_classname_value("   ") == set()


def test_classname_assignment_string_literal():
    src = 'el.className = "alpha beta";'
    assert extract(src) == {"alpha", "beta"}


def test_classname_assignment_template_literal():
    src = 'el.className = `gamma delta`;'
    assert extract(src) == {"gamma", "delta"}


def test_classlist_add_remove_toggle_contains():
    src = (
        'el.classList.add("one");\n'
        'el.classList.remove("two");\n'
        'el.classList.toggle("three");\n'
        'el.classList.contains("four");\n'
    )
    assert extract(src) == {"one", "two", "three", "four"}


def test_classlist_other_method_ignored():
    src = 'el.classList.replace("a", "b");'
    # 'replace' is not in our allowlist, so neither argument is captured
    assert extract(src) == set()


def test_setattribute_class():
    src = 'el.setAttribute("class", "x y z");'
    assert extract(src) == {"x", "y", "z"}


def test_setattribute_other_attribute_ignored():
    src = 'el.setAttribute("id", "x y z");'
    assert extract(src) == set()


def test_setattribute_template_literal_first_arg_class():
    src = "el.setAttribute(`class`, `tpl-a tpl-b`);"
    assert extract(src) == {"tpl-a", "tpl-b"}


def test_setattribute_with_one_argument_ignored():
    src = 'el.setAttribute("class");'
    assert extract(src) == set()


def test_class_attribute_in_innerhtml_template_double_quoted():
    # Backtick template lets inner double-quoted class attributes survive
    # as a single string_fragment, exercising the double-quoted branch
    # in extract_classes_from_string.
    src = 'el.innerHTML = `<span class="hl">hi</span>`;'
    assert extract(src) == {"hl"}


def test_string_fragment_without_class_attribute_ignored():
    # A string_fragment that doesn't contain "class=" must skip the
    # extract path entirely.
    src = 'el.dataset.x = "no class here";'
    assert extract(src) == set()


def test_class_attribute_in_template_literal():
    src = "el.innerHTML = `<span class='tl'>hi</span>`;"
    assert extract(src) == {"tl"}


def test_assignment_to_non_classname_property_ignored():
    src = 'el.id = "not-a-class";'
    assert extract(src) == set()


def test_call_on_non_member_expression_ignored():
    # A bare function call has no member_expression function part.
    src = 'doStuff("foo");'
    assert extract(src) == set()


def test_call_member_object_not_member_expression_ignored():
    # `obj.add("foo")` - func is a member_expression but its object is just
    # an identifier, not a member_expression, so the classList branch fails.
    src = 'obj.add("nope");'
    assert extract(src) == set()


def test_classlist_with_this_object_is_supported():
    # `this.classList.add("foo")` - object is a member_expression
    # (this.classList), so this should be captured.
    src = 'this.classList.add("yep");'
    assert extract(src) == {"yep"}


def test_main_help(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["js-refs", "--help"])
    with pytest.raises(SystemExit) as exc:
        js_refs.main()
    assert exc.value.code == 0
    assert "js-refs" in capsys.readouterr().out


def test_main_short_help(monkeypatch):
    monkeypatch.setattr("sys.argv", ["js-refs", "-h"])
    with pytest.raises(SystemExit) as exc:
        js_refs.main()
    assert exc.value.code == 0


def test_main_no_args(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["js-refs"])
    with pytest.raises(SystemExit) as exc:
        js_refs.main()
    assert exc.value.code == 1
    assert "Usage" in capsys.readouterr().err


def test_main_missing_file(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("sys.argv", ["js-refs", str(tmp_path / "nope.js")])
    with pytest.raises(SystemExit) as exc:
        js_refs.main()
    assert exc.value.code == 1
    assert "No such file" in capsys.readouterr().err


def test_main_reads_and_prints(monkeypatch, capsys, tmp_path):
    f = tmp_path / "a.js"
    f.write_text('el.className = "z a m";')
    monkeypatch.setattr("sys.argv", ["js-refs", str(f)])
    js_refs.main()
    assert capsys.readouterr().out.splitlines() == ["a", "m", "z"]
