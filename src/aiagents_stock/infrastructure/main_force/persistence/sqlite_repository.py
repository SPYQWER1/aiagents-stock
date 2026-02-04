import json
import os
import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from aiagents_stock.domain.main_force.model import MainForceAnalysis, MainForceRecommendation
from aiagents_stock.domain.main_force.ports import MainForceAnalysisRepository


def get_default_db_path() -> str:
    """获取默认数据库路径（基于项目根目录）"""
    # src/aiagents_stock/infrastructure/main_force/persistence/sqlite_repository.py -> ... -> project_root
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent.parent.parent.parent
    return str(project_root / "database_files" / "main_force_analysis.db")

class SqliteMainForceAnalysisRepository(MainForceAnalysisRepository):
    """基于 SQLite 的主力选股分析仓储"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            self.db_path = get_default_db_path()
        else:
            self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS main_force_overall_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_date TEXT,
                params TEXT,
                raw_stocks_count INTEGER,
                filtered_stocks_count INTEGER,
                fund_flow_analysis TEXT,
                industry_analysis TEXT,
                fundamental_analysis TEXT,
                recommendations TEXT,
                total_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def save(self, analysis: MainForceAnalysis) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 序列化复杂对象
        params_json = json.dumps(analysis.params, ensure_ascii=False)
        recommendations_json = json.dumps([asdict(r) for r in analysis.recommendations], ensure_ascii=False)
        
        cursor.execute("""
            INSERT INTO main_force_overall_analysis (
                analysis_date, params, raw_stocks_count, filtered_stocks_count,
                fund_flow_analysis, industry_analysis, fundamental_analysis,
                recommendations, total_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analysis.analysis_date.strftime("%Y-%m-%d %H:%M:%S"),
            params_json,
            len(analysis.raw_stocks),
            len(analysis.filtered_stocks),
            analysis.fund_flow_analysis,
            analysis.industry_analysis,
            analysis.fundamental_analysis,
            recommendations_json,
            analysis.total_time
        ))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return record_id

    def get_by_id(self, record_id: int) -> Optional[MainForceAnalysis]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM main_force_overall_analysis WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        # 这里只简单恢复部分数据用于展示，完整恢复可能需要存储更多 raw_stocks 数据
        # 目前只恢复基本信息和推荐结果
        try:
            recommendations_data = json.loads(row[8])
            recommendations = [MainForceRecommendation(**r) for r in recommendations_data]
        except (json.JSONDecodeError, TypeError, ValueError):
            recommendations = []
            
        return MainForceAnalysis(
            id=row[0],
            analysis_date=datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S"),
            params=json.loads(row[2]),
            fund_flow_analysis=row[5],
            industry_analysis=row[6],
            fundamental_analysis=row[7],
            recommendations=recommendations,
            total_time=row[9]
        )
        
    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM main_force_overall_analysis ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]

    def delete(self, record_id: int) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM main_force_overall_analysis WHERE id = ?", (record_id,))
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            return affected > 0
        except Exception as e:
            print(f"Delete failed: {e}")
            return False

    def get_statistics(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM batch_analysis_history")
        total_records = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(batch_count) FROM batch_analysis_history")
        total_stocks = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(success_count) FROM batch_analysis_history")
        total_success = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(failed_count) FROM batch_analysis_history")
        total_failed = cursor.fetchone()[0] or 0

        cursor.execute("SELECT AVG(total_time) FROM batch_analysis_history")
        avg_time = cursor.fetchone()[0] or 0

        conn.close()

        return {
            "total_records": total_records,
            "total_stocks_analyzed": total_stocks,
            "total_success": total_success,
            "total_failed": total_failed,
            "average_time": round(avg_time, 2),
            "success_rate": round(total_success / total_stocks * 100, 2) if total_stocks > 0 else 0,
        }
