import sys, asyncio
from playwright.sync_api import sync_playwright

# Ensure Windows works
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def scrape_tiktok(limit=10):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.tiktok.com/trending")
        tags = page.eval_on_selector_all(
            "a[data-e2e='trend-item-text']",
            "els => els.map(e => e.innerText)"
        )
        browser.close()
    return tags[:limit]
