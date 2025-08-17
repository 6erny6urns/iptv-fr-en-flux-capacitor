# validate_streams_parallel_fast.py
import os
import csv
import glob
import asyncio
import aiohttp
import aiofiles
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# --- CONFIGURATION ---
LOCAL_M3U_DIR = r"C:\Users\berny\OneDrive\Documents\0000000000_PROJETS\M3U"
CHANNELS_KEYWORDS_FILE = "data/channels_keywords.csv"
OUTPUT_DIR = "playlist"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "playlist_filtered.m3u")
LOG_FILE = "validation_log.txt"

# Timeout progressif
INITIAL_TIMEOUT = 10  # secondes
SECOND_PASS_TIMEOUT = 20
MAX_WORKERS = 25

# Minimum de canaux à trouver avant deuxième passe
MIN_CHANNELS = 25

# --- UTILITAIRES ---
def normalize_text(s):
    s = s.lower()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s

async def head_request(session, url, timeout):
    try:
        async with session.head(url, timeout=timeout) as resp:
            return resp.status == 200
    except:
        return False

async def fetch_valid_url(url, timeout):
    async with aiohttp.ClientSession() as session:
        return await head_request(session, url, timeout)

def load_keywords(csv_file):
    keywords = {}
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2:
                continue
            channel = row[0].strip()
            words = [x.strip() for x in row[1:6] if x.strip()]
            if words:
                keywords[channel] = words
    return keywords

def find_m3u_files(local_dir):
    files = glob.glob(os.path.join(local_dir, "**", "*.m3u"), recursive=True)
    return files

def parse_m3u_urls(m3u_file):
    urls = []
    with open(m3u_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("http"):
                urls.append(line)
    return urls

def filter_urls_by_keywords(urls, keywords):
    matched = []
    for url in urls:
        norm_url = normalize_text(url)
        for channel, words in keywords.items():
            for w in words:
                if normalize_text(w) in norm_url:
                    matched.append((url, channel))
                    break
    return matched

async def validate_urls(url_channel_list, timeout):
    valid_urls = []
    results = []
    semaphore = asyncio.Semaphore(MAX_WORKERS)

    async def validate_pair(url, channel):
        async with semaphore:
            ok = await fetch_valid_url(url, timeout)
            results.append((url, channel, ok))
            if ok:
                valid_urls.append((url, channel))
            print(f"[{len(results)}/{len(url_channel_list)}] {url} -> {'VALID' if ok else 'INVALID'}")
    await asyncio.gather(*(validate_pair(url, ch) for url, ch in url_channel_list))
    return valid_urls, results

def write_m3u(valid_list, output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for url, channel in valid_list:
            f.write(f"#EXTINF:-1,{channel}\n{url}\n")

def write_log(results):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        for url, channel, ok in results:
            f.write(f"{channel}: {url} -> {'VALID' if ok else 'INVALID'}\n")

# --- MAIN ---
async def main():
    keywords = load_keywords(CHANNELS_KEYWORDS_FILE)
    print(f"Loaded {len(keywords)} channels keywords.")

    m3u_files = find_m3u_files(LOCAL_M3U_DIR)
    if not m3u_files:
        print("Found 0 M3U files locally.")
        return

    print(f"Found {len(m3u_files)} M3U files locally. Parsing URLs...")
    urls = []
    for f in m3u_files:
        urls.extend(parse_m3u_urls(f))
    print(f"Total URLs parsed: {len(urls)}")

    # Première passe
    url_channel_list = filter_urls_by_keywords(urls, keywords)
    print(f"URLs after keyword filtering: {len(url_channel_list)}")

    valid_list, results = await validate_urls(url_channel_list, INITIAL_TIMEOUT)

    # Deuxième passe si nécessaire
    if len(valid_list) < MIN_CHANNELS:
        print("Not enough channels found, doing second pass with higher timeout...")
        remaining_urls = [(u,c) for u,c in url_channel_list if (u,c) not in valid_list]
        second_valid, second_results = await validate_urls(remaining_urls, SECOND_PASS_TIMEOUT)
        valid_list.extend(second_valid)
        results.extend(second_results)

    print(f"Total valid channels: {len(valid_list)}")
    write_m3u(valid_list, OUTPUT_FILE)
    write_log(results)
    print("Validation finished.")

if __name__ == "__main__":
    asyncio.run(main())
