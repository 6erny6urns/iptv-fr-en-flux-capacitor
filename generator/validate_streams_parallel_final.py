#!/usr/bin/env python3
"""
IPTV Playlist Optimizer
Filtre et valide les flux IPTV depuis des sources M3U multiples
Optimisé pour GitHub Actions et environnements CI/CD
"""

import os
import sys
import time
import requests
import glob
import csv
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
from typing import Dict, List, Tuple

# --- CONFIGURATION ---
DEFAULT_CONFIG = {
    "LOCAL_M3U_DIR": "m3u_sources",
    "CHANNELS_CSV": "data/channels_keywords.csv", 
    "OUTPUT_M3U": "playlist/playlist_filtered.m3u",
    "MAX_URLS_PER_CHANNEL": 3,
    "TIMEOUT_INITIAL": 8,
    "TIMEOUT_SECOND_PASS": 15,
    "MAX_WORKERS": 10,
    "LOG_LEVEL": "INFO"
}

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('iptv_optimizer.log')
    ]
)
logger = logging.getLogger(__name__)

class IPTVOptimizer:
    def __init__(self, config: Dict = None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def read_keywords(self, csv_path: str) -> Dict[str, List[str]]:
        """Lit les mots-clés depuis le fichier CSV"""
        keywords = {}
        csv_file = Path(csv_path)
        
        if not csv_file.exists():
            logger.error(f"Fichier CSV introuvable: {csv_path}")
            return keywords
            
        try:
            with open(csv_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    channel = row["channel"].strip()
                    kw_list = [k.strip() for k in row["keyword"].split("|")[:5] if k.strip()]
                    if channel and kw_list:
                        keywords[channel] = kw_list
            logger.info(f"Chargé {len(keywords)} chaînes avec mots-clés")
        except Exception as e:
            logger.error(f"Erreur lecture CSV: {e}")
            
        return keywords

    def find_m3u_files(self, base_dir: str) -> List[str]:
        """Trouve tous les fichiers M3U récursivement"""
        base_path = Path(base_dir)
        if not base_path.exists():
            logger.warning(f"Dossier M3U introuvable: {base_dir}")
            return []
            
        m3u_files = list(base_path.glob("**/*.m3u"))
        logger.info(f"Trouvé {len(m3u_files)} fichiers M3U")
        return [str(f) for f in m3u_files]

    def parse_m3u_urls(self, file_path: str) -> List[str]:
        """Extrait les URLs depuis un fichier M3U"""
        urls = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line.startswith("http"):
                        urls.append(line)
        except Exception as e:
            logger.warning(f"Erreur lecture {file_path}: {e}")
        return urls

    def filter_urls_by_keywords(self, urls: List[str], keywords: Dict[str, List[str]]) -> List[Tuple[str, str]]:
        """Filtre les URLs par mots-clés et retourne (url, channel_name)"""
        filtered = []
        for url in urls:
            url_lower = url.lower()
            for channel, kws in keywords.items():
                if any(kw.lower() in url_lower for kw in kws):
                    filtered.append((url, channel))
                    break
        logger.info(f"URLs filtrées: {len(filtered)}")
        return filtered

    def validate_url(self, url: str, timeout: int = None) -> bool:
        """Valide une URL avec timeout adaptatif"""
        timeout = timeout or self.config["TIMEOUT_INITIAL"]
        try:
            response = self.session.head(
                url, 
                timeout=timeout, 
                allow_redirects=True,
                verify=False  # Pour éviter les erreurs SSL sur certains flux
            )
            return response.status_code == 200
        except Exception:
            return False

    def validate_url_with_retry(self, url_channel: Tuple[str, str]) -> Tuple[str, str, bool]:
        """Valide une URL avec retry logique"""
        url, channel = url_channel
        
        # Premier essai
        is_valid = self.validate_url(url, self.config["TIMEOUT_INITIAL"])
        
        # Deuxième essai si échec
        if not is_valid:
            is_valid = self.validate_url(url, self.config["TIMEOUT_SECOND_PASS"])
            
        return url, channel, is_valid

    def validate_urls_parallel(self, url_channels: List[Tuple[str, str]]) -> Dict[str, List[str]]:
        """Valide les URLs en parallèle"""
        valid_urls = {}
        total = len(url_channels)
        completed = 0
        start_time = time.time()

        logger.info(f"Début validation de {total} URLs...")

        with ThreadPoolExecutor(max_workers=self.config["MAX_WORKERS"]) as executor:
            # Soumettre les tâches
            future_to_url = {
                executor.submit(self.validate_url_with_retry, url_channel): url_channel 
                for url_channel in url_channels
            }

            for future in as_completed(future_to_url):
                url, channel, is_valid = future.result()
                completed += 1

                if is_valid:
                    if channel not in valid_urls:
                        valid_urls[channel] = []
                    if len(valid_urls[channel]) < self.config["MAX_URLS_PER_CHANNEL"]:
                        valid_urls[channel].append(url)

                # Affichage progression
                if completed % 50 == 0 or completed == total:
                    elapsed = time.time() - start_time
                    pct = (completed / total) * 100
                    rate = completed / elapsed if elapsed > 0 else 0
                    est_remaining = (total - completed) / rate if rate > 0 else 0
                    
                    logger.info(
                        f"Progression: {completed}/{total} ({pct:.1f}%) | "
                        f"Taux: {rate:.1f} URLs/s | "
                        f"Restant: {int(est_remaining)}s | "
                        f"Chaînes valides: {len(valid_urls)}"
                    )

        return valid_urls

    def write_playlist(self, valid_urls: Dict[str, List[str]], output_path: str):
        """Écrit la playlist finale"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                f.write(f"#EXTINF:-1 group-title=\"Generated\",Generated by IPTV Optimizer - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("https://github.com/your-username/your-repo\n")
                
                for channel, urls in sorted(valid_urls.items()):
                    for idx, url in enumerate(urls, 1):
                        line_name = f"{channel}_{idx}" if idx > 1 else channel
                        f.write(f"#EXTINF:-1 group-title=\"{channel}\",{line_name}\n{url}\n")
            
            logger.info(f"Playlist sauvegardée: {output_path}")
        except Exception as e:
            logger.error(f"Erreur écriture playlist: {e}")

    def run(self) -> bool:
        """Exécute le processus complet"""
        try:
            # Lecture des mots-clés
            keywords = self.read_keywords(self.config["CHANNELS_CSV"])
            if not keywords:
                logger.error("Aucun mot-clé trouvé, arrêt du processus")
                return False

            # Recherche des fichiers M3U
            m3u_files = self.find_m3u_files(self.config["LOCAL_M3U_DIR"])
            if not m3u_files:
                logger.error("Aucun fichier M3U trouvé, arrêt du processus")
                return False

            # Extraction des URLs
            all_urls = []
            for m3u_file in m3u_files:
                file_urls = self.parse_m3u_urls(m3u_file)
                all_urls.extend(file_urls)
                logger.debug(f"{m3u_file}: {len(file_urls)} URLs")

            logger.info(f"Total URLs extraites: {len(all_urls)}")

            # Filtrage par mots-clés
            filtered_url_channels = self.filter_urls_by_keywords(all_urls, keywords)
            
            if not filtered_url_channels:
                logger.error("Aucune URL filtrée, vérifiez vos mots-clés")
                return False

            # Validation en parallèle
            valid_urls = self.validate_urls_parallel(filtered_url_channels)

            # Écriture de la playlist
            self.write_playlist(valid_urls, self.config["OUTPUT_M3U"])

            # Statistiques finales
            total_valid = sum(len(urls) for urls in valid_urls.values())
            logger.info(f"Processus terminé avec succès:")
            logger.info(f"  - Chaînes trouvées: {len(valid_urls)}")
            logger.info(f"  - URLs valides: {total_valid}")
            
            for channel, urls in sorted(valid_urls.items()):
                logger.info(f"  - {channel}: {len(urls)} flux")

            return True

        except Exception as e:
            logger.error(f"Erreur critique: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Optimiseur de playlists IPTV")
    parser.add_argument("--m3u-dir", default=DEFAULT_CONFIG["LOCAL_M3U_DIR"], help="Dossier des fichiers M3U")
    parser.add_argument("--channels-csv", default=DEFAULT_CONFIG["CHANNELS_CSV"], help="Fichier CSV des chaînes")
    parser.add_argument("--output", default=DEFAULT_CONFIG["OUTPUT_M3U"], help="Fichier de sortie M3U")
    parser.add_argument("--max-per-channel", type=int, default=DEFAULT_CONFIG["MAX_URLS_PER_CHANNEL"], help="Max URLs par chaîne")
    parser.add_argument("--workers", type=int, default=DEFAULT_CONFIG["MAX_WORKERS"], help="Nombre de workers parallèles")
    parser.add_argument("--verbose", action="store_true", help="Mode verbose")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    config = {
        "LOCAL_M3U_DIR": args.m3u_dir,
        "CHANNELS_CSV": args.channels_csv,
        "OUTPUT_M3U": args.output,
        "MAX_URLS_PER_CHANNEL": args.max_per_channel,
        "MAX_WORKERS": args.workers
    }
    
    optimizer = IPTVOptimizer(config)
    success = optimizer.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
