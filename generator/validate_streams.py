import csv
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

SOURCES_FILE = "data/sources.csv"
OUTPUT_FILE = "playlist_filtered.m3u"
LOG_FILE = "validation_log.txt"

TIMEOUT = 5  # secondes
MAX_WORKERS = 20  # threads

def validate_stream(url):
    try:
        r = requests.get(url, timeout=TIMEOUT, stream=True)
        if r.status_code == 200 and b"#EXTM3U" in r.content[:1000]:
            return url, True
        else:
            return url, False
    except:
        return url, False

def fetch_and_filter():
    valid_streams = []
    log_lines = []

    with open(SOURCES_FILE, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        urls = [row["url"] for row in reader]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(validate_stream, url): url for url in urls}
        for future in as_completed(future_to_url):
            url, is_valid = future.result()
            log_lines.append(f"{url} => {'VALID' if is_valid else 'INVALID'}")
            if is_valid:
                try:
                    r = requests.get(url, timeout=TIMEOUT)
                    playlist_lines = r.text.strip().splitlines()
                    valid_streams.extend(playlist_lines)
                except:
                    pass

    # Écriture logs
    with open(LOG_FILE, "w", encoding="utf-8") as logf:
        logf.write("\n".join(log_lines))

    # Filtrage pour éviter doublons
    filtered = []
    seen = set()
    for line in valid_streams:
        if line not in seen:
            filtered.append(line)
            seen.add(line)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as outf:
        outf.write("\n".join(filtered))

if __name__ == "__main__":
    fetch_and_filter()
