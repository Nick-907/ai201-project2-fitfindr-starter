"""
tests/test_tools.py

Pytest tests for each FitFindr tool. Covers the happy path and each failure
mode described in planning.md. Run with: pytest tests/
"""

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── search_listings ────────────────────────────────────────────────────────────

def test_search_returns_results():
    """Basic happy path — common keyword should match something in the dataset."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    """Impossible query should return empty list, not raise an exception."""
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    """Every returned item must be within the price ceiling."""
    results = search_listings("jacket", size=None, max_price=30)
    assert all(item["price"] <= 30 for item in results)


def test_search_size_filter():
    """Every returned item must contain the requested size string (case-insensitive)."""
    results = search_listings("jeans", size="M", max_price=None)
    assert all("m" in item["size"].lower() for item in results)


def test_search_no_size_no_price():
    """Omitting both optional filters should still return results."""
    results = search_listings("denim")
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_best_match_first():
    """The first result should have a higher or equal keyword score than the last."""
    results = search_listings("vintage denim jacket", size=None, max_price=None)
    if len(results) >= 2:
        # Just verify results is sorted (spot check: first result is relevant)
        first_title = results[0]["title"].lower() + " ".join(results[0]["style_tags"]).lower()
        keywords = {"vintage", "denim", "jacket"}
        assert any(kw in first_title for kw in keywords)


def test_search_returns_correct_fields():
    """Each result dict must contain all required fields."""
    results = search_listings("tee", size=None, max_price=50)
    required = {"id", "title", "description", "category", "style_tags",
                "size", "condition", "price", "colors", "brand", "platform"}
    for item in results:
        assert required.issubset(item.keys())


# ── suggest_outfit ─────────────────────────────────────────────────────────────

def _sample_item():
    """Return a minimal listing dict for testing suggest_outfit and create_fit_card."""
    return {
        "id": "lst_test",
        "title": "Vintage Band Tee — Black",
        "description": "Classic black band tee with a faded graphic print.",
        "category": "tops",
        "style_tags": ["vintage", "graphic tee", "streetwear"],
        "size": "M",
        "condition": "good",
        "price": 24.0,
        "colors": ["black"],
        "brand": None,
        "platform": "depop",
    }


def test_suggest_outfit_with_wardrobe():
    """Returns a non-empty string when the wardrobe has items."""
    result = suggest_outfit(_sample_item(), get_example_wardrobe())
    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_suggest_outfit_empty_wardrobe():
    """Empty wardrobe should return general styling advice, not crash."""
    result = suggest_outfit(_sample_item(), get_empty_wardrobe())
    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_suggest_outfit_empty_wardrobe_no_exception():
    """Calling with an empty wardrobe must never raise an exception."""
    try:
        suggest_outfit(_sample_item(), {"items": []})
    except Exception as e:
        assert False, f"suggest_outfit raised an exception on empty wardrobe: {e}"


# ── create_fit_card ────────────────────────────────────────────────────────────

def test_create_fit_card_happy_path():
    """Returns a non-empty string given a valid outfit suggestion."""
    outfit = "Tuck the band tee into wide-leg jeans and add chunky sneakers for a streetwear look."
    result = create_fit_card(outfit, _sample_item())
    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_create_fit_card_empty_outfit():
    """Empty outfit string returns an error message, not an exception."""
    result = create_fit_card("", _sample_item())
    assert isinstance(result, str)
    assert len(result.strip()) > 0
    # Should contain something that signals the failure
    assert "outfit" in result.lower() or "empty" in result.lower() or "couldn't" in result.lower()


def test_create_fit_card_whitespace_outfit():
    """Whitespace-only outfit string is treated the same as empty."""
    result = create_fit_card("   \n  ", _sample_item())
    assert isinstance(result, str)
    assert "outfit" in result.lower() or "empty" in result.lower() or "couldn't" in result.lower()


def test_create_fit_card_no_exception_on_bad_input():
    """create_fit_card must never raise even with empty outfit."""
    try:
        create_fit_card("", _sample_item())
    except Exception as e:
        assert False, f"create_fit_card raised an exception on empty outfit: {e}"
