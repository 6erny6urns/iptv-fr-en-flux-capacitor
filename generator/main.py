import os
import requests

SRC_CSV = os.path.join("data", "sources.csv")
OUT_DIR = "playlist"
OUT_FILE = os.path.join(OUT_DIR, "playlist.m3u")

def download_playlist(url):
    print(f"Téléchargement et parsing : {url}")
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.text

def main():
    if not os.path.isfile(SRC_CSV):
        print(f"Erreur : fichier source {SRC_CSV} introuvable.")
        return
    os.makedirs(OUT_DIR, exist_ok=True)
    all_entries = []
    with open(SRC_CSV, "r") as f:
        urls = [line.strip() for line in f if line.strip()]
    for url in urls:
        try:
            content = download_playlist(url)
            all_entries.append(content)
            print(f"Contenu téléchargé {len(content)} caractères")
        except Exception as e:
            print(f"Erreur téléchargement {url}: {e}")
    # Concaténer toutes les playlists sources
    combined = "#EXTM3U\n"
    for content in all_entries:
        # On enlève la ligne #EXTM3U des contenus pour éviter doublons
        lines = content.splitlines()
        filtered_lines = [l for l in lines if not l.startswith("#EXTM3U")]
        combined += "\n".join(filtered_lines) + "\n"
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(combined)
    print(f"Playlist générée : {OUT_FILE}")

if __name__ == "__main__":
    main()
