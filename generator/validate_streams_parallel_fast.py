# generator/validate_streams_parallel_fast.py
import os
import csv
import time
import concurrent.futures
from pathlib import Path
import requests

# --- CONFIGURATION ---
LOCAL_M3U_DIR = r"C:\Users\berny\OneDrive\Documents\0000000000_PROJETS\M3U"
OUTPUT_DIR = "playlist"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "playlist_filtered.m3u")
LOG_FILE = "validation_log.txt"

# Timeout initial et progressif
INITIAL_TIMEOUT = 10  # secondes
MAX_TIMEOUT = 20

# Nombre minimal de chaînes pour 1ère passe
MIN_CHANNELS = 25
MAX_WORKERS = 25

# Fichier CSV mots-clés des chaînes (modifiable par l’utilisateur)
KEYWORDS_FILE = "data/channels_keywords.csv"

# --- FONCTIONS ---
def load_keywords(csv_file):
    keywords = {}
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"{csv_file} introuvable")
    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            main = row["Channel"]
            variants = [row[f"Keyword{i}"] for i in range(1,6) if row.get(f"Keyword{i}")]
            keywords[main] = variants
    return keywords

def find_m3u_files(local_dir):
    """Scan récursif pour trouver tous les fichiers .m3u"""
    m3u_files = list(Path(local_dir).rglob("*.m3u"))
    return m3u_files

def parse_m3u(file_path):
    """Récupère toutes les URLs du fichier M3U"""
    urls = []
    try:
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)
    except Exception as e:
        print(f"Erreur lecture {file_path}: {e}")
    return urls

def filter_urls(urls, keywords):
    """Garde uniquement les URLs dont le titre match un mot clé"""
    filtered = []
    for url in urls:
        url_lower = url.lower()
        for kw_list in keywords.values():
            for kw in kw_list:
                if kw.lower() in url_lower:
                    filtered.append(url)
                    break
    return filtered

def validate_url(url, timeout):
    """Validation simple : HTTP HEAD puis GET si nécessaire"""
    try:
        r = requests.head(url, timeout=timeout, allow_redirects=True)
        if r.status_code == 200:
            return url
        else:
            # tentative GET si HEAD échoue
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:
                return url
    except:
        return None
    return None

def process_urls(urls, timeout):
    valid_urls = []
    total = len(urls)
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(validate_url, url, timeout): url for url in urls}
        for i, future in enumerate(concurrent.futures.as_completed(future_to_url), 1):
            result = future.result()
            url = future_to_url[future]
            if result:
                valid_urls.append(result)
                status = "VALID"
            else:
                status = "INVALID"
            elapsed = time.time() - start_time
            pct = int(i / total * 100)
            print(f"[{pct}%] {url} -> {status} ({i}/{total}) - {elapsed:.1f}s")
            with open(LOG_FILE, "a", encoding="utf-8") as logf:
                logf.write(f"{url},{status}\n")
    return valid_urls

# --- MAIN ---
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    print("Chargement mots-clés...")
    keywords = load_keywords(KEYWORDS_FILE)
    
    # Passe 1 : scan initial
    print("Recherche fichiers M3U locaux...")
    m3u_files = find_m3u_files(LOCAL_M3U_DIR)
    print(f"{len(m3u_files)} fichiers M3U trouvés.")
    
    all_urls = []
    for f in m3u_files[:MIN_CHANNELS]:  # ne prendre que les 25 premiers pour la 1ère passe
        urls = parse_m3u(f)
        all_urls.extend(urls)
    
    urls_filtered = filter_urls(all_urls, keywords)
    print(f"{len(urls_filtered)} URLs après filtrage mots-clés.")
    
    if urls_filtered:
        print("Validation des URLs (timeout initial)...")
        valid_urls = process_urls(urls_filtered, INITIAL_TIMEOUT)
    else:
        valid_urls = []
    
    # Passe 2 si moins de MIN_CHANNELS trouvées
    if len(valid_urls) < MIN_CHANNELS and len(m3u_files) > MIN_CHANNELS:
        print("Moins de 25 chaînes trouvées, passe 2 sur fichiers restants...")
        remaining_files = m3u_files[MIN_CHANNELS:]
        all_urls2 = []
        for f in remaining_files[:MIN_CHANNELS]:
            urls = parse_m3u(f)
            all_urls2.extend(urls)
        urls_filtered2 = filter_urls(all_urls2, keywords)
        if urls_filtered2:
            valid_urls2 = process_urls(urls_filtered2, MAX_TIMEOUT)
            valid_urls.extend(valid_urls2)
    
    # Sortie finale
    valid_urls = list(set(valid_urls))  # supprimer doublons
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write("#EXTM3U\n")
        for url in valid_urls:
            out.write(f"{url}\n")
    print(f"Validation terminée. Total flux valides: {len(valid_urls)}")
    print(f"Playlist finale: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
