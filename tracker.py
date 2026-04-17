"""
tracker.py — Playwright-based product scraper.

Supports:
  - Amul Shop (type: amul): sets pincode via modal, handles infinite scroll
  - Generic (type: generic): configurable selectors for other sites
"""

import logging
import time
from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Public entry point
# ─────────────────────────────────────────────

def scrape_website(website_config: dict) -> list[dict]:
    """
    Scrape a configured website and return a list of products.

    Each product dict:
        { "name": str, "status": "AVAILABLE" | "SOLD OUT", "price": str }
    """
    site_type = website_config.get("type", "generic")

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
        # silence browser console noise
        page.on("console", lambda _: None)

        try:
            if site_type == "amul":
                products = _scrape_amul(page, website_config)
            else:
                products = _scrape_generic(page, website_config)
        except Exception as exc:
            logger.error("Scrape failed for %s: %s", website_config["name"], exc, exc_info=True)
            products = []
        finally:
            browser.close()

    return products


# ─────────────────────────────────────────────
#  Amul scraper
# ─────────────────────────────────────────────

def _scrape_amul(page: Page, cfg: dict) -> list[dict]:
    url     = cfg["url"]
    pincode = cfg.get("pincode", "")

    logger.info("Navigating to %s", url)
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    time.sleep(3)  # let initial JS render

    # ── Set pincode ───────────────────────────
    if pincode:
        _set_amul_pincode(page, pincode)

    # ── Wait for at least one product card ────
    logger.info("Waiting for product cards …")
    try:
        page.wait_for_selector(".product-grid-item", timeout=30_000)
    except PWTimeout:
        logger.warning("No product cards found within timeout.")
        return []

    # ── Scroll to trigger infinite-scroll load ─
    logger.info("Scrolling to load all products …")
    _scroll_to_load_all(page, card_selector=".product-grid-item")

    # ── Extract all cards ─────────────────────
    cards = page.query_selector_all(".product-grid-item")
    logger.info("Found %d product cards", len(cards))

    products = []
    for card in cards:
        name   = _amul_name(card)
        price  = _amul_price(card)
        status = _amul_status(card)
        if name:
            products.append({"name": name, "status": status, "price": price})
            logger.debug("  [%s] %s", status, name)

    return products


def _set_amul_pincode(page: Page, pincode: str) -> None:
    """
    Set the Amul delivery pincode.

    The site auto-opens #locationWidgetModal when no pincode is stored.
    If it's already open, we skip clicking the trigger and type directly.
    If it's not open, we click the trigger first.
    """
    logger.info("Setting pincode: %s", pincode)
    try:
        # Check if modal is already visible (auto-opens on first visit)
        modal_visible = False
        try:
            modal = page.wait_for_selector(
                "#locationWidgetModal.show, #locationWidgetModal[aria-modal='true']",
                timeout=4_000
            )
            if modal and modal.is_visible():
                modal_visible = True
                logger.info("Pincode modal already open (auto-triggered).")
        except PWTimeout:
            pass

        # If not open, click the header trigger to open it
        if not modal_visible:
            trigger = page.wait_for_selector("div.pincode_wrap", timeout=8_000)
            page.evaluate("document.querySelector('div.pincode_wrap').click()")
            time.sleep(1.5)

        # The pincode search input is input#search (inside the modal)
        inp = page.wait_for_selector("input#search", state="visible", timeout=8_000)
        inp.click()
        inp.fill("")
        inp.type(pincode, delay=60)
        time.sleep(2)  # wait for AJAX suggestions

        # Click the suggestion that matches the pincode
        # Suggestions appear as <a class="searchitem-name"> inside modal
        suggestions = page.query_selector_all(
            "a.searchitem-name, "
            "#locationWidgetModal .search-item, "
            "#locationWidgetModal li"
        )
        clicked = False
        for s in suggestions:
            text = (s.inner_text() or "").strip()
            if pincode in text:
                s.click()
                clicked = True
                logger.info("Clicked suggestion: %r", text)
                break

        if not clicked and suggestions:
            # Pick the last suggestion (pincode results usually appear last)
            suggestions[-1].click()
            clicked = True
            logger.info("Clicked last suggestion (fallback).")

        if clicked:
            time.sleep(4)  # Wait for page to reload with pincode-specific stock
            logger.info("Pincode %s set ✅", pincode)
        else:
            logger.warning("No pincode suggestions appeared — proceeding without pincode.")

    except PWTimeout as e:
        logger.warning("Pincode setup timed out: %s", e)
    except Exception as exc:
        logger.warning("Pincode setup error: %s", exc)


def _scroll_to_load_all(page: Page, card_selector: str, max_scrolls: int = 25) -> None:
    """
    Gradually scroll the page to trigger intersection-observer-based infinite scroll.
    Scrolls in viewport-height increments rather than jumping to the bottom.
    """
    step = 600  # px per scroll step
    position = 0
    prev_count = len(page.query_selector_all(card_selector))
    stable_rounds = 0

    for i in range(max_scrolls):
        position += step
        page.evaluate(f"window.scrollTo(0, {position})")
        time.sleep(1.8)

        count = len(page.query_selector_all(card_selector))
        logger.debug("  Scroll step %d (y=%d): %d cards", i + 1, position, count)

        if count > prev_count:
            stable_rounds = 0  # reset — still loading
            prev_count = count
        else:
            stable_rounds += 1
            # If body height grew, keep scrolling even without new cards yet
            body_h = page.evaluate("document.body.scrollHeight")
            if position >= body_h:
                break  # reached page bottom
            if stable_rounds >= 3:
                break  # 3 rounds with no new cards → done

    logger.info("Scrolling done — %d cards loaded.", prev_count)



def _amul_name(card) -> str:
    """Product name from card."""
    # Primary: the bold anchor
    el = card.query_selector("a.lh-sm.m-0.d-block.fw-semibold.text-dark")
    if el:
        return (el.inner_text() or "").strip()
    # Fallback: anchor with title
    el = card.query_selector("a[title]")
    if el:
        return (el.get_attribute("title") or "").strip()
    # Fallback: product-grid-name div
    el = card.query_selector(".product-grid-name")
    if el:
        return (el.inner_text() or "").strip()
    return ""


def _amul_price(card) -> str:
    """Price string from card."""
    el = card.query_selector(".product-grid-price")
    if el:
        text = (el.inner_text() or "").strip().replace("\n", " ")
        return text
    return ""


def _amul_status(card) -> str:
    """
    Determine availability.

    Available signals:
      - SOLD OUT  → 'stock-indicator' element present in card
      - SOLD OUT  → mobile-btn with title 'Notify Me'
      - SOLD OUT  → mobile-btn with title 'Sold Out' or text contains 'sold'
      - AVAILABLE → mobile-btn with title 'Add to Cart'
    """
    # Strongest sold-out signal
    if card.query_selector("a.stock-indicator, .stock-indicator"):
        return "SOLD OUT"

    # Check the mobile-btn title
    btn = card.query_selector("a.mobile-btn")
    if btn:
        title = (btn.get_attribute("title") or "").lower()
        text  = (btn.inner_text() or "").lower().strip()
        if "notify" in title or "sold" in title or "sold" in text or "out of stock" in text:
            return "SOLD OUT"
        if "add" in title or "add" in text:
            return "AVAILABLE"

    # Fallback: scan card text
    card_text = (card.inner_text() or "").lower()
    if "sold out" in card_text or "notify me" in card_text:
        return "SOLD OUT"

    return "AVAILABLE"


# ─────────────────────────────────────────────
#  Generic scraper (hook for future websites)
# ─────────────────────────────────────────────

def _scrape_generic(page: Page, cfg: dict) -> list[dict]:
    """
    Minimal generic scraper driven by config selectors.

    Config keys used:
        product_selector  : CSS for each product card
        name_selector     : CSS (relative to card) for product name
        soldout_selector  : CSS (relative to card) present when sold out
        soldout_text      : text in card when sold out  (default 'sold out')
    """
    url = cfg["url"]
    logger.info("Generic scrape: %s", url)
    page.goto(url, wait_until="networkidle", timeout=60_000)
    time.sleep(2)

    product_sel  = cfg.get("product_selector",  ".product")
    name_sel     = cfg.get("name_selector",      "h2, h3, .name")
    soldout_sel  = cfg.get("soldout_selector",   ".sold-out, .out-of-stock")
    soldout_text = cfg.get("soldout_text",       "sold out").lower()

    try:
        page.wait_for_selector(product_sel, timeout=20_000)
    except PWTimeout:
        return []

    products = []
    for card in page.query_selector_all(product_sel):
        name_el = card.query_selector(name_sel)
        name    = ((name_el.inner_text() if name_el else "") or "").strip()
        if not name:
            continue
        is_soldout = (
            card.query_selector(soldout_sel) is not None
            or soldout_text in (card.inner_text() or "").lower()
        )
        products.append({
            "name":   name,
            "status": "SOLD OUT" if is_soldout else "AVAILABLE",
            "price":  "",
        })
    return products
