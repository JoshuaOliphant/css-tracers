# ABOUTME: Tests for the shared class-attribute scanner.
# ABOUTME: Covers both quoting styles, multi-class values, and empty attributes.

from tools.class_attrs import scan_class_attrs


def test_double_quoted():
    assert scan_class_attrs('<div class="a b"></div>') == {"a", "b"}


def test_single_quoted():
    assert scan_class_attrs("<div class='c d'></div>") == {"c", "d"}


def test_both_quote_styles_in_one_text():
    text = '<div class="a"><span class=\'b\'></span></div>'
    assert scan_class_attrs(text) == {"a", "b"}


def test_multi_class_collapses_whitespace():
    assert scan_class_attrs('<div class="  a   b\tc\nd  "></div>') == {"a", "b", "c", "d"}


def test_empty_attribute_yields_nothing():
    assert scan_class_attrs('<div class=""></div>') == set()
    assert scan_class_attrs("<div class=''></div>") == set()


def test_text_without_class_attribute():
    assert scan_class_attrs("<div id=\"main\">class of 99</div>") == set()


def test_unterminated_attribute_is_not_captured():
    assert scan_class_attrs('<div class="growth-') == set()


def test_repeated_attributes_accumulate():
    text = '<a class="btn"></a><a class="btn wide"></a>'
    assert scan_class_attrs(text) == {"btn", "wide"}
