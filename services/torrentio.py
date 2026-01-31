import requests

BASE_URL = "https://torrentio.strem.fun"
CONFIG = "sort=qualitysize"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}


def get_movie_streams(imdb_id: str):
    url = f"{BASE_URL}/{CONFIG}/stream/movie/{imdb_id}.json"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("streams", [])
    except Exception as e:
        print("Torrentio error:", e)
        return []


def get_episode_streams(series_imdb_id: str, season: int, episode: int):
    """Get streams for one TV episode. Stremio uses series_id:season:episode."""
    video_id = f"{series_imdb_id}:{season}:{episode}"
    url = f"{BASE_URL}/{CONFIG}/stream/series/{video_id}.json"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("streams", [])
    except Exception as e:
        print("Torrentio series error:", e)
        return []
