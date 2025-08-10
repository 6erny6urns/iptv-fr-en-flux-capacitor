# IPTV FR-EN Flux Capacitor

Playlist IPTV multilingue générée automatiquement via GitHub Actions.

## Structure

- `data/sources.csv` : URLs des playlists sources.
- `generator/main.py` : script de téléchargement et fusion des playlists.
- `generator/filter_and_categorize.py` : script de filtrage, catégorisation, et mise en favoris.
- `playlist/playlist_filtered.m3u` : playlist finale à utiliser dans MyTVOnline.

## Usage

- Modifier `data/sources.csv` pour ajouter/supprimer des sources.
- Ajouter les chaînes favorites dans `generator/filter_and_categorize.py`.
- Pousser les modifications sur GitHub.
- Le workflow GitHub Actions génère et met à jour automatiquement la playlist chaque jour.

## URL playlist

Utiliser cette URL brute dans MyTVOnline pour charger la playlist mise à jour automatiquement :

