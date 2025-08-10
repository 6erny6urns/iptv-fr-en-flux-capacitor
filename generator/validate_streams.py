import csv
import os
import subprocess

INPUT_CSV = "data/sources.csv"
OUTPUT_DIR = "playlist"
OUTPUT_PLAYLIST = os.path.join(OUTPUT_DIR, "playlist_filtered.m3u")
LOG_FILE = "validation_log.txt"

def extract_urls(csv_path):
    urls = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "url" in row and row["url"].strip():
                urls.append((row["name"], row["url"]))
    return urls

def validate_stream(url):
    # Test avec ffprobe pour valider le flux
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=format_name", "-of", "default=nw=1", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            text=True
        )
        output = result.stdout.lower()
        if "format_name=" in output:
            return True
    except Exception:
        pass
    return False

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    urls = extract_urls(INPUT_CSV)
    valid_streams = []
    with open(LOG_FILE, "w", encoding="utf-8") as logf:
        logf.write(f"Starting validation of {len(urls)} streams...\n")
        for i, (name, url) in enumerate(urls, 1):
            logf.write(f"Testing [{i}/{len(urls)}]: {name} ... ")
            print(f"Testing [{i}/{len(urls)}]: {name} ... ", end="")
            if validate_stream(url):
                logf.write("VALID\n")
                print("VALID")
                valid_streams.append(f"#EXTINF:-1,{name}\n{url}\n")
            else:
                logf.write("INVALID\n")
                print("INVALID")

        logf.write(f"Total valid streams: {len(valid_streams)}\n")
        # Génération playlist M3U
        with open(OUTPUT_PLAYLIST, "w", encoding="utf-8") as outf:
            outf.write("#EXTM3U\n")
            for entry in valid_streams:
                outf.write(entry)

if __name__ == "__main__":
    main()
