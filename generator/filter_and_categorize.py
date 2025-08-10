import os
import re

PLAYLIST_IN = "playlist/playlist.m3u"
PLAYLIST_OUT = "playlist/playlist_filtered.m3u"

# Liste des chaînes prioritaires EXACTES (tvg-id ou nom exact dans #EXTINF)
FAVORITES = [
    "1TV.af@SD",
    "CBC Montreal",
    "TF1",
    "CNN",
    "WABC-TV 7",
    # Ajoute ici toutes les chaînes que tu as listées, exactement comme dans #EXTINF
]

def extract_channels(content):
    # Retourne une liste de tuples (header_line, url_line)
    pattern = re.compile(r"(#EXTINF:[^\n]+\n)([^\n]+)", re.IGNORECASE)
    return pattern.findall(content)

def is_favorite(header_line):
    # Vérifie si la chaîne est dans FAVORITES
    for fav in FAVORITES:
        if fav.lower() in header_line.lower():
            return True
    return False

def add_favorites_group_tag(header_line):
    # Ajoute ou remplace group-title par FAVORIS
    if "group-title=" in header_line:
        header_line = re.sub(r'group-title="[^"]*"', 'group-title="FAVORIS"', header_line)
    else:
        header_line = header_line.strip()[:-1] + ' group-title="FAVORIS",\n'  # insère avant le dernier ',\n'
    return header_line

def main():
    if not os.path.exists("playlist"):
        os.makedirs("playlist")

    with open(PLAYLIST_IN, "r", encoding="utf-8") as f:
        content = f.read()

    channels = extract_channels(content)

    favorites = []
    others = []

    for header, url in channels:
        if is_favorite(header):
            header_mod = add_favorites_group_tag(header)
            favorites.append((header_mod, url))
        else:
            others.append((header, url))

    # Reconstruction playlist
    result = "#EXTM3U\n"
    for h, u in favorites:
        result += h + u + "\n"
    for h, u in others:
        result += h + u + "\n"

    with open(PLAYLIST_OUT, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"Playlist filtrée et catégorisée créée : {PLAYLIST_OUT}")

if __name__ == "__main__":
    main()
