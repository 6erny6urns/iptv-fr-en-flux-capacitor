import os
import requests

SOURCES_FILE = "data/sources.csv"
PLAYLIST_FILE = "playlist/playlist.m3u"

def download_and_parse(url):
    print(f"Téléchargement et parsing : {url}")
    try:
        r = requests.get(url)
        r.raise_for_status()
        content = r.text
        print(f"Contenu téléchargé {len(content)} caractères")
        return content
    except requests.RequestException as e:
        print(f"Erreur téléchargement {url}: {e}")
        return ""

def main():
    if not os.path.exists("playlist"):
        os.makedirs("playlist")

    playlist_entries = []
    with open(SOURCES_FILE, "r") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    for url in urls:
        content = download_and_parse(url)
        if content:
            playlist_entries.append(content)

    combined = "#EXTM3U\n" + "\n".join(playlist_entries)

    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        f.write(combined)

    print(f"Playlist générée : {PLAYLIST_FILE}")

if __name__ == "__main__":
    main()
