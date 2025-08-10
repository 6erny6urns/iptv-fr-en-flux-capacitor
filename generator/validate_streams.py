import sys
import os
import requests

def extract_urls(m3u_path):
    if not os.path.isfile(m3u_path):
        print(f"Erreur critique : fichier introuvable '{m3u_path}'")
        sys.exit(1)
    with open(m3u_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    urls = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
    return urls

def validate_url(url, timeout=5):
    try:
        # Test simple avec HEAD pour vérifier disponibilité sans tout télécharger
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return response.status_code == 200
    except requests.RequestException:
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_streams.py <chemin_playlist.m3u>")
        sys.exit(1)

    playlist_path = sys.argv[1]
    urls = extract_urls(playlist_path)

    valid_urls = []
    invalid_urls = []

    for url in urls:
        print(f"Validation du flux : {url}")
        if validate_url(url):
            valid_urls.append(url)
            print(f"✓ Valide")
        else:
            invalid_urls.append(url)
            print(f"✗ Invalide")

    # Sauvegarde des résultats
    with open("playlist_filtered.m3u", "w", encoding="utf-8") as f_out:
        f_out.write("#EXTM3U\n")
        for url in valid_urls:
            f_out.write(f"{url}\n")

    with open("validation_log.txt", "w", encoding="utf-8") as log_file:
        log_file.write("Flux valides:\n")
        log_file.writelines(f"{url}\n" for url in valid_urls)
        log_file.write("\nFlux invalides:\n")
        log_file.writelines(f"{url}\n" for url in invalid_urls)

if __name__ == "__main__":
    main()
