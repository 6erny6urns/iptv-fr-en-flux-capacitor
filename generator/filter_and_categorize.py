import os

PLAYLIST_DIR = "playlist"
INPUT_FILE = os.path.join(PLAYLIST_DIR, "playlist.m3u")
OUTPUT_FILE = os.path.join(PLAYLIST_DIR, "playlist_filtered.m3u")

# Liste des favoris EXACTS (doivent correspondre aux noms dans la playlist)
FAVORITES = [
    "1TV.af@SD",
    "CBC Montreal",
    "TF1",
    "CNN",
    "WABC-TV 7",
    # Ajoute ici toutes les chaînes que tu veux en favoris
]

def read_playlist(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_playlist(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def extract_channels(playlist_content):
    channels = []
    lines = playlist_content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXTINF"):
            info_line = line
            url_line = lines[i+1] if i+1 < len(lines) else ""
            channels.append((info_line, url_line))
            i += 2
        else:
            i += 1
    return channels

def get_channel_name(extinf_line):
    # Extrait le nom après la dernière virgule
    return extinf_line.split(",")[-1].strip()

def filter_channels(channels):
    favoris = []
    autres = []

    for info, url in channels:
        name = get_channel_name(info)
        if any(fav == name for fav in FAVORITES):
            favoris.append((info, url))
        else:
            autres.append((info, url))

    # Trier les autres chaînes par ordre alphabétique (optionnel)
    autres = sorted(autres, key=lambda x: get_channel_name(x[0]))

    return favoris, autres

def build_playlist(favoris, autres):
    playlist = "#EXTM3U\n\n"
    if favoris:
        playlist += "#EXTINF:-1,Catégorie FAVORIS\n"
        for info, url in favoris:
            playlist += f"{info}\n{url}\n"
        playlist += "\n"
    for info, url in autres:
        playlist += f"{info}\n{url}\n"
    return playlist

def main():
    if not os.path.exists(PLAYLIST_DIR):
        print(f"Le dossier {PLAYLIST_DIR} est introuvable.")
        return

    playlist_content = read_playlist(INPUT_FILE)
    channels = extract_channels(playlist_content)
    favoris, autres = filter_channels(channels)
    new_playlist = build_playlist(favoris, autres)
    write_playlist(OUTPUT_FILE, new_playlist)
    print(f"Playlist filtrée et catégorisée créée : {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
