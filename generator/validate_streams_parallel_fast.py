import os
import re
import requests
import concurrent.futures
from pathlib import Path

# --- CONFIGURATION ---
MIN_REQUIRED = 25
MAX_ATTEMPTS = 2
TIMEOUTS = [10, 20]  # 10s d’abord, puis 20s
INPUT_CSV = "data/sources.csv"  # URLs de playlists
LOCAL_DIR = r"C:\Users\berny\OneDrive\Documents\0000000000_PROJETS\M3U"
OUTPUT_M3U = "finale.m3u"

# Mots-clés principaux et variantes (5 max par mot clé)
KEYWORDS = {
    "TF1": ["TF1", "T F1", "TF-1", "TF_1", "La Une"],
    "France 2": ["France 2", "FR2", "France2", "F2", "Deux"],
    "France 3": ["France 3", "FR3", "France3", "F3", "Trois"],
    "M6": ["M6", "M 6", "M-6", "M_6", "Métropole 6"],
    "Arte": ["Arte", "ARTE", "ArteTV", "Arte-TV", "La Sept"],
    "Canal+": ["Canal+", "Canal Plus", "C+", "Canal+", "Canal_Plus"],
    "CNEWS": ["CNEWS", "C News", "C-News", "iTélé", "Canal News"],
    "LCI": ["LCI", "La Chaîne Info", "LCI-TV", "LCI_TV", "LCI Info"],
    "BFMTV": ["BFMTV", "BFM TV", "BFM-TV", "BFM_TV", "BFM"],
    "TV5": ["TV5", "TV5Monde", "TV 5", "TV-5", "TV_Cinq"],
    "RMC": ["RMC", "RMC Découverte", "RMC Story", "RMC-S", "RMC_D"],
    "France 24": ["France 24", "France24", "F24", "FR24", "France_VingtQuatre"],
    "Euronews": ["Euronews", "Euro news", "Euro-news", "ENews", "Euronews TV"],
    "CNN": ["CNN", "C N N", "CNN International", "CNNI", "CNN-Intl"],
    "BBC": ["BBC", "BBC News", "BBC-World", "BBC_World", "British Broadcasting"],
    "CTV": ["CTV", "C TV", "C-TV", "CTV Canada", "CTV_News"],
    "CBC": ["CBC", "CBC News", "CBC-TV", "Radio-Canada", "Canadian Broadcasting"],
    "Global": ["Global", "Global News", "Global-TV", "Global_TV", "Global Canada"]
}

# ---------------------------------------------------

def load_sources_online():
    """Charge les URLs depuis le fichier CSV sources."""
    urls = []
    if os.path.exists(INPUT_CSV):
        with open(INPUT_CSV, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and line.startswith("http"):
                    urls.append(line)
    return urls

def load_sources_local(limit=25):
    """Charge des fichiers M3U depuis un dossier local."""
    m3u_files = list(Path(LOCAL_DIR).rglob("*.m3u"))
    m3u_files = m3u_files[:limit]  # prend les 25 premiers
    urls = []
    for file in m3u_files:
        with open(file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("http"):
                    urls.append(line)
    return urls

def fetch_playlist(url, timeout):
    """Télécharge une playlist M3U et retourne les lignes valides."""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text.splitlines()
    except Exception:
        return []

def validate_stream(url, timeout):
    """Teste un flux avec un timeout progressif."""
    for t in TIMEOUTS:
        try:
            resp = requests.get(url, stream=True, timeout=t)
            if resp.status_code == 200:
                return True
        except Exception:
            continue
    return False

def filter_by_keywords(lines):
    """Garde uniquement les chaînes correspondant aux mots-clés définis."""
    results = []
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF"):
            for channel, variants in KEYWORDS.items():
                if any(v.lower() in line.lower() for v in variants):
                    if i + 1 < len(lines):
                        url = lines[i + 1].strip()
                        results.append((channel, line, url))
    return results

def main():
    all_results = []
    attempt = 0

    for attempt in range(MAX_ATTEMPTS):
        print(f"\n--- Tentative {attempt+1} ---")

        if attempt == 0:
            urls = load_sources_online()
        else:
            urls = load_sources_local()

        if not urls:
            print("⚠️ Aucune source trouvée.")
            continue

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(fetch_playlist, u, TIMEOUTS[0]): u for u in urls}
            for future in concurrent.futures.as_completed(future_to_url):
                lines = future.result()
                if lines:
                    all_results.extend(filter_by_keywords(lines))

        # Validation des flux trouvés
        valid_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(validate_stream, url, TIMEOUTS[0]): (ch, info, url) for ch, info, url in all_results}
            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    valid_results.append(futures[future])

        all_results = list({url: (ch, info, url) for ch, info, url in valid_results}.values())  # supprime doublons

        print(f"Chaînes valides trouvées après tentative {attempt+1}: {len(all_results)}")

        if len(all_results) >= MIN_REQUIRED:
            break

    # Écriture du fichier final
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch, info, url in all_results:
            f.write(f"{info}\n{url}\n")

    print(f"\n✅ Résultat final : {len(all_results)} chaînes valides trouvées.")
    print(f"📂 Playlist générée : {OUTPUT_M3U}")


if __name__ == "__main__":
    main()
