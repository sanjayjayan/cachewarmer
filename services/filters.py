import re


def extract_seeders(title: str) -> int:
    match = re.search(r"👤\s*(\d+)", title)
    if match:
        return int(match.group(1))
    return 0


def is_blacklisted(title: str) -> bool:
    bad = ["cam", "ts", "telesync", "hdcam"]
    t = title.lower()
    return any(word in t for word in bad)

def extract_resolution(title: str) -> int:
    t = title.lower()

    # Strong SD indicators → force low
    sd_words = ["dvd", "xvid", "divx", "camrip", "dvdrip"]
    if any(w in t for w in sd_words):
        return 480

    # 4K / UHD
    if "2160p" in t or "4k" in t or "uhd" in t or "3840x2160" in t:
        return 2160

    # 1080p
    if "1080p" in t or "1080 px" in t or "1920x1080" in t:
        return 1080

    # 720p
    if "720p" in t or "1280x720" in t:
        return 720

    return 0


def extract_size_mb(title: str) -> float:
    import re

    match = re.search(r"💾\s*([\d.]+)\s*(GB|MB)", title)
    if not match:
        return 0

    size = float(match.group(1))
    unit = match.group(2)

    if unit == "GB":
        return size * 1024
    return size

def extract_seasons_from_title(title: str) -> list:
    """
    Extract season numbers from a title. Recognizes:
    S01, S1, Season 1, Complete Season 1 -> [1]
    S01-S03, S1-S3, Season 1-3, Season 1 - 3 -> [1, 2, 3]
    Returns sorted unique list of ints; empty list if no pattern matched.
    """
    if not title or not isinstance(title, str):
        return []
    t = title
    out = set()
    # S01-S03, S1-S3, S01 - S03
    range_m = re.search(r"\bS(\d{1,2})\s*-\s*S?(\d{1,2})\b", t, re.I)
    if range_m:
        lo, hi = int(range_m.group(1)), int(range_m.group(2))
        for n in range(min(lo, hi), max(lo, hi) + 1):
            out.add(n)
    # Season 1-3, Season 1 - 3, Season 1 – 3
    range_m2 = re.search(r"\bSeason\s+(\d{1,2})\s*[-–]\s*(\d{1,2})\b", t, re.I)
    if range_m2:
        lo, hi = int(range_m2.group(1)), int(range_m2.group(2))
        for n in range(min(lo, hi), max(lo, hi) + 1):
            out.add(n)
    # Single: S01, S1, Season 1, Complete Season 1
    single_s = re.findall(r"\bS(\d{1,2})\b", t, re.I)
    for g in single_s:
        out.add(int(g))
    single_season = re.findall(r"(?:Complete\s+)?Season\s+(\d{1,2})\b", t, re.I)
    for g in single_season:
        out.add(int(g))
    return sorted(out) if out else []


def is_large_pack(title: str) -> bool:
    t = title.lower()

    bad_signals = [
        "500 movies",
        "200 movies",
        "100 movies",
        "complete movies",
        "movie pack",
        "mega pack",
        "collection",
        "trilogy",
        "quadrilogy",
        "pack",
        "great films",
        "essential films",
        "classic films",
        "movies part",
        "part 1 of",
        "part 2 of",
        "m1 ",
        " m2 ",
        " m3 "
    ]

    return any(b in t for b in bad_signals)




