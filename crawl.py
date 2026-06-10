import json
import os
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

URL = "https://moveit.kms-technology.com/leaderboard"
DOWNLOADS_DIR = Path("downloads")


def extract_table_rows(page: Page, headers: list[str]) -> list[dict]:
    rows: list[dict] = []
    for tr in page.query_selector_all("tbody tr"):
        cells = [td.inner_text().strip() for td in tr.query_selector_all("td")]
        if cells:
            rows.append(dict(zip(headers, cells)) if headers else {"cells": cells})
    return rows


def get_headers(page: Page) -> list[str]:
    table = page.query_selector("table")
    if not table:
        return []
    return [th.inner_text().strip() for th in table.query_selector_all("th")]


def fetch_all_rows(page: Page) -> list[dict]:
    headers = get_headers(page)
    all_rows: list[dict] = []
    page_num = 1

    while True:
        rows = extract_table_rows(page, headers)
        all_rows.extend(rows)
        print(f"  page {page_num}: {len(rows)} rows (total: {len(all_rows)})")

        next_btn = page.query_selector("button.btn.btn-outline.btn-sm:has-text('Next')")
        if not next_btn or next_btn.is_disabled():
            break

        next_btn.click()
        page.wait_for_timeout(800)
        page_num += 1

    return all_rows


def crawl() -> None:
    DOWNLOADS_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto(URL, wait_until="load", timeout=60000)
        page.wait_for_timeout(3000)

        html = page.content()
        text = page.inner_text("body")

        print("Fetching all pages...")
        all_rows = fetch_all_rows(page)

        page.screenshot(path=str(DOWNLOADS_DIR / "screenshot.png"), full_page=True)
        browser.close()

    (DOWNLOADS_DIR / "leaderboard.html").write_text(html, encoding="utf-8")
    (DOWNLOADS_DIR / "leaderboard.txt").write_text(text, encoding="utf-8")
    (DOWNLOADS_DIR / "leaderboard.json").write_text(
        json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\nSaved to {DOWNLOADS_DIR}/")
    print(f"  leaderboard.html  ({os.path.getsize(DOWNLOADS_DIR / 'leaderboard.html')} bytes)")
    print(f"  leaderboard.txt   ({os.path.getsize(DOWNLOADS_DIR / 'leaderboard.txt')} bytes)")
    print(f"  leaderboard.json  ({len(all_rows)} rows)")
    print("  screenshot.png")


if __name__ == "__main__":
    crawl()
