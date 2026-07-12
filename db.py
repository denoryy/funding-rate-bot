import sqlite3
import threading
from contextlib import contextmanager

_lock = threading.Lock()


class Database:
    """Простая обёртка над SQLite для хранения уже отправленных новостей."""

    def __init__(self, path: str):
        self.path = path
        self._init_schema()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS seen_items (
                    item_id TEXT PRIMARY KEY,
                    exchange TEXT NOT NULL,
                    title TEXT,
                    url TEXT,
                    seen_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
                """
            )

    def is_seen(self, item_id: str) -> bool:
        with _lock, self._connect() as conn:
            cur = conn.execute(
                "SELECT 1 FROM seen_items WHERE item_id = ?", (item_id,)
            )
            return cur.fetchone() is not None

    def mark_seen(self, item_id: str, exchange: str, title: str, url: str):
        with _lock, self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO seen_items (item_id, exchange, title, url) "
                "VALUES (?, ?, ?, ?)",
                (item_id, exchange, title, url),
            )
