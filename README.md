# IPTV Playlist Generator

Ce projet permet de générer automatiquement une **playlist M3U validée** des chaînes TV que vous souhaitez suivre, prête à être utilisée dans MyTVOnline 2. Il supporte à la fois des sources en ligne et un dossier local de fichiers M3U pour la validation.

---

## Contenu du projet

- `validate_streams_parallel_fast.py` : script principal pour filtrer et valider les flux IPTV.  
- `data/sources.csv` : liste des URLs de playlists M3U à analyser.  
- `data/channels_keywords.csv` : liste des chaînes et leurs variantes/mots-clés (5 max par chaîne).  
- `C:\Users\berny\OneDrive\Documents\0000000000_PROJETS\M3U` : dossier local contenant des fichiers M3U pour la 2ᵉ passe.  
- `finale.m3u` : playlist M3U générée avec tous les flux valides.  

---

## Pré-requis

- Python 3.9 ou supérieur  
- Module Python : `requests`  
- Connexion Internet pour la 1ʳᵉ passe (sources en ligne)  
- Accès au dossier local de playlists M3U pour la 2ᵉ passe  

Installation des dépendances :

```bash
pip install requests
