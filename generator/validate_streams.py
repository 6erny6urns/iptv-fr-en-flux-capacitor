import subprocess
import csv
import sys
import os

INPUT_CSV = "data/sources.csv"       # adapte selon ton repo
OUTPUT_M3U = "playlist/playlist_filtered.m3u"

def test_live_stream(url, timeout=10):
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-read_intervals", "%+5",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            url
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        duration = float(result.stdout.decode().strip() or 0)
        return duration > 0
    except Exception:
        return False

def read_sources(csv_path):
    streams = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Exemple attendu : id, name, url, logo, group
            streams.append({
                "id": row.get("id", ""),
                "name": row.get("name", "NoName"),
                "url": row.get("url", ""),
                "logo": row.get("logo", ""),
                "group": row.get("group", "Unknown")
            })
    return streams

def write_m3u(streams, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for s in streams:
            f.write(f'#EXTINF:-1 tvg-id="{s["id"]}" tvg-logo="{s["logo"]}" group-title="{s["group"]}", {s["name"]} LIVE\n')
            f.write(f'{s["url"]}\n')

def main():
    streams = read_sources(INPUT_CSV)
    valid_streams = []
    print(f"Testing {len(streams)} streams...")
    for i, stream in enumerate(streams, 1):
        print(f"Testing [{i}/{len(streams)}]: {stream['name']} ...", end="")
        if test_live_stream(stream["url"]):
            print("VALID")
            valid_streams.append(stream)
        else:
            print("INVALID")
    print(f"Total valid streams: {len(valid_streams)}")
    write_m3u(valid_streams, OUTPUT_M3U)
    print(f"Playlist saved to {OUTPUT_M3U}")

if __name__ == "__main__":
    main()
