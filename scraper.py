from playwright.sync_api import sync_playwright

def scrape_tiktok():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("https://www.tiktok.com/trending")
        tags = page.eval_on_selector_all("a.trending-hashtag", "els => els.map(e => e.innerText)")
        browser.close()
    return tags[:10]  # top 10
