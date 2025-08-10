import os
import re
import logging

INPUT_FILE = 'playlist/playlist.m3u'
OUTPUT_FILE = 'playlist/playlist_filtered.m3u'
LOG_FILE = 'log_update.txt'

FAVORITES = [
    # Ta liste exhaustive, exact nom tel que dans #EXTINF titre
    "1TV.af@SD",
    "CBC Montreal",
    "TF1",
    "CNN",
    "WABC-TV 7",
    "ICI Télé",
    "TVA",
    "Noovo",
    "Télé-Québec",
    "LCN",
    "RDS",
    "ICI RDI",
    "Canal Vie",
    "Super Écran",
    "AddikTV",
    "CASA",
    "Évasion",
    "Prise 2",
    "TV5",
    "Canal Savoir",
    "Unis TV",
    "CTV",
    "Global",
    "Citytv",
    "TSN",
    "Sportsnet",
    "CP24",
    "BBC",
    "Metro 14",
    "OMNI",
    "Crave",
    "Télétoon",
    "The Weather Network",
    "France 2",
    "France 3",
    "M6",
    "France 5",
    "Arte",
    "C8",
    "TMC",
    "W9",
    "TFX",
    "NRJ 12",
    "Paris Première",
    "TV Breizh",
    "6ter",
    "BFMTV",
    "CNews",
    "LCI",
    "franceinfo",
    "Canal+",
    "L'Équipe",
    "Gulli",
    "France 4",
    "Chérie 25",
    "RTL9",
    "13ème Rue",
    "Syfy",
    "Téva",
    "CStar",
    "RMC Story",
    "RMC Découverte",
    "ABC",
    "CBS",
    "NBC",
    "FOX",
    "CW",
    "Fox News Channel",
    "MSNBC",
    "CNBC",
    "PBS",
    "Newsmax",
    "NewsNation",
    "Telemundo",
    "Univision",
    "WCBS-TV 2",
    "WNBC 4",
    "WNYW 5",
    "WPIX 11",
    "Spectrum News NY1",
]

def parse_m3u(content):
    entries = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('#EXTINF:'):
            extinf = line
            url = lines[i+1] if i+1 < len(lines) else ''
            entries.append((extinf, url))
            i += 2
        else:
            i += 1
    return entries

def filter_entries(entries):
    fav_entries = []
    other_entries = []
    for extinf, url in entries:
        title = extinf.split(',')[-1].strip()
        if title in FAVORITES:
            fav_entries.append((extinf, url))
        else:
            other_entries.append((extinf, url))
    return fav_entries, other_entries

def write_playlist(fav_entries, other_entries):
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        if fav_entries:
            f.write("#EXTINF:-1 group-title=\"FAVORIS\",Favoris\n")
            for extinf, url in fav_entries:
                f.write(f"{extinf}\n{url}\n")
        # Tri alphabétique du reste
        other_entries_sorted = sorted(other_entries, key=lambda x: x[0])
        for extinf, url in other_entries_sorted:
            f.write(f"{extinf}\n{url}\n")

def main():
    logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    logging.info("Début du script filter_and_categorize.py")

    if not os.path.isfile(INPUT_FILE):
        logging.error(f"Fichier d'entrée introuvable : {INPUT_FILE}")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    entries = parse_m3u(content)
    fav_entries, other_entries = filter_entries(entries)

    write_playlist(fav_entries, other_entries)
    logging.info(f"Playlist filtrée et catégorisée créée : {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
