import os
import csv
import logging
import asyncio
from datetime import datetime
from pymongo import MongoClient
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# -----------------------
# CONFIG
# -----------------------
CSV_PATH = "top_500_stocks.csv"
DATA_DIR = "pdfs"
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "bse_scraper"
COLLECTION_NAME = "transcripts"

os.makedirs(DATA_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# -----------------------
# MONGO
# -----------------------
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
logging.info("✅ Connected to MongoDB successfully.")

# -----------------------
# PLAYWRIGHT ASYNC PDF DOWNLOAD
# -----------------------
async def download_pdf(url, filename):
    path = os.path.join(DATA_DIR, filename)
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
            })

            async with page.expect_download() as download_info:
                await page.goto(url, timeout=60000)
            download = await download_info.value
            await download.save_as(path)
            logging.info(f"📥 Downloaded PDF: {filename}")
            await browser.close()
    except PlaywrightTimeoutError:
        logging.error(f"❌ Timeout downloading {filename}: {url}")
    except Exception as e:
        logging.error(f"❌ Failed to download {filename}: {e}")

# -----------------------
# FETCH TRANSCRIPTS (placeholder)
# -----------------------
def fetch_transcripts(scrip_code):
    base_url = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/"
    example_pdf = f"{base_url}f2454c0f-aad9-4d23-add0-dfe3d49aa8d6.pdf"
    return [example_pdf]

# -----------------------
# PROCESS STOCKS
# -----------------------
async def process_stocks_async(csv_path, limit=None):
    tasks = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            if limit and count >= limit:
                break

            company_name = row.get("Company") or row.get("Name")
            scrip_code = row.get("BSE Code") or row.get("ScripCode")
            if not company_name or not scrip_code:
                logging.warning(f"Skipping row: missing Company or BSE Code {row}")
                continue

            logging.info(f"🔍 Processing {company_name} ({scrip_code})")
            transcript_links = fetch_transcripts(scrip_code)
            if not transcript_links:
                logging.warning(f"No data for {scrip_code}")
                continue

            # MongoDB insert
            doc = {
                "company": company_name,
                "scrip_code": scrip_code,
                "links": transcript_links,
                "scraped_at": datetime.now()
            }
            collection.insert_one(doc)
            logging.info(f"✅ Inserted {len(transcript_links)} transcript links into MongoDB.")

            # Schedule PDF downloads
            for link in transcript_links:
                filename = f"{scrip_code}_{os.path.basename(link)}"
                tasks.append(download_pdf(link, filename))

            count += 1

    # Run all downloads concurrently
    await asyncio.gather(*tasks)
    logging.info("🎯 Scraping run completed.")

# -----------------------
# ENTRY POINT
# -----------------------
if __name__ == "__main__":
    asyncio.run(process_stocks_async(CSV_PATH, limit=10))
