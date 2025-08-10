# IPTV FR-EN Flux Capacitor

Playlist IPTV multilingue (.m3u/.m3u8) – Français, Anglais – Monde entier

Ce projet propose une playlist IPTV actualisée automatiquement via GitHub Actions, filtrée et organisée pour inclure les chaînes les plus populaires au Québec (Montréal), France (Paris) et États-Unis (New York), en français et en anglais.

---

## Fonctionnalités

- Téléchargement automatique des sources IPTV depuis des URLs configurées dans `data/sources.csv`.  
- Test automatique de validité des flux, suppression des chaînes non fonctionnelles.  
- Filtrage et catégorisation des chaînes selon pays, langue et popularité.  
- Génération d’une playlist optimisée avec une section **FAVORIS** regroupant les chaînes principales.  
- Automatisation complète via GitHub Actions avec mise à jour quotidienne.  
- Compatible avec MyTVOnline 2 et autres lecteurs IPTV prenant en charge les playlists `.m3u`.

---

## Instructions pour mise à jour

1. Commiter et pousser les fichiers modifiés/créés dans le dépôt GitHub.  
2. Lancer manuellement le workflow GitHub Actions depuis l’onglet **Actions** si nécessaire.  
3. Vérifier que le fichier `playlist_filtered.m3u` a été généré dans le dépôt.  
4. Utiliser l’URL GitHub raw pour charger la playlist dans MyTVOnline 2 :  

