"""长期记忆引擎模块"""
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent


class LongTermMemoryEngine:
    """长期记忆引擎 - 基于向量数据库的持久化记忆系统"""

    def __init__(self, context: Any, config_manager: Any, data_dir: str):
        self.context = context
        self.config_manager = config_manager
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.data_dir / "long_term_memory.db"
        self.vector_store: Any = None
        self._initialized = False

    async def initialize(self) -> bool:
        """初始化长期记忆引擎"""
        try:
            await self._init_database()
            await self._init_vector_store()
            self._initialized = True
            logger.info("长期记忆引擎初始化完成")
            return True
        except Exception as e:
            logger.error(f"长期记忆引擎初始化失败: {e}", exc_info=True)
            return False

    async def _init_database(self):
        """初始化SQLite数据库"""
        self.db = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                content TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                created_at REAL DEFAULT (strftime('%s', 'now')),
                last_accessed REAL DEFAULT (strftime('%s', 'now')),
                access_count INTEGER DEFAULT 0,
                decay_score REAL DEFAULT 1.0,
                metadata TEXT
            )
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_session ON memories(session_id)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at)
        """)
        self.db.commit()

    async def _init_vector_store(self):
        """初始化向量存储 - 使用简单文本搜索（无需 faiss）"""
        # 不再使用 faiss，避免版本冲突
        logger.info("使用简单文本向量存储")
        self.vector_store = SimpleVectorStore()
        await self.vector_store.initialize()

    async def add_memory(
        self,
        content: str,
        session_id: str,
        importance: float = 0.5,
        metadata: dict | None = None
    ) -> int:
        """添加长期记忆"""
        if not self._initialized:
            return -1
        
        cursor = self.db.cursor()
        cursor.execute(
            """INSERT INTO memories (session_id, content, importance, metadata)
               VALUES (?, ?, ?, ?)""",
            (session_id, content, importance, json.dumps(metadata or {}))
        )
        self.db.commit()
        memory_id = cursor.lastrowid
        
        # 添加到向量存储
        await self.vector_store.add(memory_id, content)
        
        logger.debug(f"添加长期记忆: ID={memory_id}")
        return memory_id

    async def search(self, query: str, k: int = 5) -> list[dict]:
        """搜索记忆"""
        if not self._initialized:
            return []
        
        # 获取候选记忆ID
        candidate_ids = await self.vector_store.search(query, k * 2)
        
        if not candidate_ids:
            # 如果没有向量结果，返回最近的记忆
            cursor = self.db.cursor()
            cursor.execute(
                """SELECT id, session_id, content, importance, created_at, access_count
                   FROM memories ORDER BY created_at DESC LIMIT ?""",
                (k,)
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "session_id": r[1],
                    "content": r[2],
                    "importance": r[3],
                    "created_at": r[4],
                    "score": r[5] / 10.0  # 模拟相似度
                }
                for r in rows
            ]
        
        # 获取记忆详情
        placeholders = ",".join("?" * len(candidate_ids))
        cursor = self.db.cursor()
        cursor.execute(
            f"""SELECT id, session_id, content, importance, created_at, access_count
                FROM memories WHERE id IN ({placeholders})""",
            candidate_ids
        )
        rows = cursor.fetchall()
        
        # 更新访问时间
        for mid in candidate_ids:
            cursor.execute(
                """UPDATE memories SET last_accessed = ?, access_count = access_count + 1
                   WHERE id = ?""",
                (time.time(), mid)
            )
        self.db.commit()
        
        return [
            {
                "id": r[0],
                "session_id": r[1],
                "content": r[2],
                "importance": r[3],
                "created_at": r[4],
                "score": 1.0 - (i * 0.1)  # 简化的相似度
            }
            for i, r in enumerate(rows[:k])
        ]

    async def delete_memory(self, memory_id: int) -> bool:
        """删除记忆"""
        if not self._initialized:
            return False
        
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.db.commit()
        
        await self.vector_store.delete(memory_id)
        
        return cursor.rowcount > 0

    async def get_memory(self, memory_id: int) -> dict | None:
        """获取单条记忆"""
        cursor = self.db.cursor()
        cursor.execute(
            """SELECT id, session_id, content, importance, created_at, metadata
               FROM memories WHERE id = ?""",
            (memory_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            "id": row[0],
            "session_id": row[1],
            "content": row[2],
            "importance": row[3],
            "created_at": row[4],
            "metadata": json.loads(row[5] or "{}")
        }

    async def get_all_memories(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """获取所有记忆"""
        cursor = self.db.cursor()
        cursor.execute(
            """SELECT id, session_id, content, importance, created_at, access_count
               FROM memories ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (limit, offset)
        )
        rows = cursor.fetchall()
        
        return [
            {
                "id": r[0],
                "session_id": r[1],
                "content": r[2],
                "importance": r[3],
                "created_at": r[4],
                "access_count": r[5]
            }
            for r in rows
        ]

    async def update_memory(self, memory_id: int, content: str) -> bool:
        """更新记忆内容"""
        cursor = self.db.cursor()
        cursor.execute(
            "UPDATE memories SET content = ? WHERE id = ?",
            (content, memory_id)
        )
        self.db.commit()
        
        if cursor.rowcount > 0:
            await self.vector_store.update(memory_id, content)
            return True
        return False

    async def get_memory_count(self) -> int:
        """获取记忆总数"""
        cursor = self.db.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories")
        return cursor.fetchone()[0]

    async def rebuild_index(self):
        """重建向量索引"""
        await self.vector_store.rebuild()

    async def apply_decay(self):
        """应用记忆衰减"""
        if not self._initialized:
            return
        
        decay_days = self.config_manager.memory_decay_days
        threshold = time.time() - (decay_days * 24 * 3600)
        
        cursor = self.db.cursor()
        cursor.execute(
            """UPDATE memories SET decay_score = decay_score * 0.95
               WHERE last_accessed < ?""",
            (threshold,)
        )
        self.db.commit()

    async def close(self):
        """关闭引擎"""
        if hasattr(self, 'db'):
            self.db.close()
        if self.vector_store:
            await self.vector_store.close()
        logger.info("长期记忆引擎已关闭")


class SimpleVectorStore:
    """简单的内存向量存储（无外部依赖）"""

    def __init__(self):
        self.store: dict[int, str] = {}

    async def initialize(self):
        pass

    async def add(self, memory_id: int, content: str):
        self.store[memory_id] = content

    async def search(self, query: str, k: int) -> list[int]:
        # 简单的文本匹配
        results = []
        query_lower = query.lower()
        for mid, content in self.store.items():
            if query_lower in content.lower():
                results.append(mid)
                if len(results) >= k:
                    break
        return results

    async def delete(self, memory_id: int):
        if memory_id in self.store:
            del self.store[memory_id]

    async def update(self, memory_id: int, content: str):
        self.store[memory_id] = content

    async def rebuild(self):
        pass

    async def close(self):
        pass
