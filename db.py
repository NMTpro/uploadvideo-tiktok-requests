import sqlite3
from sqlite3 import Connection, Cursor
from typing import Optional, List
from datetime import datetime, timedelta

class SessionDB:
    """Quản lý kết nối và thao tác với database sessions.db"""
    def __init__(self, db_path: str = 'sessions.db'):
        self.db_path = db_path
        self.conn: Optional[Connection] = None
        self._connect()
        self._ensure_table()

    def _connect(self):
        """Mở kết nối đến database."""
        self.conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.row_factory = sqlite3.Row

    def _ensure_table(self):
        """Tạo bảng sessions nếu chưa tồn tại."""
        sql = """
        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    NOT NULL,
            user_id     TEXT    NOT NULL UNIQUE,
            sessionid   TEXT    NOT NULL,
            timestamp   TEXT    NOT NULL
        );
        """
        self.execute(sql)

    def execute(self, sql: str, params: tuple = ()) -> Cursor:
        """Thực thi một câu lệnh SQL (INSERT/UPDATE/DELETE)."""
        if not self.conn:
            raise RuntimeError("Database not connected")
        cur = self.conn.cursor()
        cur.execute(sql, params)
        self.conn.commit()
        return cur

    def insert_session(self, sessionid: str, username: str, user_id: str) -> int:
        """Chèn hoặc cập nhật session với timestamp theo giờ Việt Nam."""
        # Tính giờ hiện tại UTC+7 (giờ Việt Nam)
        now = (datetime.utcnow() + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")

        cur = self.conn.cursor()
        cur.execute("SELECT id FROM sessions WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            # Cập nhật bản ghi cũ
            self.execute(
                "UPDATE sessions SET username = ?, sessionid = ?, timestamp = ? WHERE user_id = ?",
                (username, sessionid, now, user_id)
            )
            return row[0]
        else:
            # Chèn bản ghi mới
            cur = self.execute(
                "INSERT INTO sessions (username, user_id, sessionid, timestamp) VALUES (?, ?, ?, ?)",
                (username, user_id, sessionid, now)
            )
            return cur.lastrowid

    def fetch_all(self) -> List[sqlite3.Row]:
        """Lấy toàn bộ bản ghi trong bảng sessions."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM sessions ORDER BY timestamp DESC")
        return cur.fetchall()

    def close(self):
        """Đóng kết nối."""
        if self.conn:
            self.conn.close()
            self.conn = None