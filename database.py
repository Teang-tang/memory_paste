"""
剪贴板记忆管理器 - 数据库层
使用 SQLite 存储剪贴板历史记录
"""

import sqlite3
import os
import sys
import time
from datetime import datetime, timedelta
from config import DB_FILE, MAX_HISTORY, RETENTION_DAYS, TYPE_TEXT, TYPE_IMAGE, TYPE_FILE


def _get_app_dir() -> str:
    """
    获取持久化数据目录。
    - exe 模式：exe 所在目录
    - 脚本模式：脚本所在目录
    确保数据不会因为 PyInstaller 的临时解压而丢失。
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的 exe → 用 exe 所在目录
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        # 开发模式 → 用脚本所在目录
        return os.path.dirname(os.path.abspath(__file__))


class Database:
    """剪贴板历史数据库管理"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(_get_app_dir(), DB_FILE)
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据库表"""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clipboard_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_type TEXT NOT NULL,
                    content TEXT DEFAULT '',
                    image_path TEXT DEFAULT '',
                    created_at REAL NOT NULL,
                    pinned INTEGER DEFAULT 0,
                    size_bytes INTEGER DEFAULT 0
                )
            """)
            # 为 created_at 创建索引以加速时间排序
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON clipboard_history(created_at DESC)
            """)
            conn.commit()

    def add_record(self, content_type: str, content: str = "",
                   image_path: str = "", size_bytes: int = 0) -> int:
        """
        添加一条剪贴板记录
        返回新记录的 id
        """
        # 如果是文字，去重：与最近一条文字内容相同则跳过
        if content_type == TYPE_TEXT and content:
            last = self.get_latest_text()
            if last and last["content"] == content:
                # 更新时间戳
                self._update_timestamp(last["id"])
                return last["id"]

        with self._get_conn() as conn:
            cursor = conn.execute(
                """INSERT INTO clipboard_history
                   (content_type, content, image_path, created_at, size_bytes)
                   VALUES (?, ?, ?, ?, ?)""",
                (content_type, content, image_path, time.time(), size_bytes)
            )
            conn.commit()
            record_id = cursor.lastrowid

        # 清理超量记录
        self._enforce_limits()
        return record_id

    def _update_timestamp(self, record_id: int):
        """更新记录的时间戳（用于去重时刷新已有记录）"""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE clipboard_history SET created_at = ? WHERE id = ?",
                (time.time(), record_id)
            )
            conn.commit()

    def get_latest_text(self) -> dict | None:
        """获取最近一条文字记录"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM clipboard_history WHERE content_type = ? "
                "ORDER BY created_at DESC LIMIT 1",
                (TYPE_TEXT,)
            ).fetchone()
        return dict(row) if row else None

    def get_all_records(self, search: str = "") -> list[dict]:
        """获取所有记录，按时间降序，置顶优先"""
        where = ""
        params = []
        if search:
            where = "WHERE (content LIKE ? OR image_path LIKE ?)"
            params = [f"%{search}%", f"%{search}%"]

        sql = f"""
            SELECT * FROM clipboard_history
            {where}
            ORDER BY pinned DESC, created_at DESC
        """

        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def toggle_pin(self, record_id: int) -> bool:
        """切换置顶状态，返回新状态"""
        with self._get_conn() as conn:
            current = conn.execute(
                "SELECT pinned FROM clipboard_history WHERE id = ?",
                (record_id,)
            ).fetchone()
            if current is None:
                return False
            new_val = 0 if current["pinned"] else 1
            conn.execute(
                "UPDATE clipboard_history SET pinned = ? WHERE id = ?",
                (new_val, record_id)
            )
            conn.commit()
            return bool(new_val)

    def delete_record(self, record_id: int):
        """删除一条记录（图片则同时删除文件）"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT image_path FROM clipboard_history WHERE id = ?",
                (record_id,)
            ).fetchone()
            conn.execute("DELETE FROM clipboard_history WHERE id = ?", (record_id,))
            conn.commit()

        # 删除关联的图片文件
        if row and row["image_path"] and os.path.exists(row["image_path"]):
            try:
                os.remove(row["image_path"])
            except OSError:
                pass

    def clear_all(self):
        """清空所有记录"""
        with self._get_conn() as conn:
            # 删除所有图片文件
            rows = conn.execute(
                "SELECT image_path FROM clipboard_history "
                "WHERE image_path != ''"
            ).fetchall()
            for r in rows:
                if os.path.exists(r["image_path"]):
                    try:
                        os.remove(r["image_path"])
                    except OSError:
                        pass
            conn.execute("DELETE FROM clipboard_history")
            conn.commit()

    def _enforce_limits(self):
        """执行数量和时间限制"""
        with self._get_conn() as conn:
            # 删除超过保留天数的记录
            cutoff = time.time() - RETENTION_DAYS * 86400
            old_rows = conn.execute(
                "SELECT id, image_path FROM clipboard_history "
                "WHERE created_at < ? AND pinned = 0",
                (cutoff,)
            ).fetchall()
            for r in old_rows:
                if r["image_path"] and os.path.exists(r["image_path"]):
                    try:
                        os.remove(r["image_path"])
                    except OSError:
                        pass
            conn.execute(
                "DELETE FROM clipboard_history WHERE created_at < ? AND pinned = 0",
                (cutoff,)
            )

            # 超过数量上限则删除最旧的非置顶记录
            count = conn.execute("SELECT COUNT(*) FROM clipboard_history").fetchone()[0]
            if count > MAX_HISTORY:
                excess = count - MAX_HISTORY
                old_rows = conn.execute(
                    "SELECT id, image_path FROM clipboard_history "
                    "WHERE pinned = 0 ORDER BY created_at ASC LIMIT ?",
                    (excess,)
                ).fetchall()
                for r in old_rows:
                    if r["image_path"] and os.path.exists(r["image_path"]):
                        try:
                            os.remove(r["image_path"])
                        except OSError:
                            pass
                conn.execute(
                    "DELETE FROM clipboard_history WHERE id IN ("
                    "SELECT id FROM clipboard_history "
                    "WHERE pinned = 0 ORDER BY created_at ASC LIMIT ?)",
                    (excess,)
                )
            conn.commit()

    def close(self):
        """关闭数据库（SQLite 连接由上下文管理器自动管理，此方法保留备用）"""
        pass


def format_relative_time(timestamp: float) -> str:
    """将时间戳格式化为相对时间（如"3分钟前"、"1小时前"）"""
    now = time.time()
    diff = now - timestamp

    if diff < 60:
        return "刚刚"
    elif diff < 3600:
        mins = int(diff / 60)
        return f"{mins}分钟前"
    elif diff < 86400:
        hours = int(diff / 3600)
        return f"{hours}小时前"
    elif diff < 604800:
        days = int(diff / 86400)
        return f"{days}天前"
    else:
        return datetime.fromtimestamp(timestamp).strftime("%m-%d %H:%M")
