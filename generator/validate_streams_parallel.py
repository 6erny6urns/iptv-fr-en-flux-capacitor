import os
import sys
import csv
import requests
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# CONFIGURATION
INPUT_CSV = "data/sources.csv"
CITIES_FILE = "data/cities_top50.txt"
CHANNELS_FILE = "data/top_channels.txt"
OUTPUT_DIR = "playlist"
OUTPUT_PLAYLIST = os.path.join(OUTPUT_DIR, "playlist_filtered.m3u")
LOG_FILE = os.path.join(OUTPUT_DIR, "validation_log.txt")
TIMEOUT = 3  # secondes pour ffprobe
MAX_WORKERS = 25

# Lire la liste des villes et chaînes
with open(CITIES_FILE, encoding="utf-8") as f:
    cities = [line.strip().lower() for line in f if line.strip()]
with open(CHANNELS_FILE, encoding="utf-8") as f:
    channels = [line.strip().lower() for line in f if line.strip()]

def check_ffprobe():
    try:
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False

def download_m3u(url):
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        return r.text.splitlines()
    except Exception:
        return []

def extract_urls(csv_path):
    if not os.path.isfile(csv_path):
        print(f"CSV source file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    urls = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "url" in row and row["url"].strip():
                name = row.get("name", "UNKNOWN").strip()
                url = row["url"].strip()
                urls.append((name, url))
    return urls

def parse_m3u_recursive(url, parent_name):
    urls = []
    lines = download_m3u(url)
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().endswith((".m3u", ".m3u8")):
            urls.extend(parse_m3u_recursive(line, parent_name))
        elif line.startswith("http"):
            urls.append((parent_name, line))
    return urls

def filter_target_streams(all_streams):
    """Filtre par villes et chaînes cibles (correspondances partielles, insensible à la casse)"""
    filtered = []
    for name, url in all_streams:
        lname = name.lower()
        lurl = url.lower()
        if any(c in lname or c in lurl for c in cities) and any(ch in lname for ch in channels):
            filtered.append((name, url))
    return filtered

def http_head_alive(url):
    try:
        r = requests.head(url, timeout=0.5, allow_redirects=True)
        return r.status_code < 400
    except Exception:
        return False

def validate_stream(url):
    if not http_head_alive(url):
        return False
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=format_name",
             "-of", "default=nw=1", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT,
            text=True
        )
        return "format_name=" in result.stdout.lower()
    except Exception:
        return False

def main():
    if not check_ffprobe():
        print("ERROR: ffprobe not found. Install ffmpeg/ffprobe.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    sources = extract_urls(INPUT_CSV)
    all_streams = []
    for name, url in sources:
        all_streams.extend(parse_m3u_recursive(url, name))

    filtered_streams = filter_target_streams(all_streams)

    valid_streams = []
    total = len(filtered_streams)

    with open(LOG_FILE, "w", encoding="utf-8") as logf:
        logf.write(f"Starting validation of {total} streams...\n")
        print(f"Starting validation of {total} streams...")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_stream = {executor.submit(validate_stream, url): (name, url) for name, url in filtered_streams}
            for i, future in enumerate(as_completed(future_to_stream), 1):
                name, url = future_to_stream[future]
                try:
                    result = future.result()
                except Exception:
                    result = False

                status = "VALID" if result else "INVALID"
                logf.write(f"Testing [{i}/{total}]: {name} ... {status}\n")
                print(f"Testing [{i}/{total}]: {name} ... {status}")

                if result:
                    valid_streams.append(f"#EXTINF:-1,{name}\n{url}\n")

        logf.write(f"Total valid streams: {len(valid_streams)}\n")
        print(f"Total valid streams: {len(valid_streams)}")

    with open(OUTPUT_PLAYLIST, "w", encoding="utf-8") as outf:
        outf.write("#EXTM3U\n")
        for entry in valid_streams:
            outf.write(entry)

    # Copier au root pour GitHub Pages
    cp_root = "playlist.m3u"
    with open(cp_root, "w", encoding="utf-8") as outf:
        outf.write("#EXTM3U\n")
        for entry in valid_streams:
            outf.write(entry)

    print(f"Playlist generated: {OUTPUT_PLAYLIST}")
    print(f"Playlist for GitHub Pages: {cp_root}")
    print(f"Validation log: {LOG_FILE}")

if __name__ == "__main__":
    main()
