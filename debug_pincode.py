"""
debug_pincode.py — Step-by-step pincode + scroll debug with screenshots.
Run: python3 debug_pincode.py
"""
from playwright.sync_api import sync_playwright
import time

URL = "https://shop.amul.com/en/browse/protein"
PINCODE = "411057"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    page = ctx.new_page()

    # ── 1. Load page ──────────────────────────────
    print("1. Loading page …")
    page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
    time.sleep(4)
    page.screenshot(path="dbg_01_loaded.png")
    count = len(page.query_selector_all(".product-grid-item"))
    print(f"   Products visible: {count}")
    body = page.inner_text("body")
    showing_line = [l for l in body.splitlines() if "Showing" in l]
    print(f"   '{showing_line[0] if showing_line else 'N/A'}'")

    # ── 2. Click pincode trigger ──────────────────
    print("\n2. Clicking pincode trigger …")
    try:
        trigger = page.wait_for_selector("div.pincode_wrap", timeout=8_000)
        trigger.click()
        time.sleep(2)
        page.screenshot(path="dbg_02_after_pincode_click.png")

        # capture all inputs visible
        inputs = page.query_selector_all("input:visible")
        print(f"   Visible inputs after click: {len(inputs)}")
        for inp in inputs:
            print(f"     id={inp.get_attribute('id')!r}  placeholder={inp.get_attribute('placeholder')!r}  class={inp.get_attribute('class')!r}")

        # Look for any modal becoming visible
        modals = page.query_selector_all("[class*='modal']")
        print(f"   Modal elements: {len(modals)}")
        for m in modals:
            vis = m.is_visible()
            mid = repr(m.get_attribute('id'))
            mcls = repr((m.get_attribute('class') or '')[:60])
            print(f"     {mid} / {mcls}  visible={vis}")

    except Exception as e:
        print(f"   ERROR clicking pincode: {e}")

    # ── 3. Try typing in any visible input ────────
    print("\n3. Trying to enter pincode …")
    # Try common pincode input selectors
    pincode_selectors = [
        "input#search",
        "input[placeholder*='incode']",
        "input[placeholder*='PIN']",
        "input[placeholder*='pin']",
        "#locationWidgetModal input",
        ".modal.show input",
        ".modal-body input",
    ]
    typed = False
    for sel in pincode_selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                print(f"   Found input: {sel!r}")
                el.fill(PINCODE)
                time.sleep(2)
                page.screenshot(path="dbg_03_typed_pincode.png")
                # Look for suggestions
                sug = page.query_selector_all("a.searchitem-name, .search-item, li.suggestion-item, .dropdown-item")
                print(f"   Suggestions found: {len(sug)}")
                for s in sug[:5]:
                    print(f"     {s.inner_text()[:80]!r}")
                typed = True
                break
        except Exception as e:
            pass

    if not typed:
        print("   Could not find pincode input — dumping full HTML after click")
        with open("dbg_after_click.html", "w") as f:
            f.write(page.content())
        print("   Saved → dbg_after_click.html")

    # ── 4. Scroll test ────────────────────────────
    print("\n4. Testing infinite scroll …")
    # Scroll back to top first
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(1)

    for i in range(15):
        prev = len(page.query_selector_all(".product-grid-item"))
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
        curr = len(page.query_selector_all(".product-grid-item"))
        print(f"   Scroll {i+1}: {prev} → {curr} cards")
        if curr == prev and i > 2:
            break

    page.screenshot(path="dbg_04_after_scroll.png", full_page=True)
    final_count = len(page.query_selector_all(".product-grid-item"))
    print(f"\n   Final product count: {final_count}")

    browser.close()
    print("\nScreenshots saved: dbg_01..04.png")
