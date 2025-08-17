import os
import csv
import requests
import concurrent.futures
from pathlib import Path

# --- CONFIGURATION ---
MIN_REQUIRED = 25
MAX_ATTEMPTS = 2
TIMEOUTS = [10, 20]  # 10s puis 20s
INPUT_CSV = "data/sources.csv"
LOCAL_DIR = r"C:\Users\berny\OneDrive\Documents\0000000000_PROJETS\M3U"
KEYWORDS_CSV = "data/channels_keywords.csv"
OUTPUT_M3U = "finale.m3u"

# --- Charger mots-clés depuis CSV ---
def load_keywords(csv_file):
    keywords = {}
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"Fichier keywords introuvable : {csv_file}")
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            channel = row[0].strip()
            variants = [r.strip() for r in row[1:] if r.strip()]
            keywords[channel] = variants
    return keywords

KEYWORDS = load_keywords(KEYWORDS_CSV)

# --- Sources ---
def load_sources_online():
    urls = []
    if os.path.exists(INPUT_CSV):
        with open(INPUT_CSV, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("http"):
                    urls.append(line)
    return urls

def load_sources_local(limit=25):
    m3u_files = list(Path(LOCAL_DIR).rglob("*.m3u"))
    m3u_files = m3u_files[:limit]
    urls = []
    for file in m3u_files:
        with open(file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("http"):
                    urls.append(line)
    return urls

# --- Téléchargement et validation ---
def fetch_playlist(url, timeout):
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text.splitlines()
    except Exception:
        return []

def validate_stream(url, timeout):
    for t in TIMEOUTS:
        try:
            resp = requests.get(url, stream=True, timeout=t)
            if resp.status_code == 200:
                return True
        except Exception:
            continue
    return False

# --- Filtrage par mots-clés ---
def filter_by_keywords(lines):
    results = []
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF"):
            for channel, variants in KEYWORDS.items():
                if any(v.lower() in line.lower() for v in variants):
                    if i + 1 < len(lines):
                        url = lines[i + 1].strip()
                        results.append((channel, line, url))
    return results

# --- MAIN ---
def main():
    all_results = []
    found_channels = set()

    for attempt in range(MAX_ATTEMPTS):
        print(f"\n--- Tentative {attempt+1} ---")
        urls = load_sources_online() if attempt == 0 else load_sources_local()
        if not urls:
            print("⚠️ Aucune source trouvée.")
            continue

        temp_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_playlist, u, TIMEOUTS[0]): u for u in urls}
            for future in concurrent.futures.as_completed(futures):
                lines = future.result()
                if lines:
                    temp_results.extend(filter_by_keywords(lines))

        valid_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(validate_stream, url, TIMEOUTS[0]): (ch, info, url) for ch, info, url in temp_results}
            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    ch, info, url = futures[future]
                    if ch not in found_channels:
                        valid_results.append((ch, info, url))
                        found_channels.add(ch)

        all_results.extend(valid_results)
        print(f"Chaînes valides cumulées : {len(all_results)}")
        if len(all_results) >= MIN_REQUIRED:
            break

    # Écriture du fichier final
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch, info, url in all_results:
            f.write(f"{info}\n{url}\n")

    print(f"\n✅ Résultat final : {len(all_results)} chaînes valides trouvées.")
    print("📌 Liste des chaînes trouvées :")
    for ch, _, _ in all_results:
        print(f"- {ch}")

if __name__ == "__main__":
    main()
