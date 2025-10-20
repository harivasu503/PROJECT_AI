# selenium_scraper_bse.py
"""
Selenium BSE Announcement / Concall Scraper

Usage:
    python selenium_scraper_bse.py --limit 10            # test first 10 stocks
    python selenium_scraper_bse.py --limit 0 --download  # all stocks and download files

Notes:
 - Requires Chrome installed.
 - webdriver-manager auto-downloads the correct chromedriver.
 - Uses MongoDB at mongodb://localhost:27017/ by default (configurable below).
"""

import os
import re
import time
import argparse
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from pymongo import MongoClient

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# --------------------------
# Config (adjust as needed)
# --------------------------
BSE_BASE = "https://www.bseindia.com"
ANNOUNCE_SEARCH_URL = "https://www.bseindia.com/corporates/announcements.aspx"
ANN_GET_PATH = "/corporates/AnnGet.aspx"  # backup direct page
TOP_STOCKS_FILE = "top_500_stocks.csv"
DOWNLOAD_FOLDER = "downloads"
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB = "concall_insights"
MONGO_COLLECTION = "filings_meta"

HEADLESS = True              # run browser headless
SLEEP_BETWEEN_STOCKS = 1.0   # politeness
PAGE_LOAD_TIMEOUT = 20
ELEMENT_WAIT = 12
DOWNLOAD_FILES = False       # set True if you want to download PDFs

# HTTP session for file download
http_session = requests.Session()
http_session.headers.update({"User-Agent": "ConcallInsightsBot/1.0 (+https://yourdomain.example)"})

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("selenium-bse")

# MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
collection = db[MONGO_COLLECTION]

# Utility functions
def safe_sleep(seconds=SLEEP_BETWEEN_STOCKS):
    time.sleep(seconds)

def canonicalize_url(href: str) -> str:
    if not href:
        return None
    href = href.strip()
    if href.startswith("http"):
        return href
    return urljoin(BSE_BASE, href)

def filename_from_url(url: str) -> str:
    if not url:
        return None
    path = urlparse(url).path
    name = os.path.basename(path)
    if not name:
        name = re.sub(r'\W+', '_', url)
    return name

def download_file(url: str, dest_folder: str = DOWNLOAD_FOLDER) -> str:
    try:
        os.makedirs(dest_folder, exist_ok=True)
        local_name = filename_from_url(url)
        local_path = os.path.join(dest_folder, local_name)
        logger.info(f"Downloading {url} -> {local_path}")
        with http_session.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return local_path
    except Exception as e:
        logger.warning(f"Failed to download {url}: {e}")
        return None

def save_filing_record(bse_code: str, stock_name: str, filing_url: str, anchor_text: str, context_text: str, local_path: str = None):
    rec = {
        "bse_code": bse_code,
        "stock_name": stock_name,
        "filing_url": filing_url,
        "anchor_text": anchor_text,
        "context_text": context_text,
        "filename": filename_from_url(filing_url),
        "local_path": local_path,
        "source": "bseindia.com",
        "scraped_at": datetime.utcnow()
    }
    try:
        collection.update_one({"bse_code": bse_code, "filing_url": filing_url}, {"$set": rec}, upsert=True)
        logger.info(f"Saved metadata for {stock_name} - {filing_url}")
    except Exception as e:
        logger.error(f"MongoDB insert error: {e}")

# Selenium helpers
def make_driver(headless=HEADLESS):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    # avoid detection flags (optional)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    return driver

def extract_links_from_annget_html(html: str):
    """Fallback HTML parse if we fetch raw AnnGet.aspx page via requests (rare)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        onclick = a.get("onclick") or ""
        url = None
        # handle javascript DownloadFile('path')
        m = re.search(r"DownloadFile\('(.+?)'\)", onclick)
        if m:
            url = canonicalize_url(m.group(1))
        elif href and ("pdf" in href.lower() or href.startswith("http") or href.endswith(".aspx")):
            url = canonicalize_url(href)
        if url:
            results.append({"href": url, "anchor_text": a.get_text(strip=True), "parent_text": a.parent.get_text(" ", strip=True) if a.parent else ""})
    # dedupe by href
    unique = {r['href']: r for r in results}
    return list(unique.values())

def extract_links_from_rendered_page(driver):
    """Extract link candidates from the rendered page (Selenium DOM)."""
    results = []
    try:
        anchors = driver.find_elements(By.TAG_NAME, "a")
    except Exception:
        return results
    for a in anchors:
        try:
            href = a.get_attribute("href") or ""
            onclick = a.get_attribute("onclick") or ""
            text = a.text or ""
            url = None
            m = None
            if onclick and "DownloadFile" in onclick:
                m = re.search(r"DownloadFile\('(.+?)'\)", onclick)
                if m:
                    url = canonicalize_url(m.group(1))
            if not url and href:
                # sometimes href is javascript or relative
                if href.startswith("http") and ("pdf" in href.lower() or "annexure" in href.lower()):
                    url = href
                elif href.endswith(".pdf") or href.endswith(".html") or href.endswith(".htm"):
                    url = canonicalize_url(href)
            if url:
                context = ""
                try:
                    context = a.find_element(By.XPATH, "..").text
                except Exception:
                    context = ""
                results.append({"href": url, "anchor_text": text.strip(), "parent_text": context.strip()})
        except Exception:
            continue
    # dedupe
    unique = {}
    for r in results:
        unique[r['href']] = r
    return list(unique.values())

# Core processing per stock
def process_stock(driver, bse_code: str, stock_name: str, download_files: bool = DOWNLOAD_FILES):
    logger.info(f"Processing {stock_name} ({bse_code})")
    # Strategy 1: Try AnnGet.aspx direct (some scrips still work)
    try:
        annget_url = f"{BSE_BASE}{ANN_GET_PATH}?scrip={bse_code}&expandable=0"
        logger.debug(f"Trying direct AnnGet URL: {annget_url}")
        driver.get(annget_url)
        # wait a bit for JS (if any)
        try:
            WebDriverWait(driver, ELEMENT_WAIT).until(EC.presence_of_all_elements_located((By.TAG_NAME, "a")))
        except TimeoutException:
            logger.debug("No anchors found on AnnGet direct; continuing to announcements search page.")
        links = extract_links_from_rendered_page(driver)
        if not links:
            # Strategy 2: load announcements search page and input scrip code
            logger.debug("No links from AnnGet direct; trying announcements search page.")
            driver.get(ANNOUNCE_SEARCH_URL)
            try:
                # Try several common selectors for search input/button (BSE site varies)
                found_input = None
                possible_inputs = [
                    ('id', 'ctl00_ContentPlaceHolder1_txtScripCode'),
                    ('id', 'txtScripCode'),
                    ('name', 'scrip'),
                    ('css', 'input[placeholder*="Scrip"]'),
                    ('css', 'input[aria-label*="Scrip"]'),
                    ('css', 'input[type="text"]')
                ]
                for by, sel in possible_inputs:
                    try:
                        if by == 'id':
                            el = driver.find_element(By.ID, sel)
                        elif by == 'name':
                            el = driver.find_element(By.NAME, sel)
                        else:
                            el = driver.find_element(By.CSS_SELECTOR, sel)
                        found_input = el
                        break
                    except Exception:
                        continue

                if not found_input:
                    logger.debug("Search input not found by common selectors - attempting JS injection.")
                    # fallback: try to run JS to fill scrip and call search function if available
                    script = f"""
                    try {{
                        var txt = document.querySelector('input');
                        if(txt){{ txt.value = '{bse_code}'; }}
                        var btn = document.querySelector('input[type=submit], button');
                        if(btn){{ btn.click(); }}
                    }} catch(e){{}}
                    """
                    driver.execute_script(script)
                else:
                    found_input.clear()
                    found_input.send_keys(bse_code)
                    # try to find a search button near the input
                    try:
                        parent = found_input.find_element(By.XPATH, "..")
                        # look for button or input submit in parent
                        btn = None
                        try:
                            btn = parent.find_element(By.XPATH, ".//input[@type='submit' or @type='button']")
                        except Exception:
                            try:
                                btn = parent.find_element(By.TAG_NAME, "button")
                            except Exception:
                                btn = None
                        if btn:
                            btn.click()
                        else:
                            # try pressing Enter
                            found_input.send_keys("\n")
                    except Exception:
                        found_input.send_keys("\n")

                # wait for results table to appear
                WebDriverWait(driver, ELEMENT_WAIT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
                )
                # extract links
                links = extract_links_from_rendered_page(driver)
            except TimeoutException:
                logger.warning(f"Announcements search timed out for {bse_code}")
                links = []
    except WebDriverException as e:
        logger.error(f"Selenium error while processing {bse_code}: {e}")
        links = []

    # If still empty, attempt to fetch raw AnnGet.aspx via requests as last resort
    if not links:
        try:
            raw_url = f"{BSE_BASE}{ANN_GET_PATH}?scrip={bse_code}&expandable=0"
            logger.debug(f"Trying raw HTTP get fallback: {raw_url}")
            resp = http_session.get(raw_url, timeout=15)
            if resp.ok:
                links = extract_links_from_annget_html(resp.text)
            else:
                logger.debug(f"Fallback HTTP returned status {resp.status_code}")
        except Exception as e:
            logger.debug(f"Raw HTTP fallback failed: {e}")

    if not links:
        logger.info(f"No candidate filings found for {stock_name} ({bse_code})")
        return

    # Save each link
    for item in links:
        url = item.get("href")
        # ignore javascript:
        if not url or url.lower().startswith("javascript"):
            continue
        local_path = None
        if download_files:
            local_path = download_file(url)
        save_filing_record(bse_code, stock_name, url, item.get("anchor_text", ""), item.get("parent_text", ""), local_path)
    # polite pause
    safe_sleep()

def process_all(csv_file=TOP_STOCKS_FILE, limit=None, download=False):
    if download:
        global DOWNLOAD_FILES
        DOWNLOAD_FILES = True
    if not os.path.exists(csv_file):
        logger.error(f"CSV file {csv_file} not found. Create a CSV with columns: BSE_Code,Stock_Name")
        return
    df = pd.read_csv(csv_file, dtype=str)
    if limit and limit > 0:
        df = df.head(limit)
    # Create driver
    driver = make_driver()
    try:
        for idx, row in df.iterrows():
            bse_code = row.get("BSE_Code") or row.get("BSE Code") or row.get("ScripCode") or row.get("Scrip Code")
            stock_name = row.get("Stock_Name") or row.get("Stock Name") or row.get("Name") or ""
            if not bse_code:
                logger.warning(f"Missing BSE code at row {idx}, skipping")
                continue
            try:
                process_stock(driver, bse_code.strip(), stock_name.strip() if stock_name else "", download_files=DOWNLOAD_FILES)
            except Exception as e:
                logger.exception(f"Unhandled error for {bse_code}: {e}")
        logger.info("All stocks processed.")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

# CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=str, default=TOP_STOCKS_FILE, help="CSV file with BSE_Code,Stock_Name")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of stocks (0 = all)")
    parser.add_argument("--download", action="store_true", help="Download files")
    args = parser.parse_args()
    lim = args.limit if args.limit and args.limit > 0 else None
    process_all(csv_file=args.csv, limit=lim, download=args.download)
