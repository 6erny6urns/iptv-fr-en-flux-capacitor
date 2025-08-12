import csv
import os
import subprocess
import sys

INPUT_CSV = "data/sources.csv"
OUTPUT_DIR = "playlist"
OUTPUT_PLAYLIST = os.path.join(OUTPUT_DIR, "playlist_filtered.m3u")
LOG_FILE = "validation_log.txt"

def check_ffprobe():
    try:
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False

def extract_urls(csv_path):
    if not os.path.isfile(csv_path):
        print(f"WARNING: CSV source file not found: {csv_path}")
        return []
    urls = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "url" in row and row["url"].strip():
                name = row.get("name", "UNKNOWN").strip()
                url = row["url"].strip()
                urls.append((name, url))
    return urls

def validate_stream(url):
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
    if not check_ffprobe():
        print("ERROR: ffprobe not found or not executable. Please install ffprobe.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    urls = extract_urls(INPUT_CSV)
    valid_streams = []

    with open(LOG_FILE, "w", encoding="utf-8") as logf:
        if not urls:
            logf.write("No streams found in CSV.\n")
            print("No streams found in CSV.")
        else:
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

    print(f"\nValidation complete. {len(valid_streams)} valid streams saved to '{OUTPUT_PLAYLIST}'.")
    print(f"Log file: '{LOG_FILE}'")

if __name__ == "__main__":
    main()
