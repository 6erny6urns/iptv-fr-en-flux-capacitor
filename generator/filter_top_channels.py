import csv
import os

# === Variables principales ===
PROJECT_DIR = r"C:\Users\berny\OneDrive\Documents\0000000000_PROJETS\M3U"
INPUT_CSV = os.path.join(PROJECT_DIR, "filtered_valid_m3u.csv")   # CSV source
TOP_CHANNELS_FILE = os.path.join(PROJECT_DIR, "top_channels.txt") # Liste de chaînes
OUTPUT_CSV = os.path.join(PROJECT_DIR, "top_channels_m3u.csv")   # Résultat CSV
OUTPUT_M3U = os.path.join(PROJECT_DIR, "top_channels.m3u")       # Résultat M3U

def load_top_channels(filepath):
    """Charge la liste des chaînes prioritaires à partir d’un fichier texte."""
    with open(filepath, "r", encoding="utf-8") as f:
        channels = [line.strip().lower() for line in f if line.strip()]
    return channels

def filter_channels(input_csv, top_channels):
    """Filtre les flux CSV selon les chaînes présentes dans top_channels."""
    filtered_rows = []
    with open(input_csv, "r", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            channel_name = row.get("name", "").lower()
            if any(ch in channel_name for ch in top_channels):
                filtered_rows.append(row)
    return filtered_rows

def save_csv(rows, output_csv):
    """Sauvegarde les résultats filtrés en CSV."""
    if not rows:
        print("⚠️ Aucun flux trouvé pour les chaînes demandées.")
        return
    with open(output_csv, "w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

def save_m3u(rows, output_m3u):
    """Sauvegarde les résultats filtrés en playlist M3U."""
    if not rows:
        return
    with open(output_m3u, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for row in rows:
            name = row.get("name", "Unknown")
            url = row.get("url", "")
            group = row.get("group", "")
            country = row.get("country", "")
            lang = row.get("language", "")
            f.write(f'#EXTINF:-1 group-title="{group}" tvg-country="{country}" tvg-language="{lang}",{name}\n')
            f.write(f"{url}\n")

def main():
    print("=== Filtrage des chaînes prioritaires ===")
    if not os.path.exists(INPUT_CSV):
        print(f"❌ Fichier introuvable : {INPUT_CSV}")
        return
    if not os.path.exists(TOP_CHANNELS_FILE):
        print(f"❌ Fichier introuvable : {TOP_CHANNELS_FILE}")
        return
    
    print("📥 Chargement des chaînes...")
    top_channels = load_top_channels(TOP_CHANNELS_FILE)

    print("🔎 Filtrage en cours...")
    filtered_rows = filter_channels(INPUT_CSV, top_channels)

    print(f"💾 Sauvegarde dans {OUTPUT_CSV} et {OUTPUT_M3U}...")
    save_csv(filtered_rows, OUTPUT_CSV)
    save_m3u(filtered_rows, OUTPUT_M3U)

    print(f"✅ Terminé : {len(filtered_rows)} flux trouvés et sauvegardés.")

if __name__ == "__main__":
    main()
