from services.realdebrid import test_connection, is_cached, add_magnet
from services.torrentio import get_movie_streams, get_episode_streams
from services.database import init_db, has_attempted, mark_attempted, has_cached_quality, mark_cached_quality
from services.filters import (
    extract_seeders,
    is_blacklisted,
    extract_resolution,
    extract_size_mb,
    is_large_pack,
    extract_seasons_from_title,
)
from services.config import get_or_create_config
import time
from services.imdb_search import search_imdb_id
from services.imdb_list_titles import extract_imdb_ids_from_list, extract_titles_from_list
from services.imdb_series_episodes import get_all_episodes, get_series_id
import ctypes
import os
import gc

def set_low_priority():
    """Set process priority to BELOW_NORMAL to prevent frame drops in games."""
    try:
        if os.name == 'nt':
            # BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
            ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00004000)
            print("[INFO] Process priority set to BELOW_NORMAL (Low CPU impact mode)")
        else:
            try:
                os.nice(10)
            except Exception:
                pass
    except Exception as e:
        print(f"[WARN] Could not set process priority: {e}")


STOP_REQUESTED = False
# Tray tooltip state (read by ui.py)
TRAY_RUNNING = False
TRAY_CURRENT_ITEM = ""
APP_VERSION = "0.2.0"


def start_app(imdb_list_urls=None, movies=None, series_list=None, run_mode=None, repeat_minutes=None, api_key=None):
    """
    imdb_list_urls: list of IMDb list URLs (or None)
    movies: list of IMDb IDs or movie titles, one per line (or None)
    series_list: list of IMDb series IDs or series URLs, one per line (or None)
    run_mode: "oneshot" (default), "loop", or "interval"
    repeat_minutes: used when run_mode == "interval"
    api_key: Real-Debrid API Key (overrides config)
    """
    init_db()
    set_low_priority() # Optimize thread priority for background usage
    global STOP_REQUESTED, TRAY_RUNNING, TRAY_CURRENT_ITEM
    STOP_REQUESTED = False
    TRAY_RUNNING = False
    TRAY_CURRENT_ITEM = ""

    print(f"[INFO] CacheWarmer v{APP_VERSION} booting...")

    config = get_or_create_config()
    if not api_key:
        api_key = config.get("real_debrid_api_key", "")
    mode = run_mode if run_mode is not None else config.get("run_mode", "oneshot")
    interval_mins = repeat_minutes if repeat_minutes is not None else config.get("repeat_minutes", 60)

    if not test_connection(api_key):
        print("[ERROR] Real-Debrid connection failed.")
        TRAY_RUNNING = False
        TRAY_CURRENT_ITEM = ""
        return

    print("[INFO] Real-Debrid connection successful!")

    # ------------------------
    # Load Inputs (from UI text boxes only, no .txt files)
    # ------------------------

    imdb_list = []

    # Movies/IDs from UI "Movies (IMDb IDs)" box
    if movies is not None:
        for line in movies if isinstance(movies, list) else movies.strip().splitlines():
            line = line.strip()
            if line:
                imdb_list.append(line)

    # IMDb list URLs from UI "IMDb List URL(s)" box
    if imdb_list_urls is not None:
        urls = imdb_list_urls if isinstance(imdb_list_urls, list) else [u.strip() for u in imdb_list_urls.strip().splitlines() if u.strip()]
        for url in urls:
            print("[INFO] Reading IMDb list:", url)
            ids = extract_imdb_ids_from_list(url)
            if ids:
                print(f"[INFO] Found IMDb IDs: {len(ids)}")
                imdb_list.extend(ids)
            else:
                titles = extract_titles_from_list(url)
                print(f"[INFO] Found titles (fallback): {len(titles)}")
                for title in titles:
                    imdb = search_imdb_id(title)
                    if imdb:
                        imdb_list.append(imdb)
                    time.sleep(0.1)

    imdb_list = list(set(imdb_list))

    # Series: expand each series into (series_id, season, episode) and fetch episode list from IMDb
    episode_jobs = []
    if series_list is not None:
        lines = series_list if isinstance(series_list, list) else series_list.strip().splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            print(f"[INFO] Fetching episodes for series: {line}")
            series_id = get_series_id(line)
            if not series_id:
                print("  [WARN] Invalid series ID/URL, skipping.")
                continue
            eps = get_all_episodes(line)
            if not eps:
                print("  [WARN] No episodes found, skipping.")
                continue
            for row in eps:
                episode_jobs.append((series_id, row["season"], row["episode"]))
            print(f"  [INFO] Found {len(eps)} episodes.")

    if not imdb_list and not episode_jobs:
        print("[ERROR] No input sources found!")
        print("[ERROR] Add IMDb list URL(s), Movies (IMDb IDs), and/or Series (IMDb IDs or URLs) in the UI.")
        TRAY_RUNNING = False
        TRAY_CURRENT_ITEM = ""
        return

    TRAY_RUNNING = True

    def process_streams(content_imdb_id, streams, season=None):
        """content_imdb_id: movie tt... or series tt...; season=None for movies."""
        candidates = {}
        pack_candidates = {}
        for s in streams:
            # Micro-sleep to yield CPU to foreground apps (makes app 'invisible')
            time.sleep(0.005)
            
            title = s.get("title", "")
            info_hash = s.get("infoHash")
            if not info_hash or has_attempted(info_hash) or is_blacklisted(title):
                continue
            seeders = extract_seeders(title)
            if seeders < config.get("min_seeders", 5):
                continue
            resolution = extract_resolution(title)
            if resolution < config.get("min_resolution", 720):
                continue
            if has_cached_quality(content_imdb_id, resolution, season):
                continue
            size = extract_size_mb(title)
            entry = {"title": title, "hash": info_hash, "seeders": seeders, "size": size}
            if is_large_pack(title):
                if season is not None:
                    seasons_in_title = extract_seasons_from_title(title)
                    if seasons_in_title and all(
                        has_cached_quality(content_imdb_id, resolution, s) for s in seasons_in_title
                    ):
                        continue
                pack_candidates.setdefault(resolution, []).append(entry)
            else:
                candidates.setdefault(resolution, []).append(entry)

        for resolution, items in sorted(candidates.items(), key=lambda x: -x[0]):
            if has_cached_quality(content_imdb_id, resolution, season):
                continue
            items.sort(key=lambda x: (-x["seeders"], x["size"]))
            added = 0
            for item in items:
                if STOP_REQUESTED:
                    return
                if added >= config.get("max_per_quality", 1):
                    break
                cached = is_cached(api_key, item["hash"])
                if cached is None:
                    continue
                if cached:
                    mark_attempted(item["hash"])
                    continue
                magnet = f"magnet:?xt=urn:btih:{item['hash']}"
                title_safe = (item["title"] or "").encode("ascii", "replace").decode("ascii")
                print(f"[INFO] Auto adding {resolution}p: {title_safe}")
                if add_magnet(api_key, magnet):
                    mark_attempted(item["hash"])
                    mark_cached_quality(content_imdb_id, resolution, season)
                    added += 1
        if config.get("allow_packs_fallback", True) and not candidates:
            for resolution, items in sorted(pack_candidates.items(), key=lambda x: -x[0]):
                if has_cached_quality(content_imdb_id, resolution, season):
                    continue
                items.sort(key=lambda x: (-x["seeders"], x["size"]))
                added = 0
                for item in items:
                    if STOP_REQUESTED or added >= config.get("max_per_quality", 1):
                        break
                    cached = is_cached(api_key, item["hash"])
                    if cached is None or cached:
                        if cached:
                            mark_attempted(item["hash"])
                        continue
                    title_safe = (item["title"] or "").encode("ascii", "replace").decode("ascii")
                    print(f"[INFO] Auto adding pack {resolution}p: {title_safe}")
                    if add_magnet(api_key, f"magnet:?xt=urn:btih:{item['hash']}"):
                        mark_attempted(item["hash"])
                        seasons_in_title = extract_seasons_from_title(item["title"] or "")
                        if seasons_in_title and season is not None:
                            for s in seasons_in_title:
                                mark_cached_quality(content_imdb_id, resolution, s)
                        else:
                            mark_cached_quality(content_imdb_id, resolution, season)
                        added += 1

    def run_one_pass():
        """Process all movies then all episodes once. Crash containment per item."""
        global TRAY_CURRENT_ITEM
        for imdb in imdb_list:
            if STOP_REQUESTED:
                return
            try:
                TRAY_CURRENT_ITEM = f"movie: {imdb}"
                print(f"\n[INFO] Processing movie: {imdb}")
                streams = get_movie_streams(imdb)[:50]
                print(f"[INFO] Found {len(streams)} streams (limit 50)")
                process_streams(imdb, streams, season=None)
                print("[INFO] Waiting before next item...\n")
                del streams
                gc.collect()
                time.sleep(config.get("delay_between_movies", 5))
            except Exception as e:
                print(f"[ERROR] Error processing movie {imdb}: {e}")
                continue

        for series_id, season, episode in episode_jobs:
            if STOP_REQUESTED:
                return
            try:
                TRAY_CURRENT_ITEM = f"S{season}E{episode}: {series_id}"
                print(f"\n[INFO] Processing series S{season}E{episode}: {series_id}")
                streams = get_episode_streams(series_id, season, episode)[:50]
                print(f"[INFO] Found {len(streams)} streams (limit 50)")
                process_streams(series_id, streams, season=season)
                print("[INFO] Waiting before next episode...\n")
                del streams
                gc.collect()
                time.sleep(config.get("delay_between_movies", 5))
            except Exception as e:
                print(f"[ERROR] Error processing S{season}E{episode} {series_id}: {e}")
                continue

    # ------------------------
    # Run mode
    # ------------------------
    try:
        if mode == "oneshot":
            run_one_pass()
            print("Run complete (one-shot).")
            return
        if mode == "loop":
            while not STOP_REQUESTED:
                run_one_pass()
                if STOP_REQUESTED:
                    break
                print("Loop: starting next pass...\n")
            print("Stopped.")
            return
        if mode == "interval":
            while not STOP_REQUESTED:
                run_one_pass()
                if STOP_REQUESTED:
                    break
                try:
                    mins = max(1, int(interval_mins))
                except (TypeError, ValueError):
                    mins = 60
                print(f"[INFO] Next run in {mins} minutes...\n")
                for _ in range(mins * 60):
                    if STOP_REQUESTED:
                        break
                    time.sleep(1)
            print("[INFO] Stopped.")
            return
        run_one_pass()
        print("[INFO] Run complete.")
    finally:
        TRAY_RUNNING = False
        TRAY_CURRENT_ITEM = ""


def request_stop():
    global STOP_REQUESTED
    STOP_REQUESTED = True
    print("[INFO] Stop requested.")
