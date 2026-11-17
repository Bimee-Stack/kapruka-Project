"""
Part 1: Kapruka Playwright Crawler
----------------------------------
Goal: visit kapruka.com with a headless browser and save products to data/catalog.json

How it works (2 steps):
  Step A: open each CATEGORY page, scroll down / click "next" to load everything,
          and collect all product links.
  Step B: open each PRODUCT page and extract name, price, description, availability.

Run it:
  pip install playwright
  playwright install chromium
  python crawler.py            # normal run
  python crawler.py --debug    # opens a visible browser + saves screenshots
"""

import json
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ---------------------------------------------------------------
# SETTINGS (change these, not the code below)
# ---------------------------------------------------------------
BASE = "https://www.kapruka.com"

# Category pages to crawl. Add more (flowers, chocolates, fruit baskets...)
# by opening the category on kapruka.com and copying its URL.
CATEGORY_URLS = [
    f"{BASE}/lk/online/cakes/price/ramada",
    f"{BASE}/lk/online/cakes/price/cinnamon_grand/lanka/general",
    f"{BASE}/lk/online/cakes/price/sponge/lanka/general",
]

MAX_PRODUCTS_PER_CATEGORY = 40     # keep small while testing
OUTPUT_FILE = Path("data/catalog.json")
DEBUG = "--debug" in sys.argv

# Several possible CSS selectors per field. The crawler tries them in order
# and uses the first one that finds text. If Kapruka changes its layout,
# just add a new selector to the list.
NAME_SELECTORS = ["h1", "[itemprop='name']", ".product-title"]
PRICE_SELECTORS = ["[itemprop='price']", ".price", ".product-price", "[class*='price']"]
DESC_SELECTORS = ["[itemprop='description']", ".product-description",
                  "#description", "[class*='description']"]


# ---------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------
def first_text(page, selectors):
    """Try each selector in order; return the first non-empty text, else ''."""
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el:
                text = el.inner_text().strip()
                if text:
                    return text
        except Exception:
            continue
    return ""


def parse_price(raw):
    """'RS.3,780' -> (3780.0, 'LKR');  'US$14.00' -> (14.0, 'USD')"""
    if not raw:
        return None, None
    match = re.search(r"[\d,]+(?:\.\d+)?", raw)
    if not match:
        return None, None
    amount = float(match.group().replace(",", ""))
    currency = "USD" if "US" in raw.upper() and "$" in raw else "LKR"
    return amount, currency


def detect_availability(page):
    """Return 'out_of_stock' if the page says so, else 'in_stock' if it
    has a buy button, else 'unknown'."""
    body = page.inner_text("body").lower()
    if any(w in body for w in ["out of stock", "sold out", "currently unavailable"]):
        return "out_of_stock"
    if page.query_selector("button:has-text('Buy'), button:has-text('Add to'), "
                           "a:has-text('Buy Now'), input[value*='Buy' i]"):
        return "in_stock"
    return "unknown"


def load_everything(page):
    """Handle DYNAMIC LOADING and PAGINATION on a category page.
    1. Scroll down until no new product links appear (infinite scroll).
    2. If there is a 'Next' / 'Load more' button, click it and repeat."""
    link_sel = "a[href*='/buyonline/']"
    for _ in range(15):                      # safety limit: 15 rounds
        before = len(page.query_selector_all(link_sel))
        page.mouse.wheel(0, 5000)            # scroll down
        page.wait_for_timeout(1200)          # let new items load

        button = page.query_selector(
            "a:has-text('Next'), button:has-text('Load more'), "
            "button:has-text('Show more'), a[rel='next']")
        if button:
            try:
                button.click()
                page.wait_for_timeout(1500)
            except Exception:
                pass

        after = len(page.query_selector_all(link_sel))
        if after == before:                  # nothing new -> we are done
            break


# ---------------------------------------------------------------
# STEP A: collect product links from a category page
# ---------------------------------------------------------------
def collect_product_links(page, category_url):
    print(f"[category] {category_url}")
    try:
        page.goto(category_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)
    except PWTimeout:
        print("  ! timed out, skipping")
        return []

    load_everything(page)
    if DEBUG:
        page.screenshot(path="debug_category.png", full_page=True)

    hrefs = page.eval_on_selector_all(
        "a[href*='/buyonline/']", "els => els.map(e => e.href)")
    links = list(dict.fromkeys(hrefs))       # remove duplicates, keep order
    print(f"  found {len(links)} product links")
    return links[:MAX_PRODUCTS_PER_CATEGORY]


# ---------------------------------------------------------------
# STEP B: extract one product
# ---------------------------------------------------------------
def scrape_product(page, url, category):
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(1500)

    name = first_text(page, NAME_SELECTORS)
    price_raw = first_text(page, PRICE_SELECTORS)
    price, currency = parse_price(price_raw)

    return {
        "product_id": url.rstrip("/").split("/")[-1],   # e.g. cake00ka002008
        "name": name,
        "price": price,
        "currency": currency,
        "description": first_text(page, DESC_SELECTORS),
        "availability": detect_availability(page),
        "category": category,
        "url": url,
    }


# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------
def main():
    products, attempted, failed = [], 0, 0
    seen = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not DEBUG)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (compatible; ZuuCrew-StudentProject/1.0)")
        page = context.new_page()

        for cat_url in CATEGORY_URLS:
            category = cat_url.split("/price/")[-1].split("/")[0] if "/price/" in cat_url else "general"
            for link in collect_product_links(page, cat_url):
                if link in seen:
                    continue
                seen.add(link)
                attempted += 1
                try:
                    item = scrape_product(page, link, category)
                    if item["name"] and item["price"] is not None:
                        products.append(item)
                        print(f"  ok  {item['name']} | {item['price']} {item['currency']}")
                    else:
                        failed += 1
                        print(f"  ??  missing fields: {link}")
                except Exception as e:
                    failed += 1
                    print(f"  ERR {link}: {e}")
                time.sleep(1)                # be polite: 1 second between requests

        browser.close()

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")

    # Numbers you can use for Part 5 (crawl success metric)
    rate = (len(products) / attempted * 100) if attempted else 0
    print(f"\nSaved {len(products)} products -> {OUTPUT_FILE}")
    print(f"Crawl success rate: {rate:.1f}% ({len(products)}/{attempted}), failures: {failed}")


if __name__ == "__main__":
    main()
