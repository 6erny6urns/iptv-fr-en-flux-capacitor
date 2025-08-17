import csv
import os
import re

# Emplacement du fichier CSV (dans /data)
CSV_FILE = os.path.join("data", "channels_keywords.csv")

# Fichier M3U de sortie
OUTPUT_FILE = "playlist.m3u"

# Fichier log
LOG_FILE = "generation_log.txt"

def load_keywords():
    keywords = []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            keywords.append({
                "channel": row.get("channel", "").strip(),
                "keywords": [kw.strip() for kw in row.get("keywords", "").split(",") if kw.strip()]
            })
    return keywords

def search_m3u_files(keywords):
    found_channels = []
    for root, _, files in os.walk("data"):
        for file in files:
            if file.lower().endswith(".m3u") and file != OUTPUT_FILE:
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    for entry in keywords:
                        for kw in entry["keywords"]:
                            if re.search(rf"\b{re.escape(kw)}\b", content, re.IGNORECASE):
                                found_channels.append((entry["channel"], kw, path))
    return found_channels

def generate_m3u(channels):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for channel, keyword, source in channels:
            f.write(f"#EXTINF:-1 tvg-name=\"{channel}\" group-title=\"Auto\"\n")
            f.write(f"{source}  # Found with keyword: {keyword}\n")

def log_results(channels):
    with open(LOG_FILE, "w", encoding="utf-8") as log:
        log.write("Log de génération M3U\n\n")
        for channel, keyword, source in channels:
            log.write(f"Trouvé: {channel} (mot-clé: {keyword}) dans {source}\n")

def main():
    print("Chargement des mots-clés...")
    keywords = load_keywords()
    print(f"{len(keywords)} chaînes chargées.")

    print("Recherche des flux...")
    found_channels = search_m3u_files(keywords)
    print(f"{len(found_channels)} correspondances trouvées.")

    print("Génération de la playlist...")
    generate_m3u(found_channels)

    print("Écriture du log...")
    log_results(found_channels)

    print("Terminé. Playlist générée:", OUTPUT_FILE)

if __name__ == "__main__":
    main()
