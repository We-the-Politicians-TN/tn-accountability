"""The language rules are enforced at build time; these pin the exemption's edges."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tn_accountability.language import check_text


def test_forbidden_words_in_our_prose_fail():
    assert check_text("<p>This member is corrupt.</p>", "t")


def test_verbatim_exemption_spans_nested_elements():
    # A filer's declared client interest, quoted as filed inside a verbatim list.
    html = ('<ul class="verbatim"><li>Law, GENERAL, CIVIL &amp; CRIMINAL LITIGATION</li>'
            '<li>Accounting</li></ul>')
    assert check_text(html, "t") == []


def test_forbidden_word_outside_verbatim_still_fails():
    html = '<ul class="verbatim"><li>Law</li></ul><p>a criminal enterprise</p>'
    assert check_text(html, "t")
