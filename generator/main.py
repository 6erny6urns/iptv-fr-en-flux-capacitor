import os
import requests

DATA_DIR = "data"
PLAYLIST_DIR = "playlist"
SOURCES_FILE = os.path.join(DATA_DIR, "sources.csv")
OUTPUT_FILE = os.path.join(PLAYLIST_DIR, "playlist.m3u")

def download_and_parse(url):
    print(f"Téléchargement et parsing : {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        print(f"Contenu téléchargé {len(response.text)} caractères")
        return response.text
    except requests.RequestException as e:
        print(f"Erreur téléchargement {url}: {e}")
        return ""

def main():
    if not os.path.exists(PLAYLIST_DIR):
        os.makedirs(PLAYLIST_DIR)

    if not os.path.exists(DATA_DIR):
        print(f"Le dossier {DATA_DIR} est introuvable.")
        return

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    playlist_content = "#EXTM3U\n"

    for url in urls:
        content = download_and_parse(url)
        playlist_content += content + "\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(playlist_content)

    print(f"Playlist générée : {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
