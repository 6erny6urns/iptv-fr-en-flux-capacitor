import os
import csv
import glob
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION ---
LOCAL_M3U_DIR = r"C:\Users\berny\OneDrive\Documents\0000000000_PROJETS\M3U"
KEYWORDS_FILE = "data/channels_keywords.csv"  # depuis GitHub
OUTPUT_DIR = "playlist"
OUTPUT_M3U = os.path.join(OUTPUT_DIR, "playlist_filtered.m3u")
MAX_WORKERS = 25
TIMEOUT = 10  # secondes pour chaque flux
MAX_PER_CHANNEL = 3  # max flux par chaîne

# --- CHARGER LES MOTS-CLÉS ---
keywords = {}
with open(KEYWORDS_FILE, newline='', encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:
        channel_name = row[0].strip()
        variants = [v.strip() for v in row[1:6] if v.strip()]
        keywords[channel_name] = variants

# --- TROUVER LES FICHIERS M3U ---
m3u_files = glob.glob(os.path.join(LOCAL_M3U_DIR, "**", "*.m3u"), recursive=True)
print(f"DEBUG: {len(m3u_files)} M3U files found in {LOCAL_M3U_DIR}")

# --- EXTRACTION DES URLS ---
def parse_m3u_urls(file_path):
    urls = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("http"):
                    urls.append(line)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return urls

all_urls = []
for f in m3u_files:
    urls = parse_m3u_urls(f)
    all_urls.extend(urls)
print(f"DEBUG: Total URLs parsed: {len(all_urls)}")

# --- FILTRAGE PAR MOTS-CLÉS ---
def matches_keywords(url, keywords_dict):
    url_lower = url.lower()
    for chan, variants in keywords_dict.items():
        for var in variants:
            var_lower = var.lower()
            if var_lower in url_lower:
                return chan
    return None

filtered = [(url, matches_keywords(url, keywords)) for url in all_urls if matches_keywords(url, keywords)]
print(f"DEBUG: URLs after keyword filtering: {len(filtered)}")

# --- VALIDATION DES FLUX ---
def validate_stream(url):
    try:
        r = requests.head(url, timeout=TIMEOUT)
        if r.status_code == 200:
            return True
    except:
        pass
    return False

valid_urls = {}
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {executor.submit(validate_stream, url): (url, chan) for url, chan in filtered}
    count = 0
    for future in as_completed(futures):
        url, chan = futures[future]
        if future.result():
            if chan not in valid_urls:
                valid_urls[chan] = []
            if len(valid_urls[chan]) < MAX_PER_CHANNEL:
                valid_urls[chan].append(url)
        count += 1
        if count % 50 == 0:
            print(f"Progress: {count}/{len(filtered)} URLs validated")

# --- ÉCRITURE DU M3U ---
os.makedirs(OUTPUT_DIR, exist_ok=True)
with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for chan, urls in valid_urls.items():
        for i, url in enumerate(urls, start=1):
            name = f"{chan}" if i == 1 else f"{chan} {i}"
            f.write(f"#EXTINF:-1,{name}\n{url}\n")

print("Validation finished.")
print(f"Total channels: {len(valid_urls)}")
for chan, urls in valid_urls.items():
    print(f"{chan}: {len(urls)} flux")
