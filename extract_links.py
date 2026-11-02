import asyncio
import os
import re
from urllib.parse import urlparse

from playwright.async_api import async_playwright

START_URL = os.environ["PAGE_URL"]
MAX_PAGES = 30

def is_video_url(url):
    parsed = urlparse(url)

    return (
        parsed.hostname == "rule34gen.com"
        and bool(re.match(r"^/video/\d+/", parsed.path))
    )

async def extract_video_links():
    video_links = set()
    visited_pages = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        page = await browser.new_page()
        current_url = START_URL

        for page_number in range(1, MAX_PAGES + 1):
            if not current_url or current_url in visited_pages:
                break

            visited_pages.add(current_url)

            print(f"\nScanning page {page_number}: {current_url}")

            try:
                await page.goto(
                    current_url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                await page.wait_for_timeout(3000)

                links = await page.locator(
                    "a.th.js-open-popup[href]"
                ).evaluate_all(
                    "els => els.map(a => a.href)"
                )

                before = len(video_links)

                for link in links:
                    if is_video_url(link):
                        video_links.add(link)

                print(
                    f"Found {len(links)} cards; "
                    f"{len(video_links) - before} new videos."
                )

                next_url = await page.locator(
                    "a[href]"
                ).evaluate_all("""
                    els => {
                        const a = els.find(x => {
                            const t = x.innerText.trim().toLowerCase();
                            return t === 'next' ||
                                   t === 'next »' ||
                                   t === 'next ›';
                        });
                        return a ? a.href : null;
                    }
                """)

                if not next_url:
                    page_links = await page.locator(
                        "a[href]"
                    ).evaluate_all("""
                        els => els.map(a => ({
                            text: a.innerText.trim(),
                            href: a.href
                        }))
                    """)

                    candidates = []

                    for item in page_links:
                        if item["text"].isdigit():
                            number = int(item["text"])

                            if number > page_number:
                                candidates.append(
                                    (number, item["href"])
                                )

                    if candidates:
                        candidates.sort()
                        next_url = candidates[0][1]

                if not next_url or next_url == current_url:
                    print("Last page reached.")
                    break

                current_url = next_url

            except Exception as error:
                print(f"Page error: {error}")
                break

        await browser.close()

    with open("video_links.txt", "w", encoding="utf-8") as f:
        for link in sorted(video_links):
            f.write(link + "\n")

    print(f"\nTotal unique video links: {len(video_links)}")

asyncio.run(extract_video_links())
