import csv
import os
import sys
import requests
import subprocess
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# --- CONFIGURATION ---
INPUT_CSV = "data/sources.csv"
TOP_CHANNELS_FILE = "data/top_channels.txt"
TOP_CITIES_FILE = "data/top_cities50.txt"
OUTPUT_DIR = "playlist"
OUTPUT_PLAYLIST = os.path.join(OUTPUT_DIR, "playlist_filtered.m3u")
LOG_FILE = "validation_log.txt"
TIMEOUT = 3  # secondes pour ffprobe
MAX_WORKERS = 25

# --- UTILS ---
def check_ffprobe():
    try:
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False

def download_m3u(url):
    try:
        resp = requests.get(url, timeout=5)
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

def load_list_file(path):
    if not os.path.isfile(path):
        print(f"ERROR: List file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip()]

def url_alive(url):
    try:
        resp = requests.head(url, timeout=1, allow_redirects=True)
        return resp.status_code == 200
    except Exception:
        return False

def validate_stream(url):
    if not url_alive(url):
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
        output = result.stdout.lower()
        if "format_name=" in output:
            return True
    except Exception:
        pass
    return False

# --- MAIN ---
def main():
    if not check_ffprobe():
        print("ERROR: ffprobe not found or not executable. Install ffprobe.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    top_channels = load_list_file(TOP_CHANNELS_FILE)
    top_cities = load_list_file(TOP_CITIES_FILE)

    sources = extract_urls(INPUT_CSV)
    all_streams = []

    # Extraire tous les flux directs à partir des M3U
    for name, url in sources:
        # Filtrer uniquement les chaînes et villes ciblées
        if any(tc in name.lower() for tc in top_channels) or any(city in name.lower() for city in top_cities):
            all_streams.extend(parse_m3u_recursive(url, name))

    if not all_streams:
        print("Aucun flux trouvé correspondant aux chaînes et villes ciblées.")
        return

    valid_streams = []
    total_streams = len(all_streams)

    # Compteurs pour affichage temps réel
    valid_count = 0
    invalid_count = 0
    lock = threading.Lock()

    with open(LOG_FILE, "w", encoding="utf-8") as logf, ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(validate_stream, url): (name, url) for name, url in all_streams}

        for i, future in enumerate(as_completed(futures), 1):
            name, url = futures[future]
            try:
                valid = future.result()
            except Exception:
                valid = False

            with lock:
                if valid:
                    valid_streams.append(f"#EXTINF:-1,{name}\n{url}\n")
                    valid_count += 1
                    status = "VALID"
                else:
                    invalid_count += 1
                    status = "INVALID"

                print(f"[{i}/{total_streams}] {status}: {name} | Valid: {valid_count} | Invalid: {invalid_count}")
                logf.write(f"{status} [{i}/{total_streams}]: {name} -> {url}\n")

    # Génération playlist M3U
    with open(OUTPUT_PLAYLIST, "w", encoding="utf-8") as outf:
        outf.write("#EXTM3U\n")
        for entry in valid_streams:
            outf.write(entry)

    # Copier au root pour GitHub Pages
    try:
        os.replace(OUTPUT_PLAYLIST, "playlist.m3u")
    except Exception:
        pass

    print(f"\nValidation terminée. {len(valid_streams)} flux valides sauvegardés.")
    print(f"Log: {LOG_FILE}")

if __name__ == "__main__":
    main()
