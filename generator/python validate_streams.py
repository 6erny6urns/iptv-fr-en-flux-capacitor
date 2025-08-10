import csv
import requests
import os
import time

SOURCES_CSV = 'sources.csv'
OUTPUT_M3U = 'playlist_filtered.m3u'
LOG_FILE = 'validation_log.txt'
TIMEOUT = 10  # secondes timeout requête

def fetch_playlist(url):
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return None

def test_stream_url(url):
    try:
        # HEAD souvent interdit, fallback GET avec stream=True, lecture minimale
        resp = requests.head(url, timeout=TIMEOUT)
        if resp.status_code == 200:
            return True
        # Fallback GET
        resp = requests.get(url, timeout=TIMEOUT, stream=True)
        if resp.status_code == 200:
            return True
    except:
        return False
    return False

def parse_m3u(text):
    lines = text.splitlines()
    entries = []
    current_meta = ''
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#EXTM3U'):
            continue
        if line.startswith('#EXTINF'):
            current_meta = line
        elif line.startswith('http') or line.startswith('udp://') or line.startswith('rtmp'):
            entries.append((current_meta, line))
            current_meta = ''
    return entries

def main():
    total_sources = 0
    total_streams = 0
    valid_streams = 0

    with open(LOG_FILE, 'w', encoding='utf-8') as logf, \
         open(OUTPUT_M3U, 'w', encoding='utf-8') as outm3u:

        outm3u.write('#EXTM3U\n')

        with open(SOURCES_CSV, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                url = row.get('url')
                desc = row.get('description', '')
                if not url:
                    logf.write(f"[WARN] URL vide dans sources.csv\n")
                    continue
                total_sources += 1
                logf.write(f"[INFO] Télécharger playlist : {url}\n")
                pl_text = fetch_playlist(url)
                if not pl_text:
                    logf.write(f"[ERROR] Échec téléchargement {url}\n")
                    continue
                streams = parse_m3u(pl_text)
                total_streams += len(streams)
                logf.write(f"[INFO] {len(streams)} flux extraits\n")

                for meta, stream_url in streams:
                    logf.write(f"[DEBUG] Tester flux {stream_url}...\n")
                    if test_stream_url(stream_url):
                        valid_streams += 1
                        outm3u.write(meta + '\n' + stream_url + '\n')
                        logf.write(f"[OK] Flux valide\n")
                    else:
                        logf.write(f"[FAIL] Flux invalide ou inaccessible\n")

                # Pause pour éviter blocage réseau / throttling (ajustable)
                time.sleep(1)

        logf.write(f"\nRésumé : sources={total_sources}, flux totaux={total_streams}, flux valides={valid_streams}\n")

if __name__ == '__main__':
    main()
