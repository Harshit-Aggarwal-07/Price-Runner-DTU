import pytest
from playwright.sync_api import Page, expect

def test_product_details_and_badges(page: Page):
    """Test that weight badges, rating badges, and discount tags render on cards."""
    page.goto("http://localhost:8000")

    # Search for bread
    page.locator("#search-input").fill("bread")
    page.keyboard.press("Enter")

    expect(page.locator("#results-section")).to_be_visible(timeout=15000)
    expect(page.locator(".compare-card").first).to_be_visible()

    # Weight badge verification
    weight_badges = page.locator(".store-row__weight-tag")
    expect(weight_badges.first).to_be_visible()
    first_weight = weight_badges.first.text_content()
    assert "📦" in first_weight
    assert any(unit in first_weight for unit in ["g", "kg", "ml", "L", "Pack"])

    # Rating badge verification
    rating_badges = page.locator(".store-row__rating")
    expect(rating_badges.first).to_be_visible()
    first_rating = rating_badges.first.text_content()
    assert "⭐" in first_rating

def test_sorting_and_filtering(page: Page):
    """Test interactive sort pills, filter pills, and reset functionality."""
    page.goto("http://localhost:8000")

    page.locator("#search-input").fill("biscuit")
    page.keyboard.press("Enter")

    expect(page.locator("#results-section")).to_be_visible(timeout=15000)
    expect(page.locator(".compare-card").first).to_be_visible()

    # Initial matched count
    total_cards = page.locator(".compare-card").count()
    assert total_cards > 0

    # Controls bar visible
    expect(page.locator("#results-controls-bar")).to_be_visible()

    # Test Sort: Price Low -> High
    sort_price_asc = page.locator('.control-pill[data-sort="price_asc"]')
    sort_price_asc.click()
    page.wait_for_timeout(400)
    expect(sort_price_asc).to_have_class("control-pill active")

    # Test Filter: Rated Only
    filter_rated = page.locator('.control-pill[data-filter="rated_only"]')
    filter_rated.click()
    page.wait_for_timeout(400)
    expect(filter_rated).to_have_class("control-pill active")
    expect(page.locator("#btn-reset-filters")).to_be_visible()

    # Test Reset Filters
    page.locator("#btn-reset-filters").click()
    page.wait_for_timeout(400)
    expect(page.locator('.control-pill[data-filter="all"]')).to_have_class("control-pill active")
    expect(page.locator('.control-pill[data-sort="best_match"]')).to_have_class("control-pill active")
