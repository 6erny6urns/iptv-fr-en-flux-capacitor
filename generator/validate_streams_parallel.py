#!/usr/bin/env python3
import csv
import os
import re
import sys
import time
import queue
import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests

INPUT_CSV = "data/sources.csv"
OUTPUT_DIR = "playlist"
OUTPUT_PLAYLIST = os.path.join(OUTPUT_DIR, "playlist_filtered.m3u")
LOG_FILE = "validation_log.txt"

DEFAULT_TIMEOUT = 3          # seconds for ffprobe
DEFAULT_WORKERS = 25
DEFAULT_MAX_STREAMS = 25000
DEFAULT_BATCH_SIZE = 2000    # traite par lots pour garder un log fluide
HEAD_TIMEOUT = 0.7           # HEAD precheck
GET_FALLBACK_TIMEOUT = 1.0   # si HEAD ne marche pas

CITIES_FILE = "data/cities_top50.txt"
TOP_CHANNELS_FILE = "data/top_channels.txt"

requests.adapters.DEFAULT_RETRIES = 1

def load_list(path):
    items = []
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s and not s.startswith("#"):
                    items.append(s)
    return items

def check_ffprobe():
    try:
        subprocess.run(["ffprobe","-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False

def is_http_url(s):
    try:
        u = urlparse(s.strip())
        return u.scheme in ("http","https") and u.netloc
    except Exception:
        return False

def extract_sources(csv_path):
    if not os.path.isfile(csv_path):
        print(f"ERROR: CSV source file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    out = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = (row.get("url") or "").strip()
            name = (row.get("name") or "UNKNOWN").strip()
            if url:
                out.append((name, url))
    return out

def http_head_alive(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.head(url, timeout=HEAD_TIMEOUT, allow_redirects=True, headers=headers)
        if r.status_code >= 400:
            return False
        ct = r.headers.get("Content-Type","").lower()
        # on garde large, mais on filtre les HTML évidents
        if "text/html" in ct and not url.lower().endswith(".m3u8"):
            return False
        return True
    except Exception:
        # Certains serveurs ne supportent pas HEAD -> GET rapide
        try:
            r = requests.get(url, timeout=GET_FALLBACK_TIMEOUT, stream=True, headers=headers)
            if r.status_code >= 400:
                return False
            ct = r.headers.get("Content-Type","").lower()
            if "text/html" in ct and not url.lower().endswith(".m3u8"):
                return False
            return True
        except Exception:
            return False

def ffprobe_ok(url, timeout=DEFAULT_TIMEOUT):
    try:
        res = subprocess.run(
            ["ffprobe","-v","error","-show_entries","format=format_name","-of","default=nw=1", url],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout
        )
        return "format_name=" in res.stdout.lower()
    except Exception:
        return False

EXTINF_RE = re.compile(r'#EXTINF[^,]*,(?P<name>.*)$', re.IGNORECASE)

def parse_m3u_text(text):
    """
    Retourne liste [(name, url)]
    On associe chaque URL non-commentée à la dernière ligne #EXTINF.
    """
    lines = (text or "").splitlines()
    results = []
    last_name = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            m = EXTINF_RE.search(line)
            if m:
                last_name = m.group("name").strip()
            else:
                last_name = None
            continue
        if line.startswith("#"):
            continue
        if is_http_url(line):
            name = last_name or "UNKNOWN"
            results.append((name, line))
            last_name = None
    return results

def fetch_m3u(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, timeout=10, headers=headers)
        r.raise_for_status()
        return r.text
    except Exception:
        return ""

def gather_candidates(sources, max_total=DEFAULT_MAX_STREAMS):
    """
    Télécharge chaque M3U source et agrège liste (name,url).
    Coupe si on dépasse max_total pour éviter les jobs infinis.
    """
    all_items = []
    for sname, surl in sources:
        text = fetch_m3u(surl)
        pairs = parse_m3u_text(text)
        all_items.extend(pairs)
        if len(all_items) >= max_total * 2:  # marge avant filtrage
            break
    return all_items[:max_total * 2]

def build_filters():
    cities = [c.lower() for c in load_list(CITIES_FILE)]
    tops = [t.lower() for t in load_list(TOP_CHANNELS_FILE)]
    return cities, tops

def is_candidate_kept(name, url, cities, tops):
    n = (name or "").lower()
    # on limite aux liens plausibles de stream
    if not (url.lower().endswith(".m3u8") or "m3u8" in url.lower() or "playlist" not in url.lower()):
        # tolérant: on garde même si ce n'est pas .m3u8, mais on évite manifestement des pages HTML playlist
        pass
    # priorités: tops puis villes
    for t in tops:
        if t and t in n:
            return True
    for c in cities:
        if c and c in n:
            return True
    # fallback: rejeter si rien ne matche
    return False

def prioritize(items, cities, tops, cap):
    """
    Classement: d'abord correspondances tops, ensuite villes.
    Limite à `cap` éléments.
    """
    def score(item):
        name = (item[0] or "").lower()
        s = 0
        for t in tops:
            if t and t in name:
                s += 2
        for c in cities:
            if c and c in name:
                s += 1
        return -s  # ordre décroissant

    filtered = [it for it in items if is_candidate_kept(it[0], it[1], cities, tops)]
    filtered.sort(key=score)
    return filtered[:cap]

def validate_batch(batch, timeout, workers, logf):
    valid = []
    # 1) pré-filtrage HTTP rapide
    alive = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        fut_map = {pool.submit(http_head_alive, url): (name, url) for name, url in batch}
        for fut in as_completed(fut_map):
            name, url = fut_map[fut]
            ok = False
            try:
                ok = fut.result()
            except Exception:
                ok = False
            if ok:
                alive.append((name, url))

    # 2) ffprobe en parallèle
    with ThreadPoolExecutor(max_workers=workers) as pool:
        fut_map = {pool.submit(ffprobe_ok, url, timeout): (name, url) for name, url in alive}
        for fut in as_completed(fut_map):
            name, url = fut_map[fut]
            ok = False
            try:
                ok = fut.result()
            except Exception:
                ok = False
            if ok:
                line = f"#EXTINF:-1,{name}\n{url}\n"
                valid.append(line)
                print(f"VALID: {name} -> {url}")
                logf.write(f"VALID: {name} -> {url}\n")
            else:
                print(f"INVALID: {name}")
                logf.write(f"INVALID: {name}\n")
    return valid

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--max-streams", type=int, default=DEFAULT_MAX_STREAMS)
    ap.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    args = ap.parse_args()

    if not check_ffprobe():
        print("ERROR: ffprobe not found or not executable. Please install ffprobe.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    sources = extract_sources(INPUT_CSV)
    cities, tops = build_filters()

    print(f"Loaded {len(cities)} cities and {len(tops)} top-channel keywords.")
    print(f"Gathering candidates from {len(sources)} sources...")
    all_items = gather_candidates(sources, max_total=args.max_streams)
    print(f"Initial gathered candidates: {len(all_items)}")

    # prioriser + limiter à max_streams
    candidates = prioritize(all_items, cities, tops, cap=args.max_streams)
    print(f"Candidates after filter/prioritize: {len(candidates)}")

    valid_all = []
    t0 = time.time()

    with open(LOG_FILE, "w", encoding="utf-8") as logf:
        logf.write(f"Start validation: {len(candidates)} candidates, timeout={args.timeout}s, workers={args.workers}\n")
        for i in range(0, len(candidates), args.batch_size):
            batch = candidates[i:i+args.batch_size]
            print(f"\n--- Batch {i//args.batch_size+1} ({len(batch)} items) ---")
            logf.write(f"\n--- Batch {i//args.batch_size+1} ({len(batch)} items) ---\n")
            valid = validate_batch(batch, args.timeout, args.workers, logf)
            valid_all.extend(valid)
            # flush log to disk frequently
            logf.flush()

    # écrire la playlist
    with open(OUTPUT_PLAYLIST, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for line in valid_all:
            f.write(line)

    dt = time.time() - t0
    print(f"\nValidation complete: {len(valid_all)} valid streams.")
    print(f"Saved playlist -> {OUTPUT_PLAYLIST}")
    print(f"Log -> {LOG_FILE}")
    print(f"Elapsed: {dt:.1f}s")

if __name__ == "__main__":
    main()
