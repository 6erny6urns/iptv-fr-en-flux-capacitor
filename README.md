# IPTV Playlist Generator Automatisé

## Description

Ce projet permet de générer automatiquement une playlist IPTV `.m3u` consolidée, filtrée et validée à partir de multiples sources fiables. L’ensemble du processus est automatisé via un workflow GitHub Actions, garantissant une mise à jour régulière sans intervention manuelle.

---

## Structure du projet


---

## Fonctionnement

1. **Lecture des sources** :  
   Le script `update_playlist.py` lit les URLs IPTV listées dans `data/sources.csv`.

2. **Téléchargement des playlists sources** :  
   Chaque URL est téléchargée, son contenu M3U parsé pour extraire les chaînes.

3. **Validation des flux** :  
   Chaque flux (URL) est testé via requête HTTP HEAD ou GET partiel pour confirmer sa disponibilité.

4. **Filtrage** :  
   Seules les chaînes dont le flux est valide sont conservées.

5. **Écriture de la playlist finale** :  
   La playlist filtrée est écrite dans `playlist/playlist_filtered.m3u`.

6. **Automatisation** :  
   Le workflow GitHub Actions déclenche ce script automatiquement, selon une planification (cron) ou manuellement (dispatch).

7. **Mise à jour et push** :  
   Si la playlist a changé, elle est commitée et poussée vers le dépôt.

---

## Installation / Prérequis

- Python 3.x  
- Librairie Python `requests` (`pip install requests`)

Dans GitHub Actions, l’environnement est configuré automatiquement.

---

## Usage local

```bash
python generator/update_playlist.py
