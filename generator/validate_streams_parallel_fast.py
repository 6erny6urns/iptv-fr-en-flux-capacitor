import os
import csv
import sys
import requests
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# CONFIGURATION
INPUT_CSV = "data/sources.csv"
TOP_CHANNELS_FILE = "top_channels.txt"
TOP_CITIES_FILE = "cities_top50.txt"
OUTPUT_DIR = "playlist"
OUTPUT_PLAYLIST = os.path.join(OUTPUT_DIR, "playlist_filtered.m3u")
LOG_FILE = "validation_log.txt"
TIMEOUT_FFPROBE = 2  # secondes
MAX_WORKERS = 25
HEAD_TIMEOUT = 0.5  # secondes pour pré-filtrage rapide

# Chargement des chaînes et villes
def load_list(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip() and not line.startswith("#")]

TOP_CHANNELS = load_list(TOP_CHANNELS_FILE)
TOP_CITIES = load_list(TOP_CITIES_FILE)

# Vérifie que ffprobe est présent
def check_ffprobe():
    try:
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False

# Télécharge le M3U et retourne les lignes
def download_m3u(url):
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return resp.text.splitlines()
    except Exception:
        return []

# Extraire URLs à partir du CSV
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

# Récursion pour extraire tous les flux directs
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

# Pré-filtrage HTTP HEAD rapide
def url_alive(url):
    try:
        resp = requests.head(url, timeout=HEAD_TIMEOUT)
        return resp.status_code < 400
    except Exception:
        return False

# Validation ffprobe
def validate_stream(url):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=format_name",
             "-of", "default=nw=1", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT_FFPROBE,
            text=True
        )
        output = result.stdout.lower()
        return "format_name=" in output
    except Exception:
        return False

# Filtre par chaînes et villes
def matches_top_channels_and_cities(name):
    name_lower = name.lower()
    return any(tc in name_lower for tc in TOP_CHANNELS) and any(city in name_lower for city in TOP_CITIES)

# Validation parallèle ultra-rapide
def main():
    if not check_ffprobe():
        print("ERROR: ffprobe not found or not executable. Please install ffprobe.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    sources = extract_urls(INPUT_CSV)
    all_streams = []
    for name, url in sources:
        all_streams.extend(parse_m3u_recursive(url, name))

    # Filtrer par top channels/cities
    all_streams = [(name, url) for name, url in all_streams if matches_top_channels_and_cities(name)]
    total_streams = len(all_streams)

    valid_streams = []
    with open(LOG_FILE, "w", encoding="utf-8") as logf, ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for name, url in all_streams:
            if url_alive(url):
                futures[executor.submit(validate_stream, url)] = (name, url)
            else:
                logf.write(f"SKIPPED (dead URL): {name} -> {url}\n")

        for i, future in enumerate(as_completed(futures), 1):
            name, url = futures[future]
            try:
                valid = future.result()
            except Exception:
                valid = False
            if valid:
                valid_streams.append(f"#EXTINF:-1,{name}\n{url}\n")
                logf.write(f"VALID [{i}/{total_streams}]: {name} -> {url}\n")
                print(f"VALID [{i}/{total_streams}]: {name}")
            else:
                logf.write(f"INVALID [{i}/{total_streams}]: {name} -> {url}\n")
                print(f"INVALID [{i}/{total_streams}]: {name}")

        logf.write(f"Total valid streams: {len(valid_streams)}\n")

    # Génération playlist
    with open(OUTPUT_PLAYLIST, "w", encoding="utf-8") as outf:
        outf.write("#EXTM3U\n")
        for entry in valid_streams:
            outf.write(entry)

    # Copier au root
    cp_root = os.path.join(os.getcwd(), "playlist.m3u")
    with open(cp_root, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for entry in valid_streams:
            f.write(entry)

    print(f"\nValidation complete. {len(valid_streams)} valid streams saved to '{OUTPUT_PLAYLIST}' and '{cp_root}'")
    print(f"Log file: '{LOG_FILE}'")

if __name__ == "__main__":
    main()
