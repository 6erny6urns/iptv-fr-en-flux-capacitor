import csv
import os
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Constants
DATA_DIR = "data"
PLAYLIST_DIR = "playlist"
SOURCES_FILE = os.path.join(DATA_DIR, "sources.csv")
OUTPUT_FILE = os.path.join(PLAYLIST_DIR, "playlist_filtered.m3u")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; IPTVUpdater/1.0)"
}

# Validation timeout
REQUEST_TIMEOUT = 5
MAX_WORKERS = 10  # pour multithread

def read_sources(csv_path):
    urls = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get('url')
            if url:
                urls.append(url.strip())
    return urls

def download_m3u(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200 and resp.text.strip():
            return resp.text
    except Exception:
        pass
    return ""

def parse_m3u(m3u_content):
    """
    Parse le contenu M3U en liste de dict {meta, url}.
    Ignore les lignes non conformes.
    """
    lines = m3u_content.splitlines()
    channels = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            meta = line
            url = ""
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
            channels.append({"meta": meta, "url": url})
            i += 2
        else:
            i += 1
    return channels

def validate_url(url):
    """
    Valide la chaîne IPTV en faisant une requête HEAD (ou GET courte).
    Retourne True si accessible (status 200-299).
    """
    try:
        # Essayer une requête HEAD
        resp = requests.head(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if resp.status_code >= 200 and resp.status_code < 300:
            return True
        # Sinon, fallback GET partiel
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, stream=True)
        if resp.status_code >= 200 and resp.status_code < 300:
            # Lecture partielle
            chunk = resp.raw.read(1024)
            return True if chunk else False
    except Exception:
        pass
    return False

def filter_channels(channels):
    """
    Filtre les chaînes valides (url testées).
    """
    valid_channels = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_channel = {executor.submit(validate_url, ch["url"]): ch for ch in channels}
        for future in as_completed(future_to_channel):
            ch = future_to_channel[future]
            try:
                if future.result():
                    valid_channels.append(ch)
            except Exception:
                pass
    return valid_channels

def categorize_channel(meta_line):
    """
    Extrait les catégories / pays / langue depuis #EXTINF meta.
    Peut être amélioré selon normes IPTV.
    """
    country = re.search(r'tvg-country="([^"]+)"', meta_line)
    language = re.search(r'tvg-language="([^"]+)"', meta_line)
    group_title = re.search(r'group-title="([^"]+)"', meta_line)

    return {
        "country": country.group(1) if country else "",
        "language": language.group(1) if language else "",
        "group": group_title.group(1) if group_title else ""
    }

def write_playlist(channels, output_file):
    """
    Écrit la playlist M3U valide et catégorisée.
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in channels:
            f.write(ch["meta"] + "\n")
            f.write(ch["url"] + "\n")

def main():
    print("Lecture des sources...")
    urls = read_sources(SOURCES_FILE)
    print(f"{len(urls)} sources chargées.")

    all_channels = []
    print("Téléchargement des playlists sources...")
    for url in urls:
        print(f" - {url}")
        m3u_content = download_m3u(url)
        if m3u_content:
            chans = parse_m3u(m3u_content)
            all_channels.extend(chans)
    print(f"{len(all_channels)} chaînes extraites au total.")

    print("Validation des flux...")
    valid_channels = filter_channels(all_channels)
    print(f"{len(valid_channels)} chaînes valides.")

    # Optionnel : on pourrait filtrer / regrouper par catégorie / pays ici

    print(f"Écriture de la playlist filtrée dans {OUTPUT_FILE} ...")
    write_playlist(valid_channels, OUTPUT_FILE)
    print("Terminé.")

if __name__ == "__main__":
    main()
