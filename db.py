import sqlite3
from datetime import datetime, timedelta

DB_PATH = "trends.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS trends (
                   id INTEGER PRIMARY KEY,
                   platform TEXT,
                   tag TEXT,
                   scraped_at DATETIME
                 )""")
    conn.commit()
    conn.close()

def get_cached(platform):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cutoff = datetime.utcnow() - timedelta(hours=1)
    c.execute("SELECT tag FROM trends WHERE platform=? AND scraped_at>?", (platform, cutoff))
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows

def cache_tags(platform, tags):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow()
    for tag in tags:
        c.execute("INSERT INTO trends(platform, tag, scraped_at) VALUES (?, ?, ?)",
                  (platform, tag, now))
    conn.commit()
    conn.close()
