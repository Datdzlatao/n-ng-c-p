import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.db.supabase_client import get_supabase_client

logger = logging.getLogger("smart_manager.repo.chat_history")

# Local SQLite fallback file
_LOCAL_DB_PATH = Path(__file__).resolve().parent.parent / "chat_history_local.db"


def _init_local_db():
    try:
        conn = sqlite3.connect(str(_LOCAL_DB_PATH))
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                pen_id TEXT,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_calls TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            );
            """
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error initializing local chat SQLite: {e}")


_init_local_db()


class ChatHistoryRepository:
    """
    Repository for managing chat history.
    Prioritizes Supabase `chat_messages` table.
    Falls back gracefully to local SQLite if table is not yet migrated in Supabase.
    """

    def __init__(self):
        self._table = "chat_messages"
        self._supabase_available = True

    @property
    def client(self):
        return get_supabase_client()

    def save_message(
        self,
        user_id: str,
        sender: str,
        content: str,
        pen_id: Optional[str] = None,
        tool_calls: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Save a chat message."""
        now_str = datetime.now(timezone.utc).isoformat()
        item = {
            "user_id": str(user_id).strip(),
            "pen_id": str(pen_id).strip() if pen_id else None,
            "sender": sender.strip(),
            "content": content.strip(),
            "tool_calls": tool_calls or [],
            "created_at": now_str,
        }

        if self._supabase_available:
            try:
                res = self.client.table(self._table).insert(item).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception as e:
                # If table doesn't exist, switch to local SQLite
                logger.warning(f"Supabase chat insert error: {e}. Saving to local SQLite.")
                self._supabase_available = False

        # Fallback to local SQLite
        try:
            conn = sqlite3.connect(str(_LOCAL_DB_PATH))
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO chat_messages (user_id, pen_id, sender, content, tool_calls, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    item["user_id"],
                    item["pen_id"],
                    item["sender"],
                    item["content"],
                    json.dumps(item["tool_calls"]),
                    item["created_at"],
                ),
            )
            item["id"] = cursor.lastrowid
            conn.commit()
            conn.close()
            return item
        except Exception as e:
            logger.error(f"Local SQLite insert error: {e}")
            item["id"] = int(datetime.now().timestamp() * 1000)
            return item

    def get_history(
        self,
        user_id: str,
        pen_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Retrieve recent chat history for a user, optionally filtered by pen_id."""
        clean_user = str(user_id).strip()
        clean_pen = str(pen_id).strip() if pen_id else None

        if self._supabase_available:
            try:
                query = (
                    self.client.table(self._table)
                    .select("*")
                    .eq("user_id", clean_user)
                )
                if clean_pen:
                    query = query.eq("pen_id", clean_pen)

                res = query.order("created_at", desc=False).limit(limit).execute()
                if res.data is not None:
                    return res.data
            except Exception as e:
                logger.warning(f"Supabase chat query error: {e}. Querying local SQLite.")
                self._supabase_available = False

        # Local SQLite fallback
        try:
            conn = sqlite3.connect(str(_LOCAL_DB_PATH))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if clean_pen:
                cursor.execute(
                    """
                    SELECT * FROM chat_messages
                    WHERE user_id = ? AND pen_id = ?
                    ORDER BY id ASC LIMIT ?
                    """,
                    (clean_user, clean_pen, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM chat_messages
                    WHERE user_id = ?
                    ORDER BY id ASC LIMIT ?
                    """,
                    (clean_user, limit),
                )
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                if isinstance(item.get("tool_calls"), str):
                    try:
                        item["tool_calls"] = json.loads(item["tool_calls"])
                    except Exception:
                        item["tool_calls"] = []
                results.append(item)
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Local SQLite query error: {e}")
            return []
