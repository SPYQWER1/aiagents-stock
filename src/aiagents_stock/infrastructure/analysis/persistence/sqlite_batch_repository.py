import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from aiagents_stock.domain.analysis.ports import StockBatchAnalysisRepository

logger = logging.getLogger(__name__)

def get_default_db_path() -> str:
    """获取默认数据库路径（基于项目根目录）"""
    # src/aiagents_stock/infrastructure/analysis/persistence/sqlite_batch_repository.py -> ... -> project_root
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent.parent.parent.parent
    return str(project_root / "database_files" / "stock_batch_analysis.db")


class SqliteStockBatchAnalysisRepository(StockBatchAnalysisRepository):
    """基于 SQLite 的股票批量分析历史仓储"""

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

        # 批量分析历史记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_batch_analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_date TEXT NOT NULL,
                batch_count INTEGER NOT NULL,
                analysis_mode TEXT NOT NULL,
                success_count INTEGER NOT NULL,
                failed_count INTEGER NOT NULL,
                total_time REAL NOT NULL,
                results_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analysis_date 
            ON stock_batch_analysis_history(analysis_date)
        """)

        conn.commit()
        conn.close()

    def save(
        self,
        batch_count: int,
        analysis_mode: str,
        success_count: int,
        failed_count: int,
        total_time: float,
        results: List[Dict[str, Any]],
    ) -> int:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 序列化结果
            # 注意：我们需要确保 results 中的对象是可序列化的
            # 这里我们假设传入的 results 已经是字典列表
            results_json = json.dumps(results, ensure_ascii=False)

            from datetime import datetime
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute(
                """
                INSERT INTO stock_batch_analysis_history 
                (analysis_date, batch_count, analysis_mode, success_count, failed_count, total_time, results_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    current_date,
                    batch_count,
                    analysis_mode,
                    success_count,
                    failed_count,
                    total_time,
                    results_json,
                ),
            )
            
            record_id = cursor.lastrowid
            conn.commit()
            return record_id
        except Exception as e:
            logger.error(f"保存批量分析历史失败: {e}")
            raise e
        finally:
            if 'conn' in locals():
                conn.close()

    def get_all(self, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM stock_batch_analysis_history 
                ORDER BY created_at DESC 
                LIMIT ?
                """,
                (limit,),
            )
            
            rows = cursor.fetchall()
            
            history = []
            for row in rows:
                record = dict(row)
                try:
                    record["results"] = json.loads(record["results_json"])
                except (json.JSONDecodeError, TypeError, ValueError):
                    record["results"] = []
                history.append(record)
                
            return history
        except Exception as e:
            logger.error(f"获取批量分析历史失败: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()

    def get_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM stock_batch_analysis_history WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            
            if row:
                result = dict(row)
                # 解析 JSON 结果
                try:
                    result["results"] = json.loads(result["results_json"])
                except (json.JSONDecodeError, TypeError, ValueError):
                    result["results"] = []
                return result
            return None
        except Exception as e:
            logger.error(f"获取单条批量分析记录失败: {e}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    def delete(self, record_id: int) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM stock_batch_analysis_history WHERE id = ?", (record_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"删除批量分析记录失败: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
