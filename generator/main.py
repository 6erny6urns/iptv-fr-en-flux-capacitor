import os
import requests
import logging
import time

SOURCES_FILE = 'data/sources.csv'
OUTPUT_DIR = 'playlist'
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'playlist.m3u')
LOG_FILE = 'log_update.txt'

# Timeout en secondes pour test URL flux
STREAM_TIMEOUT = 8

def download_playlist(url):
    try:
        logging.info(f"Téléchargement de la source : {url}")
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        logging.info(f"Source téléchargée : {url} ({len(resp.text)} caractères)")
        return resp.text
    except Exception as e:
        logging.error(f"Erreur téléchargement {url}: {e}")
        return None

def parse_m3u_entries(content):
    entries = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('#EXTINF:'):
            extinf = line
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                entries.append((extinf, url))
                i += 2
            else:
                i += 1
        else:
            i += 1
    return entries

def test_stream(url):
    try:
        # Requête HEAD ou GET partielle pour vérifier flux
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=STREAM_TIMEOUT, stream=True)
        resp.raise_for_status()
        # Vérifie le type de contenu comme un indice (ex: video, audio)
        content_type = resp.headers.get('Content-Type','')
        if any(x in content_type for x in ['video', 'audio', 'mpeg', 'octet-stream']):
            logging.info(f"Flux valide : {url}")
            resp.close()
            return True
        else:
            logging.warning(f"Flux rejeté (type non compatible) : {url}")
            resp.close()
            return False
    except Exception as e:
        logging.warning(f"Flux non valide ou inaccessible : {url} ({e})")
        return False

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    logging.info("Début du script main.py")

    if not os.path.isfile(SOURCES_FILE):
        logging.error(f"Fichier sources introuvable : {SOURCES_FILE}")
        return

    with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    all_entries = []

    for url in urls:
        content = download_playlist(url)
        if content:
            entries = parse_m3u_entries(content)
            logging.info(f"{len(entries)} chaînes extraites de {url}")
            all_entries.extend(entries)
        time.sleep(1)  # anti-spam

    logging.info(f"Total brut de chaînes avant test : {len(all_entries)}")

    # Test validité des flux, filtrage
    valid_entries = []
    for extinf, stream_url in all_entries:
        if test_stream(stream_url):
            valid_entries.append((extinf, stream_url))

    logging.info(f"Total chaînes valides après test : {len(valid_entries)}")

    # Ecriture fichier playlist brute validée
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for extinf, url in valid_entries:
            f.write(f"{extinf}\n{url}\n")

    logging.info(f"Playlist brute validée écrite : {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
