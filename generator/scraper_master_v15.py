import os
import re
import csv
import sys
import time
import random
import logging
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# -------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------
OUTPUT_DIR = "output"
CSV_FILE = os.path.join(OUTPUT_DIR, "scraped_m3u_links.csv")
LOG_FILE = os.path.join(OUTPUT_DIR, "log_scraper_v15.txt")

SEARCH_ENGINES = [
    "https://www.google.com/search?q=",
    "https://www.bing.com/search?q="
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)"
]

SEARCH_QUERIES = [
    "site:pastebin.com m3u",
    "site:github.com m3u playlist",
    "free iptv m3u filetype:m3u",
    "extinf m3u playlist live tv"
]

REQUEST_TIMEOUT = 10
MAX_RESULTS = 50  # max links per query

# -------------------------------------------------------------
# LOGGING
# -------------------------------------------------------------
os.makedirs(OUTPUT_DIR, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# -------------------------------------------------------------
# FUNCTIONS
# -------------------------------------------------------------
def fetch_url(url: str) -> str:
    """Download page content with random headers."""
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logging.error(f"Failed to fetch {url}: {e}")
        return ""


def parse_search_results(html: str, base: str) -> list:
    """Extract URLs from search result page."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Google often wraps links
        if "url?q=" in href:
            href = href.split("url?q=")[1].split("&")[0]
        # Bing: direct or with &r=
        if href.startswith("/url?"):
            continue
        if href.startswith("http") and "google" not in href and "bing" not in href:
            links.append(href)
    return links


def extract_m3u_links(url: str) -> list:
    """Fetch page and extract direct .m3u/.m3u8 links."""
    html = fetch_url(url)
    if not html:
        return []
    matches = re.findall(r"https?://[^\s\"']+\.m3u8?", html, re.IGNORECASE)
    return list(set(matches))


def save_to_csv(rows: list, filename: str):
    """Save results to CSV file."""
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Source", "M3U_Link"])
        writer.writerows(rows)


# -------------------------------------------------------------
# MAIN
# -------------------------------------------------------------
def main():
    logging.info("=== Scraper v15 started ===")
    all_results = []

    for query in SEARCH_QUERIES:
        logging.info(f"Searching: {query}")
        for engine in SEARCH_ENGINES:
            search_url = engine + requests.utils.quote(query)
            logging.info(f"Fetching search results: {search_url}")
            html = fetch_url(search_url)
            if not html:
                continue

            urls = parse_search_results(html, engine)
            logging.info(f"Found {len(urls)} URLs in search results")

            for u in urls[:MAX_RESULTS]:
                logging.info(f"Scanning: {u}")
                links = extract_m3u_links(u)
                for link in links:
                    all_results.append((u, link))
                time.sleep(random.uniform(1, 3))  # polite delay

    if all_results:
        save_to_csv(all_results, CSV_FILE)
        logging.info(f"Saved {len(all_results)} M3U links to {CSV_FILE}")
    else:
        logging.info("No results found.")

    logging.info("=== Scraper v15 finished ===")
    print(f"Process complete. Results saved to: {CSV_FILE}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.warning("Interrupted by user")
        sys.exit(1)
