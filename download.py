
import asyncio
import os
import re
import json
import yt_dlp

from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright

# ---------------- CONFIG ----------------

START_URL = (
    "https://rule34gen.com/search/shizzleai-/"
    "?sort_by=post_date"
)

OUTPUT_DIR = "ShizzleAI_Videos"
ARCHIVE_FILE = "downloaded.txt"
FAILED_FILE = "failed.txt"
LINKS_FILE = "video_links.txt"

# کیفیت‌های موردنظر به ترتیب اولویت
PREFERRED_HEIGHTS = [1024, 720, 576, 480, 360]

MAX_PAGES = 30

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------------- URL FILTER ----------------

def is_video_url(url):

    parsed = urlparse(url)

    if parsed.hostname != "rule34gen.com":
        return False

    return bool(
        re.match(
            r"^/video/\d+/",
            parsed.path
        )
    )


# ---------------- EXTRACT PAGES ----------------

async def extract_video_links():

    video_links = set()

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False
        )

        page = await browser.new_page()

        current_url = START_URL
        visited_pages = set()

        for page_number in range(1, MAX_PAGES + 1):

            if not current_url:
                break

            if current_url in visited_pages:
                break

            visited_pages.add(current_url)

            print(
                f"\nScanning page "
                f"{page_number}: {current_url}"
            )

            try:

                await page.goto(
                    current_url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                await page.wait_for_timeout(2500)

                # فقط کارت‌های واقعی ویدیو
                links = await page.locator(
                    "a.th.js-open-popup[href]"
                ).evaluate_all("""
                    els => els.map(a => a.href)
                """)

                for link in links:

                    if is_video_url(link):
                        video_links.add(link)

                print(
                    "Videos collected:",
                    len(video_links)
                )

                # پیدا کردن صفحه بعد
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

                # اگر دکمه Next پیدا نشد، شماره صفحات را بررسی کن
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
                    break

                current_url = next_url

            except Exception as e:

                print("Page error:", e)
                break

        await browser.close()

    # ذخیره لینک‌ها
    with open(
        LINKS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        for link in sorted(video_links):
            f.write(link + "\n")

    print(
        "\nTotal video links:",
        len(video_links)
    )

    return sorted(video_links)


# ---------------- DOWNLOAD ----------------

def download_video(url):

    options = {

        # انتخاب بهترین کیفیت موجود
        "format": (
            "bestvideo*+bestaudio/"
            "best"
        ),

        "merge_output_format": "mp4",

        "outtmpl": os.path.join(
            OUTPUT_DIR,
            "%(title).120B_%(id)s.%(ext)s"
        ),

        "download_archive": ARCHIVE_FILE,

        "ignoreerrors": True,

        "continuedl": True,

        "retries": 5,

        "fragment_retries": 5,

        "noplaylist": True,

        "quiet": False,

        "no_warnings": False,

    }

    try:

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                url,
                download=False
            )

            if not info:
                raise Exception("Video information unavailable")

            # نمایش کیفیت‌های موجود
            formats = info.get("formats", [])

            heights = sorted(
                {
                    f.get("height")
                    for f in formats
                    if f.get("height")
                },
                reverse=True
            )

            print("Available heights:", heights)

            selected = None

            for height in PREFERRED_HEIGHTS:

                if height in heights:
                    selected = height
                    break

            if selected:
                print("Preferred quality:", selected)
            else:
                print("Using best available quality")

            # دانلود با بهترین کیفیت قابل‌شناسایی
            ydl.download([url])

    except Exception as e:

        print("Download failed:", url)
        print("Reason:", str(e))

        with open(
            FAILED_FILE,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(url + "\n")


# ---------------- MAIN ----------------

async def main():

    print("=" * 50)
    print("       SHIZZLEAI VIDEO DOWNLOADER")
    print("=" * 50)

    links = await extract_video_links()

    if not links:

        print("No video links found.")
        return

    print("\nStarting downloads...\n")

    total = len(links)

    for index, url in enumerate(links, 1):

        print("\n" + "=" * 50)

        print(
            f"Video {index}/{total}"
        )

        print(url)

        try:

            await asyncio.to_thread(
                download_video,
                url
            )

        except Exception as e:

            print("Unexpected error:", e)

            with open(
                FAILED_FILE,
                "a",
                encoding="utf-8"
            ) as f:

                f.write(url + "\n")

            continue

    print("\n" + "=" * 50)
    print("DOWNLOAD PROCESS FINISHED")
    print("=" * 50)

    print("Output folder:", OUTPUT_DIR)
    print("Archive:", ARCHIVE_FILE)
    print("Failed links:", FAILED_FILE)


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nStopped by user.")
