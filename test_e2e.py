import pytest
from playwright.sync_api import Page, expect

# Ensure the FastAPI server is running before running this test

def test_homepage_loads(page: Page):
    """Test that the homepage loads and the basic UI elements are present."""
    page.goto("http://localhost:8000")
    
    # Check title and hero text
    expect(page).to_have_title("PriceRunner DTU — Grocery Price Comparison")
    expect(page.locator("h2.hero__heading")).to_contain_text("Find the Best Deal Near DTU")
    expect(page.locator("#search-input")).to_be_visible()

def test_search_and_cart_flow(page: Page):
    """Test the search and cart optimization flow."""
    page.goto("http://localhost:8000")
    
    # Perform search for maggi
    page.locator("#search-input").fill("maggi")
    page.keyboard.press("Enter")
    
    # Wait for the results section to appear
    expect(page.locator("#results-section")).to_be_visible(timeout=10000)
    
    # Expect matched items to be populated
    expect(page.locator(".compare-card").first).to_be_visible()
    
    # Add first item to cart
    first_add_btn = page.locator(".add-to-cart-btn").first
    first_add_btn.click()
    
    # Verify cart badge updated
    expect(page.locator("#cart-count")).to_have_text("1")
    
    # Adding to cart automatically opens the cart sidebar
    expect(page.locator("#cart-sidebar")).to_have_class("cart-sidebar open")
    
    # Check cart item is present
    expect(page.locator(".cart-item")).to_have_count(1)
    
    # Click optimize
    page.locator("#optimize-btn").click()
    
    # Wait for optimization result
    expect(page.locator(".cart-result")).to_be_visible(timeout=5000)
    expect(page.locator(".cart-result__title")).to_contain_text("Cart Optimization")
    expect(page.locator(".cart-result__recommendation")).to_be_visible()
