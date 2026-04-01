"""
Yinian 用量统计
"""
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from yinian.core.config import get_config


@dataclass
class UsageRecord:
    """使用记录"""
    id: int = 0
    timestamp: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    session: str = ""
    question_type: str = ""


class StatsDB:
    """统计数据库"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    cost REAL DEFAULT 0.0,
                    latency_ms REAL DEFAULT 0.0,
                    session TEXT DEFAULT '',
                    question_type TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON usage(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_model ON usage(model)
            """)
    
    def add_record(self, record: UsageRecord):
        """添加记录"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO usage (timestamp, model, input_tokens, output_tokens, 
                                   total_tokens, cost, latency_ms, session, question_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.timestamp,
                record.model,
                record.input_tokens,
                record.output_tokens,
                record.total_tokens,
                record.cost,
                record.latency_ms,
                record.session,
                record.question_type,
            ))
    
    def get_stats(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict:
        """获取统计"""
        query = "SELECT "
    
    def get_daily_stats(self, days: int = 30) -> List[Dict]:
        """获取每日统计"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT 
                    DATE(timestamp) as date,
                    SUM(input_tokens) as input_tokens,
                    SUM(output_tokens) as output_tokens,
                    SUM(total_tokens) as total_tokens,
                    SUM(cost) as total_cost,
                    COUNT(*) as request_count,
                    model
                FROM usage
                WHERE timestamp >= DATE('now', ?)
                GROUP BY DATE(timestamp), model
                ORDER BY date DESC
            """, (f"-{days} days",))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_monthly_cost(self, year: int, month: int) -> float:
        """获取月度费用"""
        date_str = f"{year}-{month:02d}%"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT SUM(cost) FROM usage WHERE timestamp LIKE ?",
                (date_str,)
            )
            result = cursor.fetchone()
            return result[0] or 0.0
    
    def get_model_stats(self) -> List[Dict]:
        """获取模型统计"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT 
                    model,
                    SUM(input_tokens) as input_tokens,
                    SUM(output_tokens) as output_tokens,
                    SUM(total_tokens) as total_tokens,
                    SUM(cost) as total_cost,
                    COUNT(*) as request_count,
                    AVG(latency_ms) as avg_latency
                FROM usage
                GROUP BY model
                ORDER BY total_cost DESC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def clear_old_records(self, days: int = 90):
        """清理旧记录"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM usage WHERE timestamp < DATE('now', ?)",
                (f"-{days} days",)
            )


class Stats:
    """用量统计"""
    
    def __init__(self):
        self.config = get_config()
        self.db_path = self.config.cache_dir / "stats.db"
        self.db = StatsDB(self.db_path)
    
    def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        latency_ms: float,
        session: str = "",
        question_type: str = ""
    ):
        """记录一次 API 调用"""
        record = UsageRecord(
            timestamp=datetime.now().isoformat(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=cost,
            latency_ms=latency_ms,
            session=session,
            question_type=question_type,
        )
        self.db.add_record(record)
        
        # 检查预算
        self._check_budget()
    
    def _check_budget(self):
        """检查预算"""
        monthly_limit = self.config.get("budget.monthly_limit", 100.0)
        alert_threshold = self.config.get("budget.alert_threshold", 0.8)
        
        now = datetime.now()
        current_cost = self.db.get_monthly_cost(now.year, now.month)
        
        if current_cost >= monthly_limit * alert_threshold:
            remaining = monthly_limit - current_cost
            if remaining > 0:
                logger.warning(
                    f"⚠️ 预算提醒: 本月已消费 ¥{current_cost:.2f}，"
                    f"超出 ¥{alert_threshold*100:.0f}% 阈值，"
                    f"剩余预算约 ¥{remaining:.2f}"
                )
    
    def get_summary(self) -> Dict:
        """获取统计摘要"""
        daily = self.db.get_daily_stats(30)
        
        total_cost = sum(d.get("total_cost", 0) for d in daily)
        total_tokens = sum(d.get("total_tokens", 0) for d in daily)
        total_requests = sum(d.get("request_count", 0) for d in daily)
        
        now = datetime.now()
        monthly_cost = self.db.get_monthly_cost(now.year, now.month)
        
        return {
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "total_requests": total_requests,
            "monthly_cost": monthly_cost,
            "monthly_limit": self.config.get("budget.monthly_limit", 100.0),
        }
    
    def get_model_breakdown(self) -> List[Dict]:
        """获取模型费用分解"""
        return self.db.get_model_stats()
    
    def export_csv(self, path: Path):
        """导出 CSV"""
        import csv
        
        daily = self.db.get_daily_stats(365)
        
        with open(path, "w", newline="", encoding="utf-8") as f:
            if not daily:
                return
            
            writer = csv.DictWriter(f, fieldnames=daily[0].keys())
            writer.writeheader()
            writer.writerows(daily)


# 全局统计实例
_stats: Optional[Stats] = None


def get_stats() -> Stats:
    """获取全局统计实例"""
    global _stats
    if _stats is None:
        _stats = Stats()
    return _stats
