"""
debug_page.py — Saves rendered HTML + screenshot so we can find real selectors.
Run: python3 debug_page.py
"""
from playwright.sync_api import sync_playwright
import time

URL = "https://shop.amul.com/en/browse/protein"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    page = context.new_page()

    print(f"Navigating to {URL} ...")
    page.goto(URL, wait_until="domcontentloaded", timeout=60_000)

    print("Waiting 8 seconds for JS to render ...")
    time.sleep(8)

    # Screenshot
    page.screenshot(path="debug_screenshot.png", full_page=True)
    print("Screenshot saved → debug_screenshot.png")

    # Save full HTML
    html = page.content()
    with open("debug_page.html", "w") as f:
        f.write(html)
    print(f"HTML saved → debug_page.html  ({len(html):,} bytes)")

    # Try to find common product-related elements and report counts
    selectors_to_try = [
        "div.product_item",
        ".product-item",
        ".product_card",
        ".product-card",
        "[class*='product']",
        "article",
        ".grid-item",
        ".collection-grid-item",
        "li.grid__item",
        ".snize-product",
        "[data-product-id]",
        ".boost-sd__product-item",
        ".item",
    ]
    print("\n--- Selector probe ---")
    for sel in selectors_to_try:
        count = len(page.query_selector_all(sel))
        if count > 0:
            print(f"  ✅  {sel!r:<40}  → {count} elements")
        else:
            print(f"  ❌  {sel!r:<40}  → 0")

    # Print first 300 chars of body text to see if products loaded
    body_text = page.inner_text("body")[:800]
    print("\n--- Page body text (first 800 chars) ---")
    print(body_text)

    browser.close()

print("\nDone. Open debug_screenshot.png to see what the page looks like.")
