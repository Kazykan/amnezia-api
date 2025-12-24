import sqlite3
from pathlib import Path

DB_PATH = Path("stats.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS peer_totals (
            public_key TEXT PRIMARY KEY,
            total_rx INTEGER,
            total_tx INTEGER,
            last_rx INTEGER,
            last_tx INTEGER,
            last_seen INTEGER
        )
    """)

    conn.commit()
    conn.close()


def save_stats(timestamp, peers):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for p in peers:
        pk = p["public_key"]
        rx = p["rx_bytes"]
        tx = p["tx_bytes"]
        handshake = p["latest_handshake"]

        c.execute("SELECT last_rx, last_tx, total_rx, total_tx, last_seen FROM peer_totals WHERE public_key=?", (pk,))
        row = c.fetchone()

        if row:
            last_rx, last_tx, total_rx, total_tx, last_seen = row

            # обработка перезапуска контейнера
            delta_rx = rx if rx < last_rx else rx - last_rx
            delta_tx = tx if tx < last_tx else tx - last_tx

            total_rx += delta_rx
            total_tx += delta_tx

            # обновляем last_seen только если handshake > 0
            if handshake > 0:
                last_seen = handshake

            c.execute("""
                UPDATE peer_totals
                SET total_rx=?, total_tx=?, last_rx=?, last_tx=?, last_seen=?
                WHERE public_key=?
            """, (total_rx, total_tx, rx, tx, last_seen, pk))

        else:
            # первая запись
            last_seen = handshake if handshake > 0 else None

            c.execute("""
                INSERT INTO peer_totals (public_key, total_rx, total_tx, last_rx, last_tx, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (pk, 0, 0, rx, tx, last_seen))

    conn.commit()
    conn.close()
