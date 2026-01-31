import sqlite3

DB_FILE = "cachewarmer.db"


def get_connection():
    return sqlite3.connect(DB_FILE)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS attempted_hashes (
            info_hash TEXT PRIMARY KEY
        )
    """)

    # Logical dedup: (imdb_id, resolution) for movies; (imdb_id, resolution, season) for series
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cached_quality (
            imdb_id TEXT NOT NULL,
            resolution INTEGER NOT NULL,
            season INTEGER,
            PRIMARY KEY (imdb_id, resolution, season)
        )
    """)

    # Indexes for performance
    cur.execute("CREATE INDEX IF NOT EXISTS idx_attempted_hash ON attempted_hashes(info_hash)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cached_quality ON cached_quality(imdb_id, resolution, season)")

    conn.commit()
    conn.close()


def has_attempted(info_hash: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT 1 FROM attempted_hashes WHERE info_hash=?",
        (info_hash,)
    )

    result = cur.fetchone()
    conn.close()

    return result is not None


def mark_attempted(info_hash: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO attempted_hashes VALUES (?)",
        (info_hash,)
    )

    conn.commit()
    conn.close()


def has_cached_quality(imdb_id: str, resolution: int, season=None) -> bool:
    """True if we already cached this imdb_id at this resolution (season=None for movies)."""
    conn = get_connection()
    cur = conn.cursor()
    if season is None:
        cur.execute(
            "SELECT 1 FROM cached_quality WHERE imdb_id=? AND resolution=? AND season IS NULL",
            (imdb_id, resolution),
        )
    else:
        cur.execute(
            "SELECT 1 FROM cached_quality WHERE imdb_id=? AND resolution=? AND season=?",
            (imdb_id, resolution, season),
        )
    result = cur.fetchone()
    conn.close()
    return result is not None


def mark_cached_quality(imdb_id: str, resolution: int, season=None):
    """Record that we cached this imdb_id at this resolution (season=None for movies)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO cached_quality (imdb_id, resolution, season) VALUES (?, ?, ?)",
        (imdb_id, resolution, season),
    )
    conn.commit()
    conn.close()
