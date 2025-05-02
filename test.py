import sys
import asyncio
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    """
    Synchronously visit TikTok homepage, scrape one post's details,
    then wait for user input before closing.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/112.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        page.add_init_script("""
            // Spoof plugins and languages
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US','en'] });
        """
        )

        # Navigate and wait for feed to load
        page.goto("https://www.tiktok.com", wait_until="networkidle")
        post = page.wait_for_selector("article[data-e2e='recommend-list-item-container']", timeout=20000)

        # Extract fields
        author = post.query_selector("[data-e2e='video-author-uniqueid']").inner_text().strip()
        description = post.query_selector("[data-e2e='video-desc']").inner_text().strip()
        likes = post.query_selector("[data-e2e='like-count']").inner_text().strip()
        comments = post.query_selector("[data-e2e='comment-count']").inner_text().strip()
        shares = post.query_selector("[data-e2e='share-count']").inner_text().strip()
        music = post.query_selector("[data-e2e='video-music']").get_attribute('href')

        # Thumbnail and video
        thumb = post.query_selector("picture img").get_attribute('src')
        video_el = post.query_selector("video")
        video_src = video_el.get_attribute('src') if video_el else None

        # Print results
        print("--- Scraped TikTok Post ---")
        print(f"Author     : {author}")
        print(f"Description: {description}")
        print(f"Likes      : {likes}")
        print(f"Comments   : {comments}")
        print(f"Shares     : {shares}")
        print(f"Music URL  : https://www.tiktok.com{music}" if music else "Music URL  : None")
        print(f"Thumbnail  : {thumb}")
        print(f"Video URL  : {video_src if video_src else '(dynamic blob URL)'}")
        
        input("\nPress Enter to exit and close browser...")
        browser.close()


if __name__ == "__main__":
    main()
