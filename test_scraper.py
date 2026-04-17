"""
test_scraper.py — Quickly test the scraper without email.
Run: python3 test_scraper.py
"""
import logging
import sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")

from tracker import scrape_website

site = {
    "name": "Amul Protein Shop",
    "url":  "https://shop.amul.com/en/browse/protein",
    "pincode": "411057",
    "type": "amul",
}

print("\n🔍  Scraping Amul Protein page for pincode 411057 …\n")
products = scrape_website(site)

if not products:
    print("❌  No products found — check selectors in tracker.py")
    sys.exit(1)

print(f"\n{'─'*70}")
print(f"  {'Product':<50}  {'Status':<12}  Price")
print(f"{'─'*70}")
for p in products:
    icon = "✅" if p["status"] == "AVAILABLE" else "❌"
    print(f"  {icon}  {p['name']:<48}  {p['status']:<12}  {p.get('price','')}")
print(f"{'─'*70}")
print(f"\nTotal: {len(products)} products found.\n")
