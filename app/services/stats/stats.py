import sqlite3
from pathlib import Path

DB_PATH = Path("stats.db")

def get_wireguard_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT public_key, total_rx, total_tx, last_seen FROM peer_totals")
    rows = c.fetchall()
    conn.close()

    return [
        {
            "public_key": r[0],
            "total_rx": r[1],
            "total_tx": r[2],
            "last_seen": r[3]
        }
        for r in rows
    ]


def get_peer_stats(public_key: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT total_rx, total_tx, last_seen FROM peer_totals WHERE public_key=?", (public_key,))
    row = c.fetchone()
    conn.close()

    if not row:
        return {"error": "peer not found"}

    return {
        "public_key": public_key,
        "total_rx": row[0],
        "total_tx": row[1],
        "last_seen": row[2]
    }
