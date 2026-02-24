"""短期记忆管理器模块"""
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


class ShortTermMemoryManager:
    """短期记忆管理器 - 基于会话的临时记忆系统"""

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.data_dir / "short_term_memory.db"
        self._lock = threading.RLock()
        self._init_database()
        
        # 内存中的会话缓存
        self._session_cache: dict[str, list[dict]] = {}

    def _init_database(self):
        """初始化数据库"""
        self.db = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS short_term_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL DEFAULT (strftime('%s', 'now'))
            )
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_short_session ON short_term_memories(session_id)
        """)
        self.db.commit()

    def add_message(self, session_id: str, role: str, content: str) -> int:
        """添加短期记忆消息"""
        with self._lock:
            cursor = self.db.cursor()
            cursor.execute(
                """INSERT INTO short_term_memories (session_id, role, content)
                   VALUES (?, ?, ?)""",
                (session_id, role, content)
            )
            self.db.commit()
            message_id = cursor.lastrowid
            
            # 更新内存缓存
            if session_id not in self._session_cache:
                self._session_cache[session_id] = []
            
            self._session_cache[session_id].append({
                "id": message_id,
                "role": role,
                "content": content,
                "timestamp": time.time()
            })
            
            # 限制缓存大小
            max_messages = 50
            if len(self._session_cache[session_id]) > max_messages:
                self._session_cache[session_id] = self._session_cache[session_id][-max_messages:]
            
            return message_id

    def get_session_messages(self, session_id: str, limit: int = 50) -> list[dict]:
        """获取会话消息"""
        # 先尝试从缓存获取
        if session_id in self._session_cache:
            return self._session_cache[session_id][-limit:]
        
        # 从数据库加载
        with self._lock:
            cursor = self.db.cursor()
            cursor.execute(
                """SELECT id, role, content, timestamp
                   FROM short_term_memories
                   WHERE session_id = ?
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                (session_id, limit)
            )
            rows = cursor.fetchall()
            
            messages = [
                {
                    "id": r[0],
                    "role": r[1],
                    "content": r[2],
                    "timestamp": r[3]
                }
                for r in reversed(rows)
            ]
            
            # 存入缓存
            self._session_cache[session_id] = messages
            
            return messages

    def get_session_context(self, session_id: str) -> list[dict]:
        """获取适合作为上下文的会话历史"""
        messages = self.get_session_messages(session_id)
        
        # 转换为 role/content 格式
        return [
            {"role": m["role"], "content": m["content"]}
            for m in messages
        ]

    def delete_memory(self, memory_id: int) -> bool:
        """删除指定记忆"""
        with self._lock:
            cursor = self.db.cursor()
            cursor.execute("DELETE FROM short_term_memories WHERE id = ?", (memory_id,))
            self.db.commit()
            
            # 从缓存中移除
            for session_id, messages in self._session_cache.items():
                self._session_cache[session_id] = [
                    m for m in messages if m["id"] != memory_id
                ]
            
            return cursor.rowcount > 0

    def clear_session(self, session_id: str):
        """清除会话记忆"""
        with self._lock:
            cursor = self.db.cursor()
            cursor.execute("DELETE FROM short_term_memories WHERE session_id = ?", (session_id,))
            self.db.commit()
            
            # 清除缓存
            if session_id in self._session_cache:
                del self._session_cache[session_id]

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            cursor = self.db.cursor()
            
            # 会话数
            cursor.execute("SELECT COUNT(DISTINCT session_id) FROM short_term_memories")
            session_count = cursor.fetchone()[0]
            
            # 消息总数
            cursor.execute("SELECT COUNT(*) FROM short_term_memories")
            message_count = cursor.fetchone()[0]
            
            return {
                "session_count": session_count,
                "message_count": message_count
            }

    def get_all_sessions(self) -> list[dict]:
        """获取所有会话"""
        with self._lock:
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT session_id, COUNT(*) as msg_count, 
                       MIN(timestamp) as first_msg, MAX(timestamp) as last_msg
                FROM short_term_memories
                GROUP BY session_id
                ORDER BY last_msg DESC
            """)
            rows = cursor.fetchall()
            
            return [
                {
                    "session_id": r[0],
                    "message_count": r[1],
                    "first_message": r[2],
                    "last_message": r[3]
                }
                for r in rows
            ]

    def update_memory(self, memory_id: int, content: str) -> bool:
        """更新记忆内容"""
        with self._lock:
            cursor = self.db.cursor()
            cursor.execute(
                "UPDATE short_term_memories SET content = ? WHERE id = ?",
                (content, memory_id)
            )
            self.db.commit()
            
            # 更新缓存
            for session_id, messages in self._session_cache.items():
                for m in messages:
                    if m["id"] == memory_id:
                        m["content"] = content
                        return True
            
            return cursor.rowcount > 0

    def search_in_session(self, session_id: str, query: str) -> list[dict]:
        """在会话中搜索"""
        messages = self.get_session_messages(session_id)
        query_lower = query.lower()
        
        return [
            m for m in messages
            if query_lower in m.get("content", "").lower()
        ]

    def close(self):
        """关闭数据库连接"""
        with self._lock:
            if hasattr(self, 'db'):
                self.db.close()
