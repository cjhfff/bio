"""
SQLite数据库连接和初始化
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
from backend.config import Config

logger = logging.getLogger(__name__)


def get_db_path() -> Path:
    """获取数据库路径"""
    db_path = Path(Config.DB_PATH)
    if not db_path.is_absolute():
        # 相对于工作目录
        db_path = Path.cwd() / db_path
    return db_path


@contextmanager
def get_db():
    """获取数据库连接(上下文管理器)"""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    
    # 启用WAL模式和并发安全配置
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"数据库操作失败: {e}")
        raise
    finally:
        conn.close()


def init_db():
    """初始化数据库表结构"""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # papers表：论文元信息
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                abstract TEXT,
                date TEXT,
                source TEXT,
                doi TEXT,
                link TEXT,
                citation_count INTEGER DEFAULT 0,
                influential_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 检查并添加title_fingerprint字段(如果不存在)
        try:
            cursor.execute("SELECT title_fingerprint FROM papers LIMIT 1")
        except:
            logger.info("添加title_fingerprint字段到papers表")
            cursor.execute("ALTER TABLE papers ADD COLUMN title_fingerprint TEXT")
        
        # runs表：每次运行记录
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT UNIQUE NOT NULL,
                window_days INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                total_papers INTEGER DEFAULT 0,
                unseen_papers INTEGER DEFAULT 0,
                top_k INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running',
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # scores表：评分记录（可解释性）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                paper_id INTEGER NOT NULL,
                score REAL NOT NULL,
                reasons_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs(run_id),
                FOREIGN KEY (paper_id) REFERENCES papers(id)
            )
        """)
        
        # pushes表：推送记录
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pushes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                paper_id INTEGER NOT NULL,
                channel TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                error TEXT,
                pushed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs(run_id),
                FOREIGN KEY (paper_id) REFERENCES papers(id)
            )
        """)
        
        # dedup_keys表：去重索引（快速查询）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dedup_keys (
                item_id TEXT PRIMARY KEY,
                paper_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (paper_id) REFERENCES papers(id)
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_item_id ON papers(item_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_date ON papers(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_title_fp ON papers(title_fingerprint)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scores_run_id ON scores(run_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pushes_run_id ON pushes(run_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pushes_status ON pushes(status)")
        
        conn.commit()
        logger.info(f"数据库初始化完成: {db_path}")







