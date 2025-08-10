import os
import requests
import time

# URLs sources IPTV (exemple, à enrichir)
SOURCES = [
    "https://iptv-org.github.io/iptv/index.country.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/fr.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/us.m3u",
    # Ajoute ici jusqu'à 25 URLs fiables
]

PLAYLIST_RAW = "../playlist/playlist_raw.m3u"
PLAYLIST_FILTERED = "../playlist/playlist_filtered.m3u"
LOG_FILE = "../playlist/validation_log.txt"

def download_sources(urls, dest):
    with open(dest, "w", encoding="utf-8") as f:
        for url in urls:
            try:
                r = requests.get(url, timeout=15)
                r.raise_for_status()
                f.write(r.text + "\n")
                print(f"[OK] Downloaded {url}")
                time.sleep(1)  # anti-flood
            except Exception as e:
                print(f"[ERROR] Failed {url}: {e}")

def validate_stream(url):
    # Test simple de validité HTTP (head ou get avec timeout)
    try:
        r = requests.head(url, timeout=8, allow_redirects=True)
        if r.status_code == 200:
            return True
    except:
        return False
    return False

def filter_and_validate(input_path, output_path, log_path):
    if not os.path.exists(input_path):
        print(f"Input file not found: {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    output_lines = []
    log_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXTINF"):
            info_line = line
            stream_line = lines[i+1].strip() if i+1 < len(lines) else ""
            if validate_stream(stream_line):
                output_lines.append(info_line)
                output_lines.append(stream_line + "\n")
                log_lines.append(f"[VALID] {stream_line}")
            else:
                log_lines.append(f"[INVALID] {stream_line}")
            i += 2
        else:
            output_lines.append(line)
            i += 1

    with open(output_path, "w", encoding="utf-8") as f_out:
        f_out.writelines(output_lines)

    with open(log_path, "w", encoding="utf-8") as logf:
        logf.write("\n".join(log_lines))

    print(f"Filtered playlist saved to {output_path}")

def main():
    print("Downloading sources...")
    download_sources(SOURCES, PLAYLIST_RAW)

    print("Filtering and validating streams...")
    filter_and_validate(PLAYLIST_RAW, PLAYLIST_FILTERED, LOG_FILE)

if __name__ == "__main__":
    main()
