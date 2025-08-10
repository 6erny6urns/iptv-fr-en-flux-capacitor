import requests
import time

INPUT_PLAYLIST = "playlist_filtered.m3u"
OUTPUT_LOG = "stream_validation_report.txt"
TIMEOUT = 5  # secondes max par requête

def extract_urls(m3u_path):
    urls = []
    with open(m3u_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("http"):
                urls.append(line)
    return urls

def test_url(url):
    try:
        # Envoi d'une requête HEAD pour test rapide de disponibilité
        resp = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
        if resp.status_code == 200:
            return True
        # Certains serveurs ne répondent pas bien au HEAD => fallback GET
        resp = requests.get(url, timeout=TIMEOUT, stream=True)
        return resp.status_code == 200
    except Exception:
        return False

def main():
    urls = extract_urls(INPUT_PLAYLIST)
    total = len(urls)
    valid = 0
    invalid_urls = []

    with open(OUTPUT_LOG, "w", encoding="utf-8") as logf:
        logf.write(f"Stream validation report - {time.ctime()}\n")
        logf.write(f"Total streams tested: {total}\n\n")

        for i, url in enumerate(urls, 1):
            is_valid = test_url(url)
            status = "VALID" if is_valid else "INVALID"
            logf.write(f"{i}/{total} {status} - {url}\n")
            if is_valid:
                valid += 1
            else:
                invalid_urls.append(url)
            print(f"{i}/{total} {status} - {url}")

        logf.write(f"\nSummary: {valid} valid, {total - valid} invalid streams\n")

    print(f"\nValidation done. See {OUTPUT_LOG} for details.")

if __name__ == "__main__":
    main()
