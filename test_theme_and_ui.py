import pytest
from playwright.sync_api import Page, expect

def test_theme_toggle_and_persistence(page: Page):
    """Test default light theme, toggle to dark, and localStorage persistence."""
    page.goto("http://localhost:8000")
    
    # Verify default light theme
    html = page.locator("html")
    expect(html).to_have_attribute("data-theme", "light")
    
    # Theme button starts showing Dark option
    theme_btn = page.locator("#theme-toggle-btn")
    expect(theme_btn).to_be_visible()
    expect(page.locator("#theme-toggle-label")).to_have_text("Dark")
    
    # Click to toggle to Dark theme
    theme_btn.click()
    expect(html).to_have_attribute("data-theme", "dark")
    expect(page.locator("#theme-toggle-label")).to_have_text("Light")
    
    # Reload page and ensure dark theme persisted
    page.reload()
    expect(html).to_have_attribute("data-theme", "dark")
    
    # Toggle back to light theme
    page.locator("#theme-toggle-btn").click()
    expect(html).to_have_attribute("data-theme", "light")

def test_lovable_ui_elements_and_filters(page: Page):
    """Test Lovable UI elements, quick tags, trust cards, and store filter tabs."""
    page.goto("http://localhost:8000")
    
    # Verify header campus location badge
    expect(page.locator("#header-location")).to_contain_text("DTU North Campus")
    
    # Click on quick tag 'milk'
    page.locator('.tag[data-query="milk"]').click()
    
    # Wait for results
    expect(page.locator("#results-section")).to_be_visible(timeout=10000)
    expect(page.locator("#status-bar")).to_be_visible()
    expect(page.locator("#status-bar")).to_contain_text("Live catalogue snapshot")
    
    # Matched comparison cards should appear
    cards = page.locator(".compare-card")
    expect(cards.first).to_be_visible()
    
    # Verify card elements (avatar, store rows with Blinkit & Instamart)
    first_card = cards.first
    expect(first_card.locator(".compare-card__header")).to_be_visible()
    expect(first_card.locator(".store-row")).to_have_count(2)
    
    # Test store filter tabs (Both, Blinkit, Instamart)
    store_filter = page.locator("#store-filter")
    expect(store_filter).to_be_visible()
    
    # Click Blinkit tab
    page.locator('.filter-tab[data-store="blinkit"]').click()
    # Cards with Blinkit should be visible
    expect(first_card).to_be_visible()
    
    # Click Both tab
    page.locator('.filter-tab[data-store="all"]').click()
    expect(first_card).to_be_visible()
    
    # Verify trust modules below results
    expect(page.locator("#trust-grid")).to_be_visible()
    expect(page.locator("#trust-grid")).to_contain_text("How we decide it’s the same product")
    expect(page.locator("#trust-grid")).to_contain_text("Built for a quick decision")

def test_take_to_home(page: Page):
    """Test that clicking the header brand logo resets to the home state."""
    page.goto("http://localhost:8000")
    
    # Perform search
    page.locator('.tag[data-query="maggi"]').click()
    expect(page.locator("#results-section")).to_be_visible(timeout=10000)
    expect(page.locator("#hero-section")).to_have_class("hero page-grid hero--collapsed")
    
    # Click on the header brand logo
    page.locator("#header-brand-home").click()
    
    # Hero should expand back and results should hide
    expect(page.locator("#hero-section")).not_to_have_class("hero page-grid hero--collapsed")
    expect(page.locator("#results-section")).not_to_be_visible()
    expect(page.locator("#status-bar")).not_to_be_visible()
    expect(page.locator("#search-input")).to_have_value("")

def test_footer_stack_and_collapse(page: Page):
    """Test that the footer is stacked at bottom and collapsed by default, and expands on toggle."""
    page.goto("http://localhost:8000")
    
    footer = page.locator("#main-footer")
    expect(footer).to_be_visible()
    
    # Verify footer is collapsed by default
    details = page.locator("#footer-details")
    expect(details).not_to_be_visible()
    
    toggle_btn = page.locator("#footer-toggle-btn")
    expect(toggle_btn).to_be_visible()
    expect(page.locator("#footer-toggle-text")).to_have_text("Info & Disclaimer")
    
    # Click to expand
    toggle_btn.click()
    expect(details).to_be_visible()
    expect(page.locator("#footer-toggle-text")).to_have_text("Hide")
    expect(details).to_contain_text("Prototype catalogue comparison for assignment demo")
    
    # Click to collapse again
    toggle_btn.click()
    expect(details).not_to_be_visible()
    expect(page.locator("#footer-toggle-text")).to_have_text("Info & Disclaimer")


