#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_filter_validate_m3u.py
Pipeline: read sources (CSV or env), download .m3u files, parse entries, filter, validate,
deduplicate, export CSV + M3U, log, and optionally commit/push to GitHub if in a repo.
Designed for Windows but cross-platform.
"""
import argparse
import csv
import os
import re
import sys
import time
import signal
import shutil
import subprocess
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from urllib.parse import urlparse, unquote

import requests

# -----------------------------
# Configuration (modifiable)
# -----------------------------
# Default local CSV path (Windows)
DEFAULT_LOCAL_CSV = r"C:\Users\berny\OneDrive\Documents\0000000000_PROJETS\M3U\sources.csv"

# Internal default filters (can be overridden by CLI)
DEFAULT_FILTER_LANGS = []       # e.g., ["fr", "en"]
DEFAULT_FILTER_COUNTRIES = []   # e.g., ["CA", "FR"]
DEFAULT_FILTER_CATEGORIES = []  # e.g., ["News", "Sport"]

# Validation settings
HTTP_TIMEOUT = 6                 # seconds per HTTP request
START_CHUNK_BYTES = 2048         # bytes enough to assert liveness
USER_AGENT = "M3U-Validator/1.0 (+https://github.com/)"

# Output filenames (fixed by spec)
OUT_FILTERED_VALID_CSV = "filtered_valid_m3u.csv"
OUT_FILTERED_OUT_CSV = "filtered_out.csv"
OUT_FINAL_PLAYLIST = "final_playlist.m3u"
OUT_LOG = "log_parse_filter_validate_m3u.txt"

RAW_DIR = "RAW"

# Git auto-commit
GIT_COMMIT_MESSAGE = "chore: update playlist and logs"
AUTO_PUSH = True

# ---------------------------------
# Logging (append, simple text log)
# ---------------------------------
class Logger:
    def __init__(self, path: str):
        self.path = path
        # rotate if > 5MB
        if os.path.exists(self.path) and os.path.getsize(self.path) > 5 * 1024 * 1024:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.move(self.path, f"{self.path}.{ts}.bak")
        self._write(f"=== RUN @ {datetime.now().isoformat()} ===")

    def _write(self, line: str):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")

    def info(self, msg: str):
        self._write(f"[INFO] {msg}")

    def warn(self, msg: str):
        self._write(f"[WARN] {msg}")

    def err(self, msg: str):
        self._write(f"[ERROR] {msg}")

# -----------------------------
# Utilities
# -----------------------------
def is_url(s: str) -> bool:
    try:
        u = urlparse(s.strip())
        return u.scheme in ("http", "https") and bool(u.netloc)
    except Exception:
        return False

def http_head_or_get(url: str, timeout: int = HTTP_TIMEOUT) -> Optional[requests.Response]:
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.head(url, timeout=timeout, allow_redirects=True, headers=headers)
        if r.status_code >= 200 and r.status_code < 400:
            return r
        # fallback to get
        r = requests.get(url, timeout=timeout, allow_redirects=True, headers=headers, stream=True)
        return r
    except Exception:
        return None

def safe_filename(s: str) -> str:
    s = unquote(s)
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s).strip("_")
    return s[:180] if len(s) > 180 else s

def ensure_dirs():
    os.makedirs(RAW_DIR, exist_ok=True)

def read_sources_from_csv(path: str) -> List[str]:
    urls = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            candidate = row[0].strip()
            if candidate and is_url(candidate):
                urls.append(candidate)
    return urls

def read_sources_from_env() -> List[str]:
    blob = os.environ.get("M3U_SOURCES", "").strip()
    urls = []
    for line in blob.splitlines():
        s = line.strip()
        if is_url(s):
            urls.append(s)
    return urls

def download_m3u(url: str, logger: Logger) -> Optional[str]:
    headers = {"User-Agent": USER_AGENT}
    try:
        with requests.get(url, timeout=HTTP_TIMEOUT, headers=headers, stream=True) as r:
            if r.status_code >= 400:
                logger.warn(f"Download failed {r.status_code} for {url}")
                return None
            # guess filename
            name = safe_filename(os.path.basename(urlparse(url).path) or "playlist.m3u")
            if not name.lower().endswith((".m3u", ".m3u8", ".txt")):
                name += ".m3u"
            dest = os.path.join(RAW_DIR, f"{int(time.time())}_{name}")
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            logger.info(f"Downloaded -> {dest}")
            return dest
    except Exception as e:
        logger.err(f"Exception download {url}: {e}")
        return None

# -----------------------------
# M3U parsing
# -----------------------------
M3U_HEADER = "#EXTM3U"
EXTINF = "#EXTINF"

def parse_m3u(path: str) -> List[Dict[str, str]]:
    """
    Return list of entries with keys:
      - name
      - url
      - tvg_id, tvg_name, tvg_logo, group_title, country, language, quality (best-effort)
    """
    entries: List[Dict[str, str]] = []
    current_meta = ""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [ln.rstrip("\n") for ln in f]
    except UnicodeDecodeError:
        with open(path, "r", encoding="latin-1", errors="ignore") as f:
            lines = [ln.rstrip("\n") for ln in f]

    if not lines or not lines[0].startswith(M3U_HEADER):
        # tolerate missing header
        pass

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith(EXTINF):
            current_meta = line
            # next non-empty non-comment line assumed URL
            j = i + 1
            url = ""
            while j < len(lines):
                cand = lines[j].strip()
                j += 1
                if cand and not cand.startswith("#"):
                    url = cand
                    break
            meta = extract_metadata(current_meta)
            meta["url"] = url
            if "name" not in meta or not meta["name"]:
                meta["name"] = derive_name_from_meta(current_meta, url)
            entries.append(meta)
            i = j
        else:
            i += 1
    return entries

def extract_metadata(extinf_line: str) -> Dict[str, str]:
    # Example: #EXTINF:-1 tvg-id="xxx" tvg-name="yyy" tvg-logo="..." group-title="News",Channel Name
    meta: Dict[str, str] = {}
    # capture quoted attributes
    for key in ["tvg-id", "tvg-name", "tvg-logo", "group-title", "country", "language", "tvg-country", "tvg-language"]:
        m = re.search(rf'{key}="([^"]*)"', extinf_line, re.IGNORECASE)
        if m:
            meta[key.replace("-", "_")] = m.group(1).strip()
    # capture name after comma
    m = re.search(r",\s*(.+)$", extinf_line)
    if m:
        meta["name"] = m.group(1).strip()
    # heuristic quality tags
    q = []
    for tag in ["UHD", "4K", "1080", "720", "HD", "FHD", "SD", "HEVC", "H265"]:
        if re.search(rf"\b{tag}\b", extinf_line, re.IGNORECASE):
            q.append(tag.upper())
    if q:
        meta["quality"] = "/".join(sorted(set(q)))
    # harmonize country/language
    if "tvg_country" in meta and "country" not in meta:
        meta["country"] = meta["tvg_country"]
    if "tvg_language" in meta and "language" not in meta:
        meta["language"] = meta["tvg_language"]
    # group-title as category
    if "group_title" in meta:
        meta["category"] = meta["group_title"]
    return meta

def derive_name_from_meta(extinf_line: str, url: str) -> str:
    # fallbacks
    m = re.search(r",\s*(.+)$", extinf_line)
    if m:
        return m.group(1).strip()
    # else from URL
    path = urlparse(url).path
    base = os.path.basename(path)
    if base:
        base = os.path.splitext(base)[0]
    return base or "Unknown"

# -----------------------------
# Filtering & Dedup
# -----------------------------
def passes_filters(entry: Dict[str, str], langs: List[str], countries: List[str], categories: List[str]) -> Tuple[bool, str]:
    def norm(x: Optional[str]) -> str:
        return (x or "").strip().lower()

    lang = norm(entry.get("language") or entry.get("tvg_name"))
    country = norm(entry.get("country"))
    category = norm(entry.get("category"))
    name = norm(entry.get("name"))

    # apply only if filter list non-empty
    if langs and lang not in [l.lower() for l in langs] and not any(f"({l.lower()})" in name for l in langs):
        return False, "lang_filter"
    if countries and country not in [c.lower() for c in countries] and not any(f"[{c.lower()}]" in name for c in countries):
        return False, "country_filter"
    if categories and category not in [g.lower() for g in categories]:
        return False, "category_filter"
    return True, "ok"

def canonical_key(entry: Dict[str, str]) -> str:
    # Deduplicate apparent duplicates for MyTVOnline 2: normalize name + domain
    name = re.sub(r"\s+", " ", (entry.get("name") or "").strip().lower())
    try:
        host = urlparse(entry.get("url") or "").netloc.lower()
    except Exception:
        host = ""
    category = (entry.get("category") or "").strip().lower()
    lang = (entry.get("language") or "").strip().lower()
    country = (entry.get("country") or "").strip().lower()
    return "|".join([name, host, category, lang, country])

def strip_redundant_tags(name: str, country: str, language: str, category: str) -> str:
    # Avoid noisy, repeated tags in sidebar
    base = name
    for tag in [country, language, category]:
        if not tag:
            continue
        tag_norm = tag.strip().lower()
        base = re.sub(rf"\b\(?{re.escape(tag_norm)}\)?\b", "", base, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", base).strip()

# -----------------------------
# Validation
# -----------------------------
def validate_stream(url: str) -> Tuple[bool, str, int]:
    """
    Returns (is_valid, reason, status_code)
    """
    headers = {"User-Agent": USER_AGENT}
    try:
        with requests.get(url, timeout=HTTP_TIMEOUT, headers=headers, stream=True) as r:
            status = r.status_code
            if status >= 400:
                return False, f"http_{status}", status
            # try to read a small chunk
            total = 0
            for chunk in r.iter_content(chunk_size=1024):
                if not chunk:
                    break
                total += len(chunk)
                if total >= START_CHUNK_BYTES:
                    break
            if total > 0:
                return True, "ok", status
            else:
                return False, "no_data", status
    except requests.exceptions.Timeout:
        return False, "timeout", 0
    except Exception as e:
        return False, f"exception:{type(e).__name__}", 0

# -----------------------------
# Export
# -----------------------------
def write_csv(path: str, rows: List[Dict[str, str]], logger: Logger):
    fieldnames = ["name","url","country","language","category","quality","tvg_id","tvg_name","tvg_logo"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    logger.info(f"Wrote CSV {path} ({len(rows)} rows)")

def write_m3u(path: str, rows: List[Dict[str, str]], logger: Logger):
    with open(path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for e in rows:
            attrs = []
            if e.get("tvg_id"): attrs.append(f'tvg-id="{e["tvg_id"]}"')
            if e.get("tvg_name"): attrs.append(f'tvg-name="{e["tvg_name"]}"')
            if e.get("tvg_logo"): attrs.append(f'tvg-logo="{e["tvg_logo"]}"')
            if e.get("category"): attrs.append(f'group-title="{e["category"]}"')
            if e.get("country"): attrs.append(f'country="{e["country"]}"')
            if e.get("language"): attrs.append(f'language="{e["language"]}"')
            if e.get("quality"): attrs.append(f'quality="{e["quality"]}"')
            name = strip_redundant_tags(e.get("name",""), e.get("country",""), e.get("language",""), e.get("category",""))
            f.write(f'#EXTINF:-1 {" ".join(attrs)},{name}\n')
            f.write(f'{e.get("url","")}\n')
    logger.info(f"Wrote M3U {path} ({len(rows)} entries)")

# -----------------------------
# Git integration
# -----------------------------
def in_git_repo() -> bool:
    return os.path.isdir(".git")

def git(*args: str) -> Tuple[int, str]:
    try:
        cp = subprocess.run(["git", *args], capture_output=True, text=True)
        out = (cp.stdout or "") + (cp.stderr or "")
        return cp.returncode, out
    except Exception as e:
        return 1, str(e)

def commit_and_push(logger: Logger):
    if not in_git_repo():
        logger.warn("Not in a git repository, skipping commit/push.")
        return
    code, out = git("add", OUT_FILTERED_VALID_CSV, OUT_FILTERED_OUT_CSV, OUT_FINAL_PLAYLIST, OUT_LOG)
    logger.info(out.strip())
    code, out = git("commit", "-m", GIT_COMMIT_MESSAGE)
    logger.info(out.strip())
    if AUTO_PUSH:
        code, out = git("push")
        logger.info(out.strip())

# -----------------------------
# Ctrl+C handling
# -----------------------------
ABORT_REQUESTED = False

def _handle_sigint(sig, frame):
    global ABORT_REQUESTED
    ABORT_REQUESTED = True
    # Do not exit immediately; main loop will checkpoint and exit gracefully.
    print("\n[!] Ctrl+C detected — completing current step and saving partial results...")

signal.signal(signal.SIGINT, _handle_sigint)

# -----------------------------
# Main pipeline
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Parse, filter, validate M3U playlists and publish outputs.")
    parser.add_argument("--csv", help="Path to local CSV containing M3U URLs (default: internal Windows path).")
    parser.add_argument("--lang", nargs="*", default=DEFAULT_FILTER_LANGS, help="Filter languages (e.g. fr en).")
    parser.add_argument("--country", nargs="*", default=DEFAULT_FILTER_COUNTRIES, help="Filter countries (e.g. CA FR).")
    parser.add_argument("--category", nargs="*", default=DEFAULT_FILTER_CATEGORIES, help="Filter categories (e.g. News Sport).")
    parser.add_argument("--skip-validate", action="store_true", help="Skip HTTP validation (fast parse/filter only).")
    parser.add_argument("--no-git", action="store_true", help="Do not commit/push outputs.")
    args = parser.parse_args()

    print("Processing... (press Ctrl+C to abort)")

    ensure_dirs()
    logger = Logger(OUT_LOG)

    # Read sources
    sources: List[str] = []
    if os.environ.get("GITHUB_ACTIONS") == "true":
        sources = read_sources_from_env()
        logger.info(f"CI mode: read {len(sources)} URLs from env M3U_SOURCES")
    else:
        csv_path = args.csv or DEFAULT_LOCAL_CSV
        if os.path.exists(csv_path):
            sources = read_sources_from_csv(csv_path)
            logger.info(f"Local mode: read {len(sources)} URLs from CSV {csv_path}")
        else:
            logger.err(f"CSV not found: {csv_path}")
            print(f"[ERROR] CSV not found: {csv_path}")
            sys.exit(1)

    # Verify URLs are reachable
    verified = []
    for i, url in enumerate(sources, 1):
        if ABORT_REQUESTED: break
        ok = is_url(url) and (http_head_or_get(url) is not None)
        if ok:
            verified.append(url)
        else:
            logger.warn(f"Unreachable or invalid URL: {url}")
        pct = int(i * 100 / max(1, len(sources)))
        print(f"[1/5] Verify URLs: {i}/{len(sources)} ({pct}%)", end="\r", flush=True)
    print()

    # Download
    downloaded_files = []
    for i, url in enumerate(verified, 1):
        if ABORT_REQUESTED: break
        dest = download_m3u(url, logger)
        if dest:
            downloaded_files.append(dest)
        pct = int(i * 100 / max(1, len(verified)))
        print(f"[2/5] Download: {i}/{len(verified)} ({pct}%)", end="\r", flush=True)
    print()

    # Parse
    all_entries: List[Dict[str, str]] = []
    for i, path in enumerate(downloaded_files, 1):
        if ABORT_REQUESTED: break
        parsed = parse_m3u(path)
        all_entries.extend(parsed)
        print(f"[3/5] Parse: {i}/{len(downloaded_files)} ({int(i*100/max(1,len(downloaded_files)))}%)", end="\r", flush=True)
    print()
    logger.info(f"Parsed total entries: {len(all_entries)}")

    # Filter
    kept, filtered_out = [], []
    for i, e in enumerate(all_entries, 1):
        if ABORT_REQUESTED: break
        ok, reason = passes_filters(e, args.lang, args.country, args.category)
        if ok:
            kept.append(e)
        else:
            e2 = e.copy()
            e2["reject_reason"] = reason
            filtered_out.append(e2)
        if i % 200 == 0:
            print(f"[4/5] Filtered {i}/{len(all_entries)}", end="\r", flush=True)
    print()
    logger.info(f"After filtering: kept={len(kept)} rejected={len(filtered_out)}")

    # Validate
    valid, invalid = [], []
    if not args.skip_validate:
        for i, e in enumerate(kept, 1):
            if ABORT_REQUESTED: break
            ok, reason, status = validate_stream(e.get("url",""))
            if ok:
                valid.append(e)
            else:
                e2 = e.copy()
                e2["reject_reason"] = reason
                e2["http_status"] = status
                invalid.append(e2)
            if i % 50 == 0 or i == len(kept):
                pct = int(i * 100 / max(1, len(kept)))
                print(f"[5/5] Validate: {i}/{len(kept)} ({pct}%)", end="\r", flush=True)
        print()
    else:
        valid = kept
        logger.warn("Validation skipped by flag --skip-validate")
    logger.info(f"Validation results: valid={len(valid)} invalid={len(invalid)}")

    # Deduplicate
    seen = set()
    deduped = []
    for e in valid:
        key = canonical_key(e)
        if key not in seen:
            seen.add(key)
            deduped.append(e)
    logger.info(f"Deduplicated: {len(valid)} -> {len(deduped)}")

    # Export
    write_csv(OUT_FILTERED_VALID_CSV, deduped, logger)
    write_csv(OUT_FILTERED_OUT_CSV, filtered_out + invalid, logger)
    write_m3u(OUT_FINAL_PLAYLIST, deduped, logger)

    # Commit/push
    if not args.no_git:
        commit_and_push(logger)

    # Summary
    print("— Summary —")
    print(f"Sources (input): {len(sources)}")
    print(f"Verified URLs  : {len(verified)}")
    print(f"Downloaded     : {len(downloaded_files)}")
    print(f"Parsed entries : {len(all_entries)}")
    print(f"Kept (pre-val) : {len(kept)}")
    if not args.skip_validate:
        print(f"Valid streams  : {len(deduped)} (after dedup)")
        print(f"Invalid/Rejected saved to: {OUT_FILTERED_OUT_CSV}")
    print(f"Final playlist : {OUT_FINAL_PLAYLIST}")
    print("Done.")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        # Already handled; ensure partial files are present if any
        print("\nInterrupted. Partial results saved if available.")
        sys.exit(130)
