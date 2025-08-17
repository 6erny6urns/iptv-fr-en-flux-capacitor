import os
import csv
import requests
import re
from tqdm import tqdm

# === Paramètres ===
# URL brute vers ton CSV dans GitHub (adapter ton utilisateur/repo/branche)
CSV_URL = "https://raw.githubusercontent.com/<TON_USER>/<TON_REPO>/main/channels_keywords.csv"

# Dossier pour sauvegarder les résultats
OUTPUT_DIR = "results"
VALID_OUTPUT = os.path.join(OUTPUT_DIR, "filtered_valid_m3u.csv")
INVALID_OUTPUT = os.path.join(OUTPUT_DIR, "filtered_out.csv")
LOG_FILE = os.path.join(OUTPUT_DIR, "log_parse_filter_validate_m3u.txt")

# === Téléchargement du CSV depuis GitHub ===
def fetch_keywords_from_github():
    print(f"Téléchargement du fichier CSV depuis GitHub : {CSV_URL}")
    resp = requests.get(CSV_URL)
    resp.raise_for_status()

    keywords = []
    decoded_content = resp.content.decode("utf-8").splitlines()
    reader = csv.reader(decoded_content)
    for row in reader:
        if row:  # éviter les lignes vides
            keywords.append(row[0].strip().lower())
    print(f"✅ {len(keywords)} mots-clés chargés")
    return keywords

# === Vérification basique d’un flux M3U ===
def validate_stream(url):
    try:
        r = requests.head(url, timeout=5)
        return r.status_code == 200
    except Exception:
        return False

# === Parsing des fichiers M3U ===
def parse_and_filter_m3u(keywords):
    if not os.path.exists("RAW"):
        print("❌ Dossier RAW non trouvé. Mets tes fichiers M3U dans /RAW")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    valid_entries = []
    invalid_entries = []

    with open(LOG_FILE, "w", encoding="utf-8") as log:
        for filename in os.listdir("RAW"):
            if filename.endswith(".m3u"):
                filepath = os.path.join("RAW", filename)
                log.write(f"\n--- Parsing {filepath} ---\n")
                print(f"🔎 Parsing {filepath}")

                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                matches = []
                for kw in keywords:
                    found = re.findall(rf".*{kw}.*", content, re.IGNORECASE)
                    matches.extend(found)

                for line in tqdm(matches, desc=f"Testing {filename}"):
                    if line.startswith("http"):
                        url = line.strip()
                        if validate_stream(url):
                            valid_entries.append([filename, kw, url])
                            log.write(f"VALID: {url}\n")
                        else:
                            invalid_entries.append([filename, kw, url])
                            log.write(f"INVALID: {url}\n")

    # Sauvegarde résultats
    with open(VALID_OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Fichier", "Mot-clé", "URL"])
        writer.writerows(valid_entries)

    with open(INVALID_OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Fichier", "Mot-clé", "URL"])
        writer.writerows(invalid_entries)

    print(f"\n✅ Résultats enregistrés dans {OUTPUT_DIR}/")
    print(f" - Flux valides : {len(valid_entries)}")
    print(f" - Flux invalides : {len(invalid_entries)}")

if __name__ == "__main__":
    keywords = fetch_keywords_from_github()
    parse_and_filter_m3u(keywords)
