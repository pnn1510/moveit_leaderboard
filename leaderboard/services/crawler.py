import logging
from playwright.sync_api import Page, sync_playwright
import streamlit as st

LEADERBOARD_URL = st.secrets["LEADERBOARD_URL"]
PAGE_TIMEOUT = 400


logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger()


def extract_table_rows(page: Page, headers: list[str]) -> list[dict]:
    rows: list[dict] = []
    for tr in page.query_selector_all("tbody tr"):
        # Extract data-uid attribute from the <tr> element
        data_uid = tr.get_attribute("data-uid")

        cells = [td.inner_text().strip() for td in tr.query_selector_all("td")]

        if cells:
            row = dict(zip(headers, cells)) if headers else {"cells": cells}
            # Inject data-uid into the row dict
            row["data_uid"] = data_uid  # type: ignore
            rows.append(row)

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
        logger.info(f"  page {page_num}: {len(rows)} rows (total: {len(all_rows)})")
        next_btn = page.query_selector("button.btn.btn-outline.btn-sm:has-text('Next')")
        if not next_btn or next_btn.is_disabled():
            break
        next_btn.click()
        page.wait_for_timeout(PAGE_TIMEOUT)
        page_num += 1
    return all_rows


def crawl() -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(LEADERBOARD_URL, wait_until="load", timeout=60000)
        page.wait_for_timeout(3000)
        logger.info("Fetching all pages...")
        all_rows = fetch_all_rows(page)
        browser.close()
    logger.info(f"Fetched {len(all_rows)} rows")
    return all_rows
