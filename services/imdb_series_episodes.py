"""
Fetch all episode IDs for an IMDb TV series by scraping the series episode pages.
No TSV/dataset files required.
"""
import re
import requests
import time
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def get_series_id(series_input: str) -> str | None:
    """Get series tt... from URL or raw ID. Use this for Torrentio series:season:episode."""
    s = (series_input or "").strip()
    if not s:
        return None
    m = re.search(r"(tt\d{7,})", s, re.I)
    return m.group(1).lower() if m else None


def _extract_series_id(series_input: str) -> str | None:
    return get_series_id(series_input)


def _get_season_numbers(series_id: str) -> list[int]:
    """Fetch main episodes page and parse season links (e.g. ?season=1)."""
    url = f"https://www.imdb.com/title/{series_id}/episodes"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        # Links like /title/tt0944947/episodes?season=1
        seasons = re.findall(r"[?&]season=(\d+)", r.text)
        nums = sorted(set(int(x) for x in seasons if x.isdigit()))
        return nums if nums else [1]  # default to season 1 if none found
    except Exception:
        return [1]


def _parse_episodes_from_season_page(html: str) -> list[dict]:
    """Parse one season page: (season, episode, episode_id)."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    # Episode links have ref_=ttep_ep in href; link text often "S1.E1 ∙ Title"
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if "ttep_ep" not in href:
            continue
        m = re.search(r"/title/(tt\d+)(?:/|\?)", href)
        if not m:
            continue
        ep_id = m.group(1).lower()
        text = a.get_text(strip=True) or ""
        se = re.search(r"S(\d{1,2})\.E(\d{1,3})\b", text, re.I)
        if not se:
            continue
        season_num = int(se.group(1))
        ep_num = int(se.group(2))
        out.append({"season": season_num, "episode": ep_num, "episode_id": ep_id})
    return out


def get_all_episodes(series_input: str) -> list[dict]:
    """
    Get all episodes for a series. Returns list of
    { "season": int, "episode": int, "episode_id": "tt..." }.
    series_input: IMDb series ID (tt0944947) or full series URL.
    """
    series_id = _extract_series_id(series_input)
    if not series_id:
        return []

    seasons = _get_season_numbers(series_id)
    all_eps = []
    seen = set()

    for season in seasons:
        time.sleep(1.0) # Be polite to IMDb and save CPU
        url = f"https://www.imdb.com/title/{series_id}/episodes?season={season}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            for row in _parse_episodes_from_season_page(r.text):
                key = (row["season"], row["episode"], row["episode_id"])
                if key not in seen:
                    seen.add(key)
                    all_eps.append(row)
        except Exception as e:
            print("IMDb series page error:", e)
            continue

    all_eps.sort(key=lambda x: (x["season"], x["episode"]))
    return all_eps


