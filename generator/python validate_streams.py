import csv
import concurrent.futures
import requests
from pathlib import Path

# Chemins
BASE_DIR = Path(__file__).resolve().parent.parent
SOURCES_FILE = BASE_DIR / "sources.csv"
OUTPUT_FILE = BASE_DIR / "playlist_filtered.m3u"
LOG_FILE = BASE_DIR / "validation_log.txt"

TIMEOUT = 3  # secondes
MAX_WORKERS = 50  # nombre de threads en parallèle

def check_stream(url):
    """Teste si un flux est actif avec une requête HEAD."""
    try:
        r = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code < 400:
            return url, True
    except Exception:
        pass
    return url, False

def main():
    # Lire les sources
    if not SOURCES_FILE.exists():
        print(f"❌ Fichier {SOURCES_FILE} introuvable.")
        return

    with open(SOURCES_FILE, newline='', encoding="utf-8") as f:
        reader = csv.reader(f)
        urls = [row[0].strip() for row in reader if row]

    print(f"🔍 {len(urls)} flux à tester...")

    valid_urls = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(check_stream, urls)

        with open(LOG_FILE, "w", encoding="utf-8") as log:
            for url, is_valid in results:
                if is_valid:
                    valid_urls.append(url)
                    log.write(f"[OK] {url}\n")
                else:
                    log.write(f"[FAIL] {url}\n")

    # Écrire le M3U filtré
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for url in valid_urls:
            f.write(f"#EXTINF:-1,{url}\n{url}\n")

    print(f"✅ {len(valid_urls)} flux valides enregistrés dans {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
