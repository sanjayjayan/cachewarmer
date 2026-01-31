import re
import requests
from bs4 import BeautifulSoup

# Browser-like User-Agent so IMDb returns full HTML (not a minimal JS shell)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def extract_imdb_ids_from_list(url: str):
    """Extract IMDb IDs (tt...) directly from a list page. Most reliable method."""
    try:
        r = requests.get(url.strip(), headers=HEADERS, timeout=20)
        r.raise_for_status()
        html = r.text
        # Match /title/tt1234567/ or /title/tt1234567? in the page
        ids = re.findall(r"/title/(tt\d+)(?:/|\?)", html)
        # Preserve order, remove duplicates
        seen = set()
        unique = []
        for i in ids:
            if i not in seen:
                seen.add(i)
                unique.append(i)
        return unique
    except Exception as e:
        print("IMDb list ID parse error:", e)
        return []


def extract_titles_from_list(url: str):
    """Extract movie titles from list page (fallback when IDs not used)."""
    try:
        r = requests.get(url.strip(), headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        titles = []

        # Method 1: List item title anchors
        for a in soup.select("a[href^='/title/tt']"):
            text = a.get_text(strip=True)
            if text and len(text) < 120:
                titles.append(text)

        # Method 2: Fallback - h3 tags
        if not titles:
            for h3 in soup.find_all("h3"):
                text = h3.get_text(strip=True)
                if text and len(text) < 120:
                    titles.append(text)

        # Clean duplicates
        clean = []
        for t in titles:
            if t not in clean:
                clean.append(t)

        return clean

    except Exception as e:
        print("IMDb title parse error:", e)
        return []
