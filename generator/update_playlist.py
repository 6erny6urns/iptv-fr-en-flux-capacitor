name: Update IPTV Playlist

on:
  schedule:
    - cron: '0 4 * * *'  # Tous les jours à 4h UTC
  workflow_dispatch:     # Permet un lancement manuel

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Setup Python 3.x
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests

      - name: Create output directory if missing
        run: mkdir -p playlist

      - name: Download initial playlist_filtered.m3u
        run: |
          curl -L -o playlist/playlist_filtered.m3u https://raw.githubusercontent.com/iptv-org/iptv/master/streams/fr.m3u

      - name: List repo structure (debug)
        run: ls -R

      - name: Run stream validation script
        run: python generator/validate_streams.py playlist/playlist_filtered.m3u

      - name: Commit and push filtered playlist and logs
        run: |
          git config user.name "GitHub Actions Bot"
          git config user.email "actions@github.com"
          git add playlist_filtered.m3u validation_log.txt
          git commit -m "Automated playlist update with validated streams"
          git push
        continue-on-error: true
