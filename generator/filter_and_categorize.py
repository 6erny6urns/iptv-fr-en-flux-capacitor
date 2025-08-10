import os

IN_FILE = os.path.join("playlist", "playlist.m3u")
OUT_FILE = os.path.join("playlist", "playlist_filtered.m3u")

# Liste des chaînes favorites - noms exacts ou fragments trouvés dans EXTINF
FAVORITES = [
    "1TV.af@SD",
    "CBC Montreal",
    "TF1",
    "CNN",
    "WABC-TV 7",
    # Ajoute ici toutes les chaînes listées plus haut
]

def is_favorite(line):
    return any(fav in line for fav in FAVORITES)

def main():
    if not os.path.isfile(IN_FILE):
        print(f"Erreur : fichier {IN_FILE} introuvable.")
        return
    with open(IN_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    header = []
    favorites_section = []
    others_section = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXTINF"):
            extinf = line.strip()
            url_line = lines[i+1].strip() if i+1 < len(lines) else ""
            entry = extinf + "\n" + url_line + "\n"
            if is_favorite(extinf):
                favorites_section.append(entry)
            else:
                others_section.append(entry)
            i += 2
        else:
            if line.startswith("#EXTM3U"):
                header.append(line)
            i += 1

    # Création playlist filtrée avec section FAVORIS en premier
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.writelines(header)
        f.write("#EXTINF:-1, FAVORIS\n")
        for entry in favorites_section:
            f.write(entry)
        f.write("#EXTINF:-1, AUTRES\n")
        for entry in others_section:
            f.write(entry)

    print(f"Playlist filtrée et catégorisée créée : {OUT_FILE}")

if __name__ == "__main__":
    main()
