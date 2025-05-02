from playwright.sync_api import sync_playwright

# Script: take_map_screenshot.py
# Description: Navigates to a Google Maps URL and takes a screenshot saved as test.jpg

URL = "https://www.google.com/maps/place//@24.5161394,72.7879175,129m/data=!3m1!1e3?entry=ttu&g_ep=EgoyMDI1MDQyOS4wIKXMDSoASAFQAw%3D%3D"

def run():
    with sync_playwright() as p:
        # Launch headless Chromium
        browser = p.chromium.launch(headless=False)
        # Create a new page with a large viewport for maps
        page = browser.new_page(viewport={
            "width": 1920,
            "height": 1080
        })
        # Navigate to the Google Maps URL
        page.goto(URL)
        # Wait for the map canvas to render
        # The selector 'canvas' targets the map canvas layer
        page.wait_for_selector('id-app-container', timeout=15000)
        # Optionally wait a bit more for tiles to load
        page.wait_for_timeout(2000)
        # Take screenshot of the viewport
        page.screenshot(path='test.jpg', full_page=False)
        print("Screenshot saved to test.jpg")
        # Close browser
        browser.close()

if __name__ == '__main__':
    run()
