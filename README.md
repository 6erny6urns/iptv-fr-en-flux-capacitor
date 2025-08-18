# M3U_Project_GitHub

Script unique **`parse_filter_validate_m3u.py`** pour télécharger, parser, filtrer, valider et publier des playlists IPTV, avec automatisation GitHub Actions.

## 🧭 Résumé
- Lecture des **sources** (CSV local *ou* variable d’environnement `M3U_SOURCES` pour CI).
- **Téléchargement** dans `RAW/` (auto-créé).
- **Parsing** des entrées `#EXTINF` + URL.
- **Filtrage** par langue, pays, catégorie (modifiables + CLI).
- **Validation** HTTP rapide (réponse + début de flux).
- **Déduplication** optimisée pour **MyTVOnline 2** (réduction des doublons apparents).
- **Exports** : `filtered_valid_m3u.csv`, `filtered_out.csv`, `final_playlist.m3u`, `log_parse_filter_validate_m3u.txt`.
- **Git** : si le repo est initialisé, `git add/commit/push` automatique.
- **CI** : workflow **`update_playlist.yml`** exécute le script chaque jour.

## 🔧 Prérequis
- Python 3.9+
- `pip install requests`
- Git (pour commit/push automatique) et un remote `origin` configuré.

## 📂 Arborescence
```
/M3U_Project_GitHub
├─ parse_filter_validate_m3u.py
├─ run_parse_filter_validate_m3u.bat
├─ README.md
├─ filtered_valid_m3u.csv
├─ filtered_out.csv
├─ final_playlist.m3u
├─ log_parse_filter_validate_m3u.txt
├─ RAW/
│   └─ [fichiers m3u téléchargés]
└─ .github/workflows/
    └─ update_playlist.yml
```

## 🖥️ Utilisation locale (Windows)
1. Placez votre CSV **local** des sources M3U ici :  
   `C:\Users\berny\OneDrive\Documents\0000000000_PROJETS\M3U\sources.csv`
2. Double-cliquez **`run_parse_filter_validate_m3u.bat`**.  
   - Le lanceur propose d’entrer des filtres (langue/pays/catégorie).  
   - Message visible : `Processing... (press Ctrl+C to abort)`  
   - Une interruption **Ctrl+C** déclenche une sauvegarde propre.
3. Les fichiers générés seront commités/poussés si le dossier est un dépôt Git.

> ⚠️ Vous pouvez surcharger le CSV par défaut avec `--csv "C:\mon\autre\sources.csv"`.

## 🏗️ Détails techniques
- **Parsing** : extraction `tvg-id`, `tvg-name`, `tvg-logo`, `group-title`→`category`, `country`, `language`, heuristique `quality`.
- **Filtrage** : appliqué seulement si la liste est non vide.  
  Normalisation en minuscules ; support rudimentaire de tags dans le nom `(fr)`, `[CA]`.
- **Validation** : requêtes HTTP avec timeout court, lecture de quelques kilo-octets pour attester la vivacité.
- **Déduplication** : clé canonique `name|host|category|language|country` pour limiter les doublons dans **MyTVOnline 2**.
- **M3U final** : suppression des tags redondants dans les `name` pour des métadonnées **claires, uniques, non répétitives**.

## ☁️ Automatisation GitHub Actions
Le workflow **`update_playlist.yml`** s’exécute **chaque jour**. Deux modes d’alimentation des sources :

1) **Secrets (recommandé pour CI)**  
   - Ajoutez un secret de dépôt **`M3U_SOURCES`** contenant une liste d’URLs (une par ligne).  
   - Avantage : aucun CSV dans le repo (respect de la contrainte “les CSV restent locaux”).

2) **Pas de secrets**  
   - Le job tournera mais ne pourra pas rafraîchir sans sources. Le script échouera proprement.

### Variables/Secrets utilisés par le workflow
- `M3U_SOURCES` (secret) : URLs des playlists à agréger (une par ligne).
- Facultatif : `GIT_USER_NAME`, `GIT_USER_EMAIL` (pour configurer l’auteur de commit).

## 🌐 URL publique de la playlist
Une fois poussée, votre playlist est accessible en **Raw** depuis GitHub, par exemple :  
`https://raw.githubusercontent.com/<votre_user>/<votre_repo>/main/final_playlist.m3u`

## 🧩 Exemples
- Exécuter sans validation (rapide) :  
  `python parse_filter_validate_m3u.py --skip-validate --lang fr en --country CA FR`
- Exécuter en forçant un autre CSV :  
  `python parse_filter_validate_m3u.py --csv "D:\sources_alt.csv" --category News Sport`

## ❗ Remarques
- Le script tente un **commit/push** automatique si `.git/` est présent et un `origin` est configuré.  
  Utilisez `--no-git` pour le désactiver.
- Le workflow CI configure automatiquement `git` si des variables d’auteur sont fournies.

## 📄 Licence
MIT (à adapter selon vos besoins).
