# generator/validate_streams.py
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import os

SOURCES_FILE = "data/sources.csv"
OUTPUT_FILE = "playlist_filtered.m3u"
LOG_FILE = "validation_log.txt"

TIMEOUT = 3  # secondes max par flux
MAX_WORKERS = 30  # nombre de threads en parallèle

def check_stream(url):
    try:
        start = time.time()
        r = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code < 400:
            elapsed = round(time.time() - start, 2)
            return True, elapsed
    except Exception:
        pass
    return False, None

def load_streams():
    streams = []
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                streams.append(line)
    return streams

def save_results(valid_streams, log_data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for url in valid_streams:
            out.write(f"#EXTINF:-1,{url}\n{url}\n")
    with open(LOG_FILE, "w", encoding="utf-8") as log:
        log.write("\n".join(log_data))

def main():
    streams = load_streams()
    valid_streams = []
    log_data = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(check_stream, url): url for url in streams}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            ok, elapsed = future.result()
            if ok:
                valid_streams.append(url)
                log_data.append(f"[OK] {url} ({elapsed}s)")
            else:
                log_data.append(f"[FAIL] {url}")

    save_results(valid_streams, log_data)
    print(f"{len(valid_streams)}/{len(streams)} flux valides")

if __name__ == "__main__":
    main()
