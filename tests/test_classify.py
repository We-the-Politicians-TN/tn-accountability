"""Regression tests for donor industry classification.

Every case here was a real misclassification found in production data. Prefix
matching is powerful and silently wrong when one industry's word is the start of
another's: HOSPITAL/HOSPITALITY put $184,500 of restaurant money into health care.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tn_accountability.classify import DONOR_RULES, first_match


def cat(name):
    return first_match(name, DONOR_RULES)[0]


def test_hospitality_is_not_healthcare():
    # The live bug: 14 donors, $184,500.
    for name in ["TENNESSEE HOSPITALITY PAC",
                 "TENNESSEE HOSPITALITY AND TOURISM - PAC",
                 "CUMBERLAND HOSPITALITY GROUP LLC",
                 "A. MARSHALL HOSPITALITY LLC"]:
        assert cat(name) == "hospitality", f"{name} -> {cat(name)}"


def test_nursery_is_not_healthcare():
    assert cat("CENTER HILL NURSERY LLC") != "healthcare"


def test_real_healthcare_still_matches():
    for name in ["TENNESSEE HOSPITAL ASSOCIATION",
                 "LIFEPOINT HEALTH PAC",
                 "TENNESSEE RADIOLOGISTS PAC",
                 "DELTA DENTAL OF TENNESSEE PAC",
                 "INDEPENDENT MEDICINE'S PAC-TN",
                 "TENNESSEE NURSING HOME PAC"]:
        assert cat(name) == "healthcare", f"{name} -> {cat(name)}"


def test_plural_and_truncated_forms_match():
    # \bBANK\b could not match BANKERS; the fix was prefix matching.
    assert cat("TENNESSEE BANKERS ASSN PAC") == "finance"
    assert cat("TENNESSEE REALTORS PAC") == "real_estate"
    assert cat("LAWYERS INVOLVED FOR TN") == "legal"


def test_unknown_names_stay_unmatched():
    assert cat("WSWT POLITICAL ACTION COMMITTEE") is None


def test_genuinely_ambiguous_names_are_not_asserted():
    """Some names have no single right answer and belong in human review.

    RYMAN HOSPITALITY PROPERTIES is a hotel REIT: 'hospitality' and 'real_estate'
    are both defensible, and the rules resolve it by ordering rather than judgement.
    The test records that it lands *somewhere* sensible, not which — the donor review
    file is where a person settles cases like this.
    """
    assert cat("RYMAN HOSPITALITY PROPERTIES PAC") in ("hospitality", "real_estate")


def test_retry_covers_server_errors():
    """HTTP 5xx must be retried; 4xx must not.

    2023's contributions failed twice because raise_for_status() was called OUTSIDE
    the retry wrapper, so a transient HTTP 500 was raised after _retrying had already
    returned and killed hours of work. Retrying a 4xx would be pointless — it means
    our request is wrong, not that the server stumbled.
    """
    import requests
    from tn_accountability.tref import TrefClient, TrefError

    client = TrefClient.__new__(TrefClient)  # no network setup needed

    calls = {"n": 0}

    def flaky_500():
        calls["n"] += 1
        if calls["n"] < 3:
            r = requests.Response()
            r.status_code = 500
            r.raise_for_status()
        return "recovered"

    assert client._retrying(flaky_500, "t", attempts=4) == "recovered"
    assert calls["n"] == 3

    def always_404():
        r = requests.Response()
        r.status_code = 404
        r.raise_for_status()

    try:
        client._retrying(always_404, "t", attempts=4)
        raise AssertionError("404 should not be retried")
    except requests.exceptions.HTTPError:
        pass  # correct: fails fast
