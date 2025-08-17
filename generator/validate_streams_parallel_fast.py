# validate_streams_parallel_fast.py
import os
import glob
import concurrent.futures
import time
from pathlib import Path
import m3u8
import requests

# --- CONFIGURATION ---
LOCAL_M3U_DIR = r"C:\Users\berny\OneDrive\Documents\0000000000_PROJETS\M3U"
OUTPUT_DIR = "playlist"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "playlist_filtered.m3u")
LOG_FILE = "validation_log.txt"

# Timeout et passes
TIMEOUT_FIRST_PASS = 10
TIMEOUT_SECOND_PASS = 20
MAX_WORKERS = 25
MIN_CHANNELS_REQUIRED = 25

# Mots-clés principaux et variantes (5 max par chaîne)
KEYWORDS = {
    "TF1": ["TF1", "T F1", "TF-1", "TF_1", "La Une"],
    "France 2": ["France 2", "FR2", "France2", "F2", "Deux"],
    "France 3": ["France 3", "FR3", "France3", "F3", "Trois"],
    "France 4": ["France 4", "FR4", "France4", "F4", "Quatre"],
    "France 5": ["France 5", "FR5", "France5", "F5", "Cinq"],
    "M6": ["M6", "M 6", "M-6", "M_6", "Métropole 6"],
    "Arte": ["Arte", "ARTE", "AR-TE", "A R T E", "Arte TV"],
    "6TER": ["6TER", "6 Ter", "6-Ter", "6_Ter", "Sixter"],
    "W9": ["W9", "W 9", "W-9", "W_9", "W9 TV"],
    "TMC": ["TMC", "T M C", "T-M-C", "TMC TV", "Télé Monte Carlo"],
    "TFX": ["TFX", "T F X", "TF-X", "TFX TV", "TFX Channel"],
    "Chérie 25": ["Chérie 25", "Cherie25", "Cherie 25", "Ch25", "Chérie TV"],
    "RMC Story": ["RMC Story", "RMCStory", "RMC-S", "RMC Story TV", "RMC Story Channel"],
    "RMC Découverte": ["RMC Découverte", "RMC Decouverte", "RMC-D", "RMC Découv", "RMC Decouv"],
    "LCI": ["LCI", "La Chaîne Info", "LCI TV", "LC Info", "LCI News"],
    "BFM TV": ["BFM TV", "BFM", "BFM-TV", "BFM Info", "BFM News"],
    "CNews": ["CNews", "C News", "C-News", "iTélé", "Canal News"],
    "Franceinfo": ["Franceinfo", "France Info", "FInfo", "FranceInfo TV", "France-Info"],
    "LCP": ["LCP", "La Chaîne Parlementaire", "LCP TV", "LCP Info", "LCP-Info"],
    "Public Sénat": ["Public Sénat", "PubSenat", "PublicSenat", "PS TV", "Senat TV"],
    "CANAL+": ["CANAL+", "Canal Plus", "Canal+", "Canal+", "Canal+"],
    "Paris Première": ["Paris Première", "Paris Premiere", "Paris 1", "Paris1", "PP TV"],
    "Téva": ["Téva", "Teva", "Téva TV", "T Eva", "TV Téva"],
    "TV Breizh": ["TV Breizh", "TVBreizh", "TV-Breizh", "TV_Breizh", "Breizh TV"],
    "Gulli": ["Gulli", "Gulli TV", "GulliTV", "Gulli-France", "Gulli Channel"],
    "Canal J": ["Canal J", "CanalJ", "Canal-J", "CanalJ TV", "Canal Junior"],
    "CStar": ["CStar", "C Star", "C-Star", "CStar TV", "CStar Channel"],
    "TV5 Monde": ["TV5 Monde", "TV5Monde", "TV5", "TV5-Monde", "TV5-TV"],
    "France 24": ["France 24", "FR24", "France24", "F24", "France Twenty4"],
    "TVA": ["TVA", "TVA Québec", "TVA Québec", "TVA-TV", "TVA Canada"],
    "LCN": ["LCN", "LCN TV", "LCN-Info", "LCN News", "LCN Channel"],
    "Noovo": ["Noovo", "Noovo TV", "Noovo-Québec", "Noovo Channel", "Noovo Canada"],
    # 👉 tu peux ajouter d'autres chaînes ici
}

# --- FONCTIONS ---
def log(message):
    print(message)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message + "\n")

def find_m3u_files(folder):
    return sorted(glob.glob(os.path.join(folder, "**", "*.m3u"), recursive=True))

def parse_m3u(file_path):
    urls = []
    try:
        playlist = m3u8.load(file_path)
        for seg in playlist.segments:
            urls.append(str(seg.uri))
    except Exception:
        # Si le fichier est un M3U simple (texte)
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("http"):
                    urls.append(line.strip())
    return urls

def matches_keywords(name):
    name_lower = name.lower()
    for kw_list in KEYWORDS.values():
        for kw in kw_list:
            if kw.lower() in name_lower:
                return True
    return False

def validate_url(url, timeout):
    try:
        r = requests.head(url, timeout=timeout)
        if r.status_code == 200:
            return True
        return False
    except Exception:
        return False

def process_urls(urls, timeout):
    valid = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(validate_url, u, timeout): u for u in urls}
        for i, fut in enumerate(concurrent.futures.as_completed(future_to_url), 1):
            url = future_to_url[fut]
            try:
                if fut.result():
                    log(f"VALID: {url}")
                    valid.append(url)
                else:
                    log(f"INVALID: {url}")
            except Exception as e:
                log(f"ERROR: {url} -> {e}")
            if i % 10 == 0:
                log(f"Progress: {i}/{len(urls)} URLs processed")
    return valid

def run_validation():
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    all_files = find_m3u_files(LOCAL_M3U_DIR)
    log(f"Found {len(all_files)} M3U files locally.")

    all_urls = []
    for f in all_files[:25]:  # 1ère passe, max 25 fichiers
        all_urls.extend(parse_m3u(f))

    # Filtrage par mots-clés uniquement
    filtered_urls = [u for u in all_urls if matches_keywords(u)]
    log(f"URLs after keyword filtering: {len(filtered_urls)}")

    # Validation
    valid_urls = process_urls(filtered_urls, TIMEOUT_FIRST_PASS)

    # Si moins de MIN_CHANNELS_REQUIRED, deuxième passe
    if len(valid_urls) < MIN_CHANNELS_REQUIRED and len(all_files) > 25:
        remaining_files = all_files[25:25+25]
        second_pass_urls = []
        for f in remaining_files:
            second_pass_urls.extend(parse_m3u(f))
        second_pass_filtered = [u for u in second_pass_urls if matches_keywords(u)]
        log(f"Second pass URLs after keyword filtering: {len(second_pass_filtered)}")
        second_pass_valid = process_urls(second_pass_filtered, TIMEOUT_SECOND_PASS)
        valid_urls.extend(second_pass_valid)

    # Écriture playlist finale
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for url in valid_urls:
            f.write(url + "\n")
    log(f"Total valid URLs: {len(valid_urls)}")
    log("Validation finished.")

if __name__ == "__main__":
    run_validation()
