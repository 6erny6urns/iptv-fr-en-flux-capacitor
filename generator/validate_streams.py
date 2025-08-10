import sys
import os

def extract_urls(m3u_path):
    if not os.path.isfile(m3u_path):
        print(f"Erreur critique : fichier introuvable '{m3u_path}'")
        sys.exit(1)
    with open(m3u_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    # Extraction simple des URLs à partir des lignes non commentées (#EXT...)
    urls = [line.strip() for line in lines if line and not line.startswith('#')]
    return urls

def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_streams.py <chemin_playlist.m3u>")
        sys.exit(1)

    playlist_path = sys.argv[1]
    urls = extract_urls(playlist_path)

    # ici la validation des urls, par ex. ping, requests.head, etc.
    for url in urls:
        print(f"Validation du flux : {url}")
        # Valide chaque flux, stocke résultats, etc.

if __name__ == "__main__":
    main()
