import os
import time
import requests
import glob
import csv

# --- CONFIGURATION ---
LOCAL_M3U_DIR = r"C:\Users\berny\OneDrive\Documents\0000000000_PROJETS\M3U"
CHANNELS_CSV = "data/channels_keywords.csv"
OUTPUT_M3U = "playlist/playlist_filtered.m3u"
MAX_URLS_PER_CHANNEL = 3
TIMEOUT_INITIAL = 10  # secondes
TIMEOUT_SECOND_PASS = 20

# --- UTILITAIRES ---

def read_keywords(csv_path):
    keywords = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            channel = row["channel"].strip()
            kw_list = [k.strip() for k in row["keyword"].split("|")[:5]]
            keywords[channel] = kw_list
    return keywords

def find_m3u_files(base_dir):
    return glob.glob(os.path.join(base_dir, "**", "*.m3u"), recursive=True)

def parse_m3u_urls(file_path):
    urls = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("http"):
                urls.append(line)
    return urls

def filter_urls_by_keywords(urls, keywords):
    filtered = []
    for url in urls:
        url_lower = url.lower()
        for kws in keywords.values():
            if any(kw.lower() in url_lower for kw in kws):
                filtered.append(url)
                break
    return filtered

def validate_url(url, timeout):
    try:
        r = requests.head(url, timeout=timeout, allow_redirects=True)
        return r.status_code == 200
    except:
        return False

# --- SCRIPT PRINCIPAL ---

def main():
    keywords = read_keywords(CHANNELS_CSV)

    # Trouver tous les fichiers M3U
    m3u_files = find_m3u_files(LOCAL_M3U_DIR)
    print(f"DEBUG: {len(m3u_files)} M3U files found locally.")

    all_urls = []
    for f in m3u_files:
        file_urls = parse_m3u_urls(f)
        all_urls.extend(file_urls)
    print(f"DEBUG: Total URLs parsed: {len(all_urls)}")

    filtered_urls = filter_urls_by_keywords(all_urls, keywords)
    print(f"DEBUG: URLs after keyword filtering: {len(filtered_urls)}")

    # Validation progressive
    valid_urls = {}
    total = len(filtered_urls)
    start_time = time.time()
    for i, url in enumerate(filtered_urls, 1):
        channel_name = None
        for ch, kws in keywords.items():
            if any(kw.lower() in url.lower() for kw in kws):
                channel_name = ch
                break
        if channel_name is None:
            continue

        # Validation
        timeout = TIMEOUT_INITIAL
        is_valid = validate_url(url, timeout)
        if not is_valid:
            timeout = TIMEOUT_SECOND_PASS
            is_valid = validate_url(url, timeout)

        if is_valid:
            if channel_name not in valid_urls:
                valid_urls[channel_name] = []
            if len(valid_urls[channel_name]) < MAX_URLS_PER_CHANNEL:
                valid_urls[channel_name].append(url)

        # Progression
        elapsed = time.time() - start_time
        pct = (i / total) * 100 if total > 0 else 0
        est_total = (elapsed / i) * total if i > 0 else 0
        est_remaining = est_total - elapsed
        print(f"Progress: {i}/{total} ({pct:.2f}%) | Estimated remaining: {int(est_remaining)}s | Valid channels so far: {len(valid_urls)}")

    # Écrire la playlist finale
    os.makedirs(os.path.dirname(OUTPUT_M3U), exist_ok=True)
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch, urls in valid_urls.items():
            for idx, url in enumerate(urls, 1):
                line_name = f"{ch}_{idx}" if idx > 1 else ch
                f.write(f"#EXTINF:-1,{line_name}\n{url}\n")

    print(f"\nValidation finished. Total valid channels: {len(valid_urls)}")
    for ch, urls in valid_urls.items():
        print(f"{ch}: {len(urls)} flux validés")

if __name__ == "__main__":
    main()
