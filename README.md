# IPTV Playlist Automation

Ce dépôt contient un système automatisé pour générer, valider et mettre à jour une playlist IPTV filtrée, compatible avec MyTVOnline 2.

## Structure du dépôt

- `data/sources.csv` : Liste des URLs sources IPTV à valider.
- `generator/validate_streams.py` : Script Python qui teste la validité des flux et génère la playlist filtrée.
- `playlist/playlist_filtered.m3u` : Playlist filtrée générée automatiquement.
- `.github/workflows/update_playlist.yml` : Workflow GitHub Actions pour automatiser la validation et la mise à jour quotidienne.

## Fonctionnement

1. Le workflow GitHub s'exécute automatiquement chaque jour à 4h UTC (configurable).
2. Il installe les dépendances nécessaires, notamment `ffprobe`.
3. Il lance le script de validation des flux qui teste les URLs IPTV dans `data/sources.csv`.
4. Les flux valides sont compilés dans `playlist/playlist_filtered.m3u`.
5. Le workflow pousse automatiquement les modifications validées dans le dépôt GitHub.

## Prérequis pour le workflow

- Un Personal Access Token (PAT) GitHub avec le secret `GH_PAT_TOKEN` configuré dans les Secrets du dépôt pour autoriser le push automatique.
- Le fichier `data/sources.csv` doit être correctement renseigné avec les URLs IPTV à tester.
- L'outil `ffprobe` est installé et accessible dans le runner GitHub Actions via le workflow.

## Commandes manuelles

Pour valider localement les flux (nécessite `ffprobe` installé localement) :

```bash
python generator/validate_streams.py
