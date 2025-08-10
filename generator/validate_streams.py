import csv
import concurrent.futures
import requests
from pathlib import Path

# Chemins
BASE_DIR = Path(__file__).resolve().parent.parent
SOURCES_FILE = BASE_DIR / "sources.csv"
OUTPUT_FILE = BASE_DIR / "playlist_filtered.m3u"
LOG_FILE = BASE_DIR / "validation_log.txt"

TIMEOUT = 3       # secondes
MAX_WORKERS = 50  # threads parallèles

def check_stream(entry):
    """Teste si un flux est actif via requête HEAD."""
    url, name, group = entry
    try:
        r = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code < 400:
            return entry, True
    except Exception:
        pass
    return entry, False

def main():
    # Lecture CSV : url,name,group
    if not SOURCES_FILE.exists():
        print(f"❌ Fichier {SOURCES_FILE} introuvable.")
        return

    with open(SOURCES_FILE, newline='', encoding="utf-8") as f:
        reader = csv.reader(f)
        entries = [(row[0].strip(), row[1].strip() if len(row) > 1 else "No Name",
                    row[2].strip() if len(row) > 2 else "Misc")
                   for row in reader if row]

    print(f"🔍 {len(entries)} flux à tester...")

    valid_entries = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(check_stream, entries)

        with open(LOG_FILE, "w", encoding="utf-8") as log:
            for entry, is_valid in results:
                url, name, group = entry
                if is_valid:
                    valid_entries.append(entry)
                    log.write(f"[OK] {url} ({name}) [{group}]\n")
                else:
                    log.write(f"[FAIL] {url} ({name}) [{group}]\n")

    # Écriture M3U enrichi
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for url, name, group in valid_entries:
            f.write(f'#EXTINF:-1 group-title="{group}",{name}\n{url}\n')

    print(f"✅ {len(valid_entries)} flux valides enregistrés dans {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
