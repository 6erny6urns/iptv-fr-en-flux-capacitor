import requests
import csv
import os

PLAYLIST_DIR = os.path.join(os.path.dirname(__file__), '..', 'playlist')
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
RAW_DIR = os.path.join(os.path.dirname(__file__), '..', 'raw')

os.makedirs(PLAYLIST_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)

SOURCES_CSV = os.path.join(DATA_DIR, 'sources.csv')
OUTPUT_PLAYLIST = os.path.join(PLAYLIST_DIR, 'playlist.m3u')

def download_sources():
    urls = []
    with open(SOURCES_CSV, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if row and row[0].strip():
                urls.append(row[0].strip())
    return urls

def download_m3u(url):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        filename = os.path.join(RAW_DIR, os.path.basename(url).split('?')[0])
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(r.text)
        return filename
    except Exception as e:
        print(f"Erreur téléchargement {url}: {e}")
        return None

def merge_playlists(filepaths):
    combined = "#EXTM3U\n"
    for fp in filepaths:
        if not fp:
            continue
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                content = f.read()
                # Ignore #EXTM3U header in merged files
                content = '\n'.join(line for line in content.splitlines() if not line.strip().startswith("#EXTM3U"))
                combined += content + '\n'
        except Exception as e:
            print(f"Erreur lecture fichier {fp}: {e}")
    return combined

def save_playlist(content):
    with open(OUTPUT_PLAYLIST, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    urls = download_sources()
    if not urls:
        print("Aucune source trouvée dans sources.csv")
        return
    downloaded_files = []
    for url in urls:
        print(f"Téléchargement : {url}")
        filepath = download_m3u(url)
        if filepath:
            downloaded_files.append(filepath)
    playlist_content = merge_playlists(downloaded_files)
    save_playlist(playlist_content)
    print(f"Playlist brute générée dans : {OUTPUT_PLAYLIST}")

if __name__ == "__main__":
    main()
