import requests
import os

DATA_SOURCES = "data/sources.csv"
OUTPUT_PLAYLIST = "playlist/playlist.m3u"

def download_and_concat_playlists(urls):
    all_lines = ["#EXTM3U\n"]
    for url in urls:
        url = url.strip()
        if not url:
            continue
        print(f"Téléchargement et parsing : {url}")
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            content = r.text
            # Ignorer la première ligne #EXTM3U de chaque playlist pour éviter doublons
            lines = content.splitlines()
            if lines[0].startswith("#EXTM3U"):
                lines = lines[1:]
            all_lines.extend(lines)
            all_lines.append("")  # ajouter une ligne vide entre playlists
        except Exception as e:
            print(f"Erreur téléchargement {url}: {e}")
    return "\n".join(all_lines)

def main():
    if not os.path.exists("playlist"):
        os.makedirs("playlist")
    if not os.path.exists("data/sources.csv"):
        print("Fichier data/sources.csv introuvable")
        return
    with open(DATA_SOURCES, "r", encoding="utf-8") as f:
        urls = f.readlines()
    playlist_content = download_and_concat_playlists(urls)
    with open(OUTPUT_PLAYLIST, "w", encoding="utf-8") as f:
        f.write(playlist_content)
    print(f"Playlist brute générée : {OUTPUT_PLAYLIST}")

if __name__ == "__main__":
    main()
