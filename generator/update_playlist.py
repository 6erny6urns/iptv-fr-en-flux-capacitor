import os
import requests

# 1. Création du dossier playlist s'il n'existe pas
os.makedirs('playlist', exist_ok=True)

# 2. Exemple simple d'URLs à traiter (à adapter ou récupérer depuis data/sources.csv)
sources = [
    "https://iptv-org.github.io/iptv/index.country.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/fr.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/us.m3u",
    # ajoute tes autres URLs ici...
]

def download_m3u(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"Erreur téléchargement {url} : {e}")
        return ""

def filter_valid_streams(m3u_content):
    # Ici tu implémentes ta logique de filtrage et validation automatique des flux
    # Par exemple, retirer les entrées vides, vérifier la validité URL, etc.
    # Simplification : retourne le contenu brut pour l'exemple
    return m3u_content

def main():
    all_streams = ""

    for url in sources:
        print(f"Téléchargement de {url}")
        content = download_m3u(url)
        valid_streams = filter_valid_streams(content)
        all_streams += valid_streams + "\n"

    # Écriture dans playlist/playlist_filtered.m3u
    output_file = "playlist/playlist_filtered.m3u"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(all_streams)

    print(f"Playlist mise à jour enregistrée dans {output_file}")

if __name__ == "__main__":
    main()
