import sqlite3
from datetime import datetime, timedelta

DB_PATH = "trends.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS trends (
                        id INTEGER PRIMARY KEY,
                        platform TEXT,
                        tag TEXT,
                        scraped_at DATETIME
                    )""")
    conn.commit()
    conn.close()

def get_cached(platform, max_age_hours=1):
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT tag FROM trends WHERE platform=? AND scraped_at>?",
                (platform, cutoff))
    tags = [r[0] for r in cur.fetchall()]
    conn.close()
    return tags

def cache_tags(platform, tags):
    now = datetime.utcnow()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for tag in tags:
        cur.execute("INSERT INTO trends(platform, tag, scraped_at) VALUES (?, ?, ?)",
                    (platform, tag, now))
    conn.commit()
    conn.close()
