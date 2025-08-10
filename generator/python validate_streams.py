import os

# Exemple très simple de validation de flux IPTV
# Charge le fichier playlist.m3u, valide les URLs, écrit playlist_filtered.m3u

def validate_url(url):
    # Ici, mettre la vraie logique (ping, test HTTP, etc.)
    return url.startswith("http")

def main():
    input_path = "../playlist/playlist.m3u"
    output_path = "../playlist/playlist_filtered.m3u"
    log_path = "../playlist/validation_log.txt"

    if not os.path.exists(input_path):
        print(f"Fichier d'entrée non trouvé : {input_path}")
        return

    valid_urls = []
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    with open(log_path, "w", encoding="utf-8") as log:
        for line in lines:
            if line.strip().startswith("#EXTINF"):
                log.write(line)
                valid_urls.append(line)
            elif line.strip() and not line.strip().startswith("#"):
                url = line.strip()
                if validate_url(url):
                    log.write(f"Valid URL: {url}\n")
                    valid_urls.append(url + "\n")
                else:
                    log.write(f"Invalid URL: {url}\n")
            else:
                valid_urls.append(line)

    with open(output_path, "w", encoding="utf-8") as f_out:
        f_out.writelines(valid_urls)

    print(f"Validation terminée. {len(valid_urls)} lignes traitées.")

if __name__ == "__main__":
    main()
