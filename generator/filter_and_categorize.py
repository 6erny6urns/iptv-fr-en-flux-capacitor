import os
import re

PLAYLIST_DIR = os.path.join(os.path.dirname(__file__), '..', 'playlist')
INPUT_PLAYLIST = os.path.join(PLAYLIST_DIR, 'playlist.m3u')
OUTPUT_PLAYLIST = os.path.join(PLAYLIST_DIR, 'playlist_filtered.m3u')

def is_valid_url(url):
    # Test simple de validité syntaxique URL
    pattern = re.compile(r'^http[s]?://')
    return bool(pattern.match(url))

def test_stream_url(url, timeout=10):
    # Test rapide si le flux est accessible (HEAD ou GET avec timeout)
    import requests
    try:
        resp = requests.head(url, timeout=timeout)
        if resp.status_code == 200:
            return True
    except:
        pass
    # fallback GET
    try:
        resp = requests.get(url, timeout=timeout, stream=True)
        if resp.status_code == 200:
            return True
    except:
        pass
    return False

def filter_playlist():
    if not os.path.exists(INPUT_PLAYLIST):
        print("Fichier playlist.m3u non trouvé pour filtrage")
        return

    with open(INPUT_PLAYLIST, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    filtered_lines = []
    i = 0
    valid_count = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            # récupère la ligne suivante URL
            if i + 1 >= len(lines):
                break
            url = lines[i + 1].strip()
            if is_valid_url(url) and test_stream_url(url):
                filtered_lines.append(lines[i])
                filtered_lines.append(lines[i + 1])
                valid_count += 1
            i += 2
        else:
            # on copie les entêtes généraux #EXTM3U etc.
            if line.startswith("#EXTM3U"):
                filtered_lines.append(lines[i])
            i += 1

    with open(OUTPUT_PLAYLIST, 'w', encoding='utf-8') as f:
        f.writelines(filtered_lines)

    print(f"{valid_count} flux valides gardés dans {OUTPUT_PLAYLIST}")

if __name__ == "__main__":
    filter_playlist()
