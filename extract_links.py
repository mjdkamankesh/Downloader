import asyncio
import re
import sys
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

from playwright.async_api import async_playwright

START_URL = sys.argv[1]
OUTPUT_FILE = "video_links.txt"

def page_url(base_url, page_number):
    parsed = urlparse(base_url)
    params = parse_qs(parsed.query)
    params["page"] = [str(page_number)]

    query = urlencode(params, doseq=True)

    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        query,
        parsed.fragment
    ))

async def main():
    all_links = set()
    max_page = 1

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        page = await browser.new_page()
        page.set_default_timeout(30000)

        # First page: discover pagination range
        print("Opening first page:", START_URL)

        await page.goto(
            START_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(4000)

        pagination_links = await page.locator("a[href]").evaluate_all("""
            elements => elements.map(a => a.href)
        """)

        for href in pagination_links:
            parsed = urlparse(href)
            params = parse_qs(parsed.query)

            if "page" in params:
                try:
                    number = int(params["page"][0])
                    max_page = max(max_page, number)
                except Exception:
                    pass

        print("Detected maximum page:", max_page)

        # Process every page
        empty_pages = 0

        for number in range(1, max_page + 1):
            url = page_url(START_URL, number)

            print(f"\\nProcessing page {number}/{max_page}")
            print(url)

            try:
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                await page.wait_for_timeout(3000)

                links = await page.locator(
                    "a.th.js-open-popup[href], a[href*='/video/']"
                ).evaluate_all("""
                    elements => elements.map(a => a.href)
                """)

                page_links = set()

                for link in links:
                    absolute = urljoin(url, link)

                    if "/video/" in absolute:
                        page_links.add(absolute.split("?")[0])

                before = len(all_links)
                all_links.update(page_links)
                added = len(all_links) - before

                print(
                    f"Found {len(page_links)} links, "
                    f"{added} new links."
                )

                if not page_links:
                    empty_pages += 1
                else:
                    empty_pages = 0

                # Avoid unnecessary requests after consecutive empty pages
                if empty_pages >= 2 and number > 1:
                    print("Two empty pages detected. Stopping.")
                    break

            except Exception as error:
                print(f"Page {number} failed: {error}")

        await browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for link in sorted(all_links):
            f.write(link + "\\n")

    print("\\nTotal unique video links:", len(all_links))

asyncio.run(main())
