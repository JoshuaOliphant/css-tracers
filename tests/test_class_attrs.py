# ABOUTME: Tests for the shared class-attribute scanner.
# ABOUTME: Covers quoting styles, whitespace handling, and the malformed-input edges.

from tools import class_attrs


def test_double_quoted():
    assert class_attrs.scan_class_attrs('<div class="a b"></div>') == {"a", "b"}


def test_single_quoted():
    assert class_attrs.scan_class_attrs("<div class='c d'></div>") == {"c", "d"}


def test_both_quote_styles_in_one_text():
    text = '<div class="a"><span class=\'b\'></span></div>'
    assert class_attrs.scan_class_attrs(text) == {"a", "b"}


def test_multi_class_splits_on_any_whitespace():
    assert class_attrs.scan_class_attrs('<div class="  a   b\tc\nd  "></div>') == {"a", "b", "c", "d"}


def test_empty_attribute_yields_nothing():
    assert class_attrs.scan_class_attrs('<div class=""></div>') == set()
    assert class_attrs.scan_class_attrs("<div class=''></div>") == set()


def test_text_without_class_attribute():
    assert class_attrs.scan_class_attrs("<div id=\"main\">class of 99</div>") == set()


def test_unterminated_attribute_with_no_later_quote_yields_nothing():
    assert class_attrs.scan_class_attrs('<div class="growth-') == set()


def test_unterminated_attribute_pairs_with_the_next_quote():
    # The regex has no attribute boundary, so the value runs to the next quote
    # of the same style and drags the text between them in with it.
    text = '<div class="growth-\n<p>hello "world"</p>'
    assert class_attrs.scan_class_attrs(text) == {"growth-", "<p>hello"}


def test_class_matches_without_a_left_boundary():
    assert class_attrs.scan_class_attrs('<div superclass="leak">') == {"leak"}
    assert class_attrs.scan_class_attrs('<div data-class="leak">') == {"leak"}


def test_value_tokens_are_returned_verbatim():
    # py-refs hands over reconstructed f-strings, placeholders and all; the
    # scanner does not judge what a class name may look like.
    assert class_attrs.scan_class_attrs('<div class="growth-{...} card">') == {
        "growth-{...}",
        "card",
    }


def test_repeated_attributes_accumulate():
    text = '<a class="btn"></a><a class="btn wide"></a>'
    assert class_attrs.scan_class_attrs(text) == {"btn", "wide"}
