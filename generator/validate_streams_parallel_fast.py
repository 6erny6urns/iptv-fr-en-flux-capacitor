import os
import glob
import csv
import re
import time
import concurrent.futures
import requests

# --- CONFIGURATION ---
LOCAL_M3U_DIR = r"C:\Users\berny\OneDrive\Documents\0000000000_PROJETS\M3U"
OUTPUT_DIR = "playlist"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "playlist_filtered.m3u")
LOG_FILE = "validation_log.txt"
KEYWORDS_CSV = "data/keywords.csv"
MIN_CHANNELS = 25
TIMEOUT_INITIAL = 10
TIMEOUT_SECOND = 20
MAX_WORKERS = 25

# --- UTILITAIRES ---
def load_keywords(csv_file):
    keywords = {}
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                keywords[row[0]] = [kw.strip() for kw in row[1:6] if kw.strip()]
    return keywords

def find_m3u_files(local_dir, max_files=None):
    files = glob.glob(os.path.join(local_dir, '**/*.m3u'), recursive=True)
    if max_files:
        files = files[:max_files]
    return files

def parse_m3u(file_path):
    urls = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls

def url_matches_keywords(url, keywords_dict):
    url_lower = url.lower()
    for channel, variants in keywords_dict.items():
        for kw in variants:
            if kw.lower() in url_lower:
                return channel
    return None

def validate_url(url, timeout):
    try:
        r = requests.head(url, timeout=timeout, allow_redirects=True)
        if r.status_code == 200:
            return True
    except Exception:
        return False
    return False

# --- LOG ---
log_lines = []
valid_streams = {}

def log(message):
    print(message)
    log_lines.append(message)

# --- PROCESS ---
def process_urls(urls, keywords_dict, timeout):
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(validate_url, url, timeout): url for url in urls}
        for i, future in enumerate(concurrent.futures.as_completed(future_to_url), 1):
            url = future_to_url[future]
            channel = url_matches_keywords(url, keywords_dict)
            if channel and future.result():
                results[channel] = url
                log(f"[VALID] {channel} -> {url} ({i}/{len(urls)})")
            else:
                log(f"[INVALID] {url} ({i}/{len(urls)})")
            # Progress
            print(f"Progress: {i}/{len(urls)} ({i*100/len(urls):.1f}%)")
    return results

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    keywords_dict = load_keywords(KEYWORDS_CSV)

    # --- PASS 1 ---
    log("Starting first pass with initial timeout...")
    m3u_files = find_m3u_files(LOCAL_M3U_DIR, max_files=25)
    if not m3u_files:
        log("No M3U files found locally.")
    all_urls = []
    for f in m3u_files:
        all_urls.extend(parse_m3u(f))
    log(f"Found {len(all_urls)} URLs in first pass.")
    global valid_streams
    valid_streams = process_urls(all_urls, keywords_dict, TIMEOUT_INITIAL)

    # --- PASS 2 if needed ---
    if len(valid_streams) < MIN_CHANNELS:
        remaining_needed = MIN_CHANNELS - len(valid_streams)
        log(f"PASS 2: Need {remaining_needed} more channels, second pass with longer timeout...")
        remaining_files = find_m3u_files(LOCAL_M3U_DIR, max_files=None)
        remaining_files = [f for f in remaining_files if f not in m3u_files]
        remaining_files = remaining_files[:remaining_needed]
        all_urls_second = []
        for f in remaining_files:
            all_urls_second.extend(parse_m3u(f))
        additional_streams = process_urls(all_urls_second, keywords_dict, TIMEOUT_SECOND)
        valid_streams.update(additional_streams)

    # --- WRITE OUTPUT ---
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for channel, url in valid_streams.items():
            f.write(f"#EXTINF:-1,{channel}\n{url}\n")

    log(f"Total valid channels: {len(valid_streams)}")
    log("Validation finished.")

    # --- WRITE LOG ---
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(log_lines))

if __name__ == "__main__":
    main()
