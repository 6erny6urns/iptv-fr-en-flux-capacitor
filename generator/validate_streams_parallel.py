import csv
import os
import subprocess
import sys
import requests
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
INPUT_CSV = "data/sources.csv"
OUTPUT_DIR = "playlist"
OUTPUT_PLAYLIST = os.path.join(OUTPUT_DIR, "playlist_filtered.m3u")
LOG_FILE = "validation_log.txt"
TIMEOUT = 15  # secondes pour ffprobe
MAX_WORKERS = 8  # nombre de threads pour validation parallèle

# Vérifie la présence de ffprobe
def check_ffprobe():
    try:
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False

# Télécharge un M3U et retourne les lignes
def download_m3u(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.text.splitlines()
    except Exception:
        return []

# Extrait les URLs depuis le CSV
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

# Récursion pour M3U imbriqués
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

# Validation d'un flux avec ffprobe
def validate_stream(name_url):
    name, url = name_url
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
            return name, url, True
    except Exception:
        pass
    return name, url, False

def main():
    if not check_ffprobe():
        print("ERROR: ffprobe not found or not executable. Please install ffprobe.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    sources = extract_urls(INPUT_CSV)

    # Extraction récursive des flux
    all_streams = []
    for name, url in sources:
        all_streams.extend(parse_m3u_recursive(url, name))

    valid_streams = []

    # Validation parallèle
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor, open(LOG_FILE, "w", encoding="utf-8") as logf:
        future_to_stream = {executor.submit(validate_stream, s): s for s in all_streams}
        for i, future in enumerate(as_completed(future_to_stream), 1):
            name, url, valid = future.result()
            logf.write(f"Testing [{i}/{len(all_streams)}]: {name} ... {'VALID' if valid else 'INVALID'}\n")
            print(f"Testing [{i}/{len(all_streams)}]: {name} ... {'VALID' if valid else 'INVALID'}")
            if valid:
                valid_streams.append(f"#EXTINF:-1,{name}\n{url}\n")
        logf.write(f"Total valid streams: {len(valid_streams)}\n")

    # Écriture du fichier M3U
    with open(OUTPUT_PLAYLIST, "w", encoding="utf-8") as outf:
        outf.write("#EXTM3U\n")
        for entry in valid_streams:
            outf.write(entry)

    print(f"\nValidation complete. {len(valid_streams)} valid streams saved to '{OUTPUT_PLAYLIST}'.")
    print(f"Log file: '{LOG_FILE}'")

if __name__ == "__main__":
    main()

