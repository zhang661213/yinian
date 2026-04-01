"""
Yinian 本地缓存
"""
import hashlib
import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

from loguru import logger

from yinian.core.config import get_config


@dataclass
class CacheEntry:
    """缓存条目"""
    id: int = 0
    question_hash: str = ""
    question: str = ""
    model: str = ""
    response: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    created_at: str = ""
    expires_at: str = ""
    hit_count: int = 0
    _ttl_hours: int = 24  # 内部字段，不存入 DB
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.expires_at:
            # 不再调用 get_config()，使用缓存的 ttl 或默认值 24
            ttl = getattr(self, '_ttl_hours', 24)
            expires = datetime.now() + timedelta(hours=ttl)
            self.expires_at = expires.isoformat()
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        try:
            expires = datetime.fromisoformat(self.expires_at)
            return datetime.now() > expires
        except:
            return True
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "CacheEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class CacheDB:
    """缓存数据库"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_hash TEXT UNIQUE NOT NULL,
                    question TEXT NOT NULL,
                    model TEXT NOT NULL,
                    response TEXT NOT NULL,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    cost REAL DEFAULT 0.0,
                    latency_ms REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    hit_count INTEGER DEFAULT 0
                )
            """)
            
            # 索引
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_question_hash ON cache(question_hash)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)
            """)
    
    def _compute_hash(self, question: str, model: str) -> str:
        """计算问题哈希"""
        # 包含 model 因为不同模型的结果不同
        content = f"{question}:{model}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, question: str, model: str) -> Optional[CacheEntry]:
        """获取缓存"""
        question_hash = self._compute_hash(question, model)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM cache WHERE question_hash = ?
            """, (question_hash,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            entry = CacheEntry(
                id=row["id"],
                question_hash=row["question_hash"],
                question=row["question"],
                model=row["model"],
                response=row["response"],
                input_tokens=row["input_tokens"],
                output_tokens=row["output_tokens"],
                cost=row["cost"],
                latency_ms=row["latency_ms"],
                created_at=row["created_at"],
                expires_at=row["expires_at"],
                hit_count=row["hit_count"],
            )
            
            # 检查是否过期
            if entry.is_expired():
                self.delete(question_hash)
                return None
            
            # 增加命中计数
            conn.execute("""
                UPDATE cache SET hit_count = hit_count + 1 WHERE id = ?
            """, (entry.id,))
            
            return entry
    
    def set(self, entry: CacheEntry) -> bool:
        """设置缓存"""
        try:
            question_hash = self._compute_hash(entry.question, entry.model)
            entry.question_hash = question_hash
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cache 
                    (question_hash, question, model, response, input_tokens, 
                     output_tokens, cost, latency_ms, created_at, expires_at, hit_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.question_hash,
                    entry.question[:500],  # 限制问题长度
                    entry.model,
                    entry.response[:10000],  # 限制响应长度
                    entry.input_tokens,
                    entry.output_tokens,
                    entry.cost,
                    entry.latency_ms,
                    entry.created_at,
                    entry.expires_at,
                    entry.hit_count,
                ))
            
            logger.debug(f"缓存已保存: {question_hash[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"缓存保存失败: {e}")
            return False
    
    def delete(self, question_hash: str) -> bool:
        """删除缓存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache WHERE question_hash = ?", (question_hash,))
            return True
        except Exception as e:
            logger.error(f"缓存删除失败: {e}")
            return False
    
    def clear_expired(self) -> int:
        """清理过期缓存"""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM cache WHERE expires_at < ?
            """, (now,))
            
            count = cursor.rowcount
            if count > 0:
                logger.info(f"已清理 {count} 条过期缓存")
            
            return count
    
    def clear_all(self) -> int:
        """清空所有缓存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM cache")
            count = cursor.fetchone()[0]
            
            conn.execute("DELETE FROM cache")
            
            logger.info(f"已清空 {count} 条缓存")
            return count
    
    def get_stats(self) -> dict:
        """获取缓存统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_count,
                    SUM(hit_count) as total_hits,
                    SUM(cost) as total_saved,
                    AVG(cost) as avg_cost
                FROM cache
            """)
            
            row = cursor.fetchone()
            
            cursor2 = conn.execute("""
                SELECT COUNT(*) as expired_count
                FROM cache
                WHERE expires_at < ?
            """, (datetime.now().isoformat(),))
            
            expired = cursor2.fetchone()[0]
            
            return {
                "total_count": row[0] or 0,
                "total_hits": row[1] or 0,
                "total_saved": row[2] or 0.0,
                "avg_cost": row[3] or 0.0,
                "expired_count": expired,
            }
    
    def get_recent(self, limit: int = 10) -> List[CacheEntry]:
        """获取最近缓存"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM cache 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            
            return [
                CacheEntry(
                    id=row["id"],
                    question_hash=row["question_hash"],
                    question=row["question"],
                    model=row["model"],
                    response=row["response"],
                    input_tokens=row["input_tokens"],
                    output_tokens=row["output_tokens"],
                    cost=row["cost"],
                    latency_ms=row["latency_ms"],
                    created_at=row["created_at"],
                    expires_at=row["expires_at"],
                    hit_count=row["hit_count"],
                )
                for row in cursor.fetchall()
            ]


class Cache:
    """缓存管理器"""
    
    def __init__(self):
        self.config = get_config()
        self.db_path = self.config.cache_dir / "cache.db"
        self.db = CacheDB(self.db_path)
        self._enabled = self.config.get("cache.enabled", True)
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        self.config.set("cache.enabled", value)
    
    def get(self, question: str, model: str) -> Optional[CacheEntry]:
        """获取缓存"""
        if not self.enabled:
            return None
        
        entry = self.db.get(question, model)
        
        if entry:
            logger.debug(f"缓存命中: {question[:50]}... ({entry.model})")
        
        return entry
    
    def set(
        self,
        question: str,
        model: str,
        response: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
        latency_ms: float = 0.0,
    ) -> bool:
        """设置缓存"""
        if not self.enabled:
            return False
        
        entry = CacheEntry(
            question=question,
            model=model,
            response=response,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            latency_ms=latency_ms,
            _ttl_hours=self.config.get("cache.ttl_hours", 24),
        )
        
        return self.db.set(entry)
    
    def clear_expired(self) -> int:
        """清理过期缓存"""
        return self.db.clear_expired()
    
    def clear_all(self) -> int:
        """清空所有缓存"""
        return self.db.clear_all()
    
    def stats(self) -> dict:
        """获取统计"""
        return self.db.get_stats()
    
    def toggle(self) -> bool:
        """切换缓存状态"""
        self.enabled = not self.enabled
        return self.enabled


# 全局缓存实例
_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """获取全局缓存实例"""
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache
