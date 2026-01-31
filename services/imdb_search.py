import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def search_imdb_id(title: str):
    try:
        url = f"https://www.imdb.com/find?q={requests.utils.quote(title)}&s=all"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")

        # IMDb search result rows
        results = soup.select("section[data-testid='find-results-section-title'] li")

        for item in results:
            link = item.find("a", href=True)
            if not link:
                continue

            href = link["href"]

            if "/title/" in href:
                match = re.search(r"/title/(tt\d+)", href)
                if match:
                    return match.group(1)

    except Exception:
        pass

    return None
