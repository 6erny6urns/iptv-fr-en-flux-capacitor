import csv
import os
import subprocess
import sys
import requests
from urllib.parse import urlparse

INPUT_CSV = "data/sources.csv"
OUTPUT_DIR = "playlist"
OUTPUT_PLAYLIST = os.path.join(OUTPUT_DIR, "playlist_filtered.m3u")
LOG_FILE = "validation_log.txt"
TIMEOUT = 15  # secondes pour ffprobe

def check_ffprobe():
    try:
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False

def download_m3u(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.text.splitlines()
    except Exception:
        return []

def extract_urls(csv_path):
    if not os.path.isfile(csv_path):
        print(f"ERROR: CSV source file not found: {csv_path}", file=sys.stderr)
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
        if line.lower().endswith(".m3u") or line.lower().endswith(".m3u8"):
            urls.extend(parse_m3u_recursive(line, parent_name))
        elif line.startswith("http"):
            urls.append((parent_name, line))
    return urls

def validate_stream(url):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=format_name",
             "-of", "default=nw=1", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT,
            text=True
        )
        output = result.stdout.lower()
        if "format_name=" in output:
            return True
    except Exception:
        pass
    return False

def main():
    if not check_ffprobe():
        print("ERROR: ffprobe not found or not executable.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    sources = extract_urls(INPUT_CSV)
    all_streams = []
    for name, url in sources:
        all_streams.extend(parse_m3u_recursive(url, name))

    valid_streams = []
    total = len(all_streams)

    with open(LOG_FILE, "w", encoding="utf-8") as logf:
        logf.write(f"Starting validation of {total} streams...\n")
        for i, (name, url) in enumerate(all_streams, 1):
            percent = (i / total) * 100
            print(f"[{i}/{total}] ({percent:.1f}%) Testing {name} ... ", end="", flush=True)
            logf.write(f"Testing [{i}/{total}]: {name} ... ")
            if validate_stream(url):
                print("VALID")
                logf.write("VALID\n")
                valid_streams.append(f"#EXTINF:-1,{name}\n{url}\n")
            else:
                print("INVALID")
                logf.write("INVALID\n")

        logf.write(f"Total valid streams: {len(valid_streams)}\n")

    with open(OUTPUT_PLAYLIST, "w", encoding="utf-8") as outf:
        outf.write("#EXTM3U\n")
        for entry in valid_streams:
            outf.write(entry)

    print(f"\nValidation complete. {len(valid_streams)} valid streams saved to '{OUTPUT_PLAYLIST}'.")
    print(f"Log file: '{LOG_FILE}'")

if __name__ == "__main__":
    main()
