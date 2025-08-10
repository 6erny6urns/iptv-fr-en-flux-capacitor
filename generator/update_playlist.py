import csv
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Chemins fichiers
SOURCES_FILE = 'data/sources.csv'
OUTPUT_FILE = 'playlist/playlist_filtered.m3u'

# Timeout pour test flux
REQUEST_TIMEOUT = 5

def read_sources(file_path):
    urls = []
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            url = row.get('url')
            if url:
                urls.append(url.strip())
    return urls

def download_playlist(url):
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None

def parse_m3u(content):
    """Retourne une liste de dict { 'name': ..., 'url': ... }"""
    lines = content.splitlines()
    entries = []
    current_name = None
    for line in lines:
        line = line.strip()
        if line.startswith('#EXTINF:'):
            # Extraire nom après la virgule
            idx = line.find(',')
            current_name = line[idx+1:] if idx != -1 else None
        elif line and not line.startswith('#'):
            # URL de flux
            if current_name:
                entries.append({'name': current_name, 'url': line})
            else:
                # Si pas de nom, on met URL comme nom
                entries.append({'name': line, 'url': line})
            current_name = None
    return entries

def test_stream_url(url):
    """Teste si l'url est accessible par un HEAD ou GET simple"""
    try:
        # Certaines URLs ne répondent pas au HEAD, donc GET limité
        resp = requests.head(url, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            return True
        # Sinon test GET léger
        resp = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            return True
        return False
    except Exception:
        return False

def process_source(url):
    """Télécharge, parse, teste les flux, retourne liste valide"""
    playlist_content = download_playlist(url)
    if not playlist_content:
        return []

    entries = parse_m3u(playlist_content)
    valid_entries = []
    for e in entries:
        if test_stream_url(e['url']):
            valid_entries.append(e)
    return valid_entries

def main():
    sources = read_sources(SOURCES_FILE)
    all_valid_entries = []

    print(f"Sources à traiter: {len(sources)}")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_source, url): url for url in sources}
        for i, future in enumerate(as_completed(futures), 1):
            url = futures[future]
            try:
                valid_entries = future.result()
                all_valid_entries.extend(valid_entries)
                print(f"[{i}/{len(sources)}] {url} : {len(valid_entries)} flux valides")
            except Exception as e:
                print(f"[{i}/{len(sources)}] {url} erreur : {e}")

    # Supprimer doublons sur URL (garder premier)
    seen_urls = set()
    filtered_entries = []
    for entry in all_valid_entries:
        if entry['url'] not in seen_urls:
            filtered_entries.append(entry)
            seen_urls.add(entry['url'])

    # Écrire le fichier final
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for entry in filtered_entries:
            f.write(f'#EXTINF:-1,{entry["name"]}\n')
            f.write(f'{entry["url"]}\n')

    print(f"Playlist finale créée : {OUTPUT_FILE} avec {len(filtered_entries)} flux valides")

if __name__ == '__main__':
    main()
