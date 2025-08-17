import os
import re
import requests
import concurrent.futures
from pathlib import Path

# --- CONFIGURATION ---
MIN_REQUIRED = 25
MAX_ATTEMPTS = 2
TIMEOUTS = [10, 20]  # 10s d’abord, puis 20s
INPUT_CSV = "data/sources.csv"  # URLs de playlists en ligne
LOCAL_DIR = r"C:\Users\berny\OneDrive\Documents\0000000000_PROJETS\M3U"
OUTPUT_M3U = "finale.m3u"

# --- Mots-clés principaux et variantes (5 max par chaîne) ---
KEYWORDS = {
    "TF1": ["TF1", "T F1", "TF-1", "TF_1", "La Une"],
    "France 2": ["France 2", "FR2", "France2", "F2", "Deux"],
    "France 3": ["France 3", "FR3", "France3", "F3", "Trois"],
    "France 4": ["France 4", "FR4", "France4", "F4", "Quatre"],
    "France 5": ["France 5", "FR5", "France5", "F5", "Cinq"],
    "M6": ["M6", "M 6", "M-6", "M_6", "Métropole 6"],
    "Arte": ["Arte", "ARTE", "ArteTV", "Arte-TV", "La Sept"],
    "6TER": ["6TER", "6 TER", "6-Ter", "SixTer", "Six Ter"],
    "W9": ["W9", "W 9", "W-Neuf", "W_Nine", "Neuf"],
    "TMC": ["TMC", "T M C", "T-MC", "TMC TV", "Télé Monte Carlo"],
    "TFX": ["TFX", "T F X", "TF-X", "TFX TV", "TFX_Channel"],
    "Chérie 25": ["Chérie 25", "Cherie25", "Ch25", "Cherie", "Chérie25TV"],
    "RMC Story": ["RMC Story", "RMCStory", "RMC-S", "RMC_Story", "RMC S"],
    "RMC Découverte": ["RMC Découverte", "RMCDecouverte", "RMC-D", "RMC_D", "RMC Dec"],
    "LCI": ["LCI", "La Chaîne Info", "LCI-TV", "LCI_TV", "LCI Info"],
    "BFM TV": ["BFMTV", "BFM TV", "BFM-TV", "BFM_TV", "BFM"],
    "CNews": ["CNEWS", "C News", "C-News", "iTélé", "Canal News"],
    "Franceinfo": ["Franceinfo", "France Info", "FInfo", "FranceInfoTV", "Info France"],
    "LCP": ["LCP", "La Chaîne Parlementaire", "LCP-TV", "LCP_TV", "LCP Info"],
    "Public Sénat": ["Public Sénat", "PublicSenat", "Senat", "PubSenat", "PSenat"],
    "CANAL+": ["Canal+", "Canal Plus", "C+", "Canal+", "Canal_Plus"],
    "Paris Première": ["Paris Première", "Paris1", "PP TV", "Paris-P", "ParisPremiere"],
    "Téva": ["Téva", "Teva", "TVA Téva", "Teva TV", "Teva_TV"],
    "TV Breizh": ["TV Breizh", "TVB", "TV-Breizh", "Breizh TV", "TVBreizh"],
    "Gulli": ["Gulli", "Gulli TV", "Gulli-TV", "Gulli_TV", "Guli"],
    "Canal J": ["Canal J", "CanalJ", "Canal_J", "CJ TV", "Canal Junior"],
    "CStar": ["CStar", "C Star", "C-Star", "CStar TV", "C_Star"],
    "TV5 Monde": ["TV5", "TV5Monde", "TV 5", "TV-5", "TV_Cinq"],
    "TV8 Mont-Blanc": ["TV8 Mont-Blanc", "TV8", "TV8MB", "TV 8", "Mont-Blanc TV"],
    "France 24": ["France 24", "France24", "F24", "FR24", "France_VingtQuatre"],
    "TVA": ["TVA", "TVA TV", "TVA Québec", "TVA Qc", "TVA Canada"],
    "TVA Sports": ["TVA Sports", "TVA_Sports", "TVA Sport", "TVA-S", "TVA-Sports"],
    "LCN": ["LCN", "LCN TV", "La Chaîne Nouvelles", "LCN-News", "LCN_TV"],
    "Noovo": ["Noovo", "Noovo TV", "NooVo", "NooVo TV", "Noovo_TV"],
    "ICI Radio-Canada": ["Radio-Canada", "ICI Radio-Canada", "RCI", "Radio C", "RadioCanada"],
    "ICI Télé": ["ICI Télé", "IciTele", "ICITele", "ICI-Tele", "ICITV"],
    "Télé-Québec": ["Télé-Québec", "TeleQuebec", "Tele-Quebec", "TQ TV", "TeleQ"],
    "Unis TV": ["Unis TV", "UNIS", "UnisTV", "Unis-TV", "Unis_TV"],
    "VRAK": ["VRAK", "VRAK.TV", "VrakTV", "VRAK_TV", "Vrak"],
    "Télétoon": ["Télétoon", "Teletoon", "Tele-toon", "Télé-toon", "TeletoonTV"],
    "Prise 2": ["Prise 2", "Prise2", "Prise-2", "PriseTwo", "PriseII"],
    "AMI-télé": ["AMI-télé", "AMI Tele", "AMI-Tele", "AMITV", "AMI-TV"],
    "Toute l’Histoire": ["Toute l’Histoire", "Histoire", "TLH", "Histoire TV", "TLH TV"],
    "Planète+": ["Planète+", "Planete Plus", "Planete+", "PlaneteTV", "Planete_Plus"],
    "Historia": ["Historia", "Historia TV", "Histoire", "HistoireTV", "Histo"],
    "Zeste": ["Zeste", "Zeste TV", "Zeste-TV", "ZesteTV", "Zest"],
    "Cinépop": ["Cinépop", "Cinepop", "Ciné Pop", "Ciné-Pop", "Cine-Pop"],
    "Canal D": ["Canal D", "CanalD", "Canal-D", "CanalDTV", "Canal_D"],
    "Canal Vie": ["Canal Vie", "CanalVie", "Canal-Vie", "CanalVieTV", "Canal_Vie"],
    # ... tu peux compléter les 50 chaînes si tu veux, ici je me limite pour exemple
}

# ---------------------------------------------------

def load_sources_online():
    urls = []
    if os.path.exists(INPUT_CSV):
        with open(INPUT_CSV, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("http"):
                    urls.append(line)
    return urls

def load_sources_local(limit=25):
    m3u_files = list(Path(LOCAL_DIR).rglob("*.m3u"))
    m3u_files = m3u_files[:limit]
    urls = []
    for file in m3u_files:
        with open(file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("http"):
                    urls.append(line)
    return urls

def fetch_playlist(url, timeout):
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text.splitlines()
    except Exception:
        return []

def validate_stream(url, timeout):
    for t in TIMEOUTS:
        try:
            resp = requests.get(url, stream=True, timeout=t)
            if resp.status_code == 200:
                return True
        except Exception:
            continue
    return False

def filter_by_keywords(lines):
    results = []
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF"):
            for channel, variants in KEYWORDS.items():
                if any(v.lower() in line.lower() for v in variants):
                    if i + 1 < len(lines):
                        url = lines[i + 1].strip()
                        results.append((channel, line, url))
    return results

def main():
    all_results = []
    found_channels = set()

    for attempt in range(MAX_ATTEMPTS):
        print(f"\n--- Tentative {attempt+1} ---")

        urls = load_sources_online() if attempt == 0 else load_sources_local()
        if not urls:
            print("⚠️ Aucune source trouvée.")
            continue

        temp_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_playlist, u, TIMEOUTS[0]): u for u in urls}
            for future in concurrent.futures.as_completed(futures):
                lines = future.result()
                if lines:
                    temp_results.extend(filter_by_keywords(lines))

        valid_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(validate_stream, url, TIMEOUTS[0]): (ch, info, url) for ch, info, url in temp_results}
            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    ch, info, url = futures[future]
                    if ch not in found_channels:
                        valid_results.append((ch, info, url))
                        found_channels.add(ch)

        all_results.extend(valid_results)
        print(f"Chaînes valides cumulées : {
