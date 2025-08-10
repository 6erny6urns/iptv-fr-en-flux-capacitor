import os

# Chemins
INPUT_PLAYLIST = "playlist/playlist.m3u"
OUTPUT_PLAYLIST = "playlist/playlist_filtered.m3u"

# Liste des chaînes favorites exactes ou motifs clés (à adapter)
FAVORITES = [
    "1TV.af@SD",
    "CBC Montreal",
    "TF1",
    "CNN",
    "WABC-TV 7",
    # Ajoute ici toutes les chaînes que tu veux absolument en favoris
]

def is_favorite(line):
    return any(fav in line for fav in FAVORITES)

def main():
    if not os.path.exists(INPUT_PLAYLIST):
        print(f"Erreur : fichier source {INPUT_PLAYLIST} introuvable.")
        return

    with open(INPUT_PLAYLIST, encoding="utf-8") as f:
        lines = f.readlines()

    favorites_block = []
    others_block = []

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXTINF"):
            # Regroupe ligne #EXTINF + url suivante
            entry = lines[i] + lines[i+1]
            if is_favorite(entry):
                favorites_block.append(entry)
            else:
                others_block.append(entry)
            i += 2
        else:
            i += 1

    with open(OUTPUT_PLAYLIST, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write("#EXTINF:-1, FAVORITES\n")
        for entry in favorites_block:
            f.write(entry)
        f.write("\n#EXTINF:-1, OTHERS\n")
        for entry in others_block:
            f.write(entry)

    print(f"Playlist filtrée générée : {OUTPUT_PLAYLIST}")

if __name__ == "__main__":
    main()
