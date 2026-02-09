"""
SQLite数据库连接和初始化
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
from backend.core.config import Config

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
        
        # users表：用户信息
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                role TEXT DEFAULT 'user',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        # 检查并添加latest_score字段(用于去除JOIN提升查询性能)
        try:
            cursor.execute("SELECT latest_score FROM papers LIMIT 1")
        except Exception:
            logger.info("添加latest_score字段到papers表")
            cursor.execute("ALTER TABLE papers ADD COLUMN latest_score REAL DEFAULT 0")

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_item_id ON papers(item_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_date ON papers(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_title_fp ON papers(title_fingerprint)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_source ON papers(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_latest_score ON papers(latest_score)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scores_run_id ON scores(run_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scores_paper_id ON scores(paper_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pushes_run_id ON pushes(run_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pushes_status ON pushes(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")

        # 创建FTS5全文检索虚拟表（用于高性能标题/摘要搜索）
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
                title,
                abstract,
                content='papers',
                content_rowid='id',
                tokenize='unicode61 remove_diacritics 2'
            )
        """)

        # 创建触发器保持FTS5索引与papers表同步
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS papers_fts_insert AFTER INSERT ON papers BEGIN
                INSERT INTO papers_fts(rowid, title, abstract)
                VALUES (new.id, new.title, new.abstract);
            END
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS papers_fts_delete AFTER DELETE ON papers BEGIN
                INSERT INTO papers_fts(papers_fts, rowid, title, abstract)
                VALUES ('delete', old.id, old.title, old.abstract);
            END
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS papers_fts_update AFTER UPDATE ON papers BEGIN
                INSERT INTO papers_fts(papers_fts, rowid, title, abstract)
                VALUES ('delete', old.id, old.title, old.abstract);
                INSERT INTO papers_fts(rowid, title, abstract)
                VALUES (new.id, new.title, new.abstract);
            END
        """)

        # 为已有数据重建FTS索引（仅在FTS表为空时执行）
        cursor.execute("SELECT COUNT(*) FROM papers_fts")
        fts_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM papers")
        papers_count = cursor.fetchone()[0]
        if papers_count > 0 and fts_count == 0:
            logger.info(f"为 {papers_count} 篇已有论文重建FTS索引...")
            cursor.execute("""
                INSERT INTO papers_fts(rowid, title, abstract)
                SELECT id, title, abstract FROM papers
            """)
            logger.info("FTS索引重建完成")

        # 回填latest_score（仅在latest_score全为0或NULL时执行）
        cursor.execute("SELECT COUNT(*) FROM papers WHERE latest_score > 0")
        scored_count = cursor.fetchone()[0]
        if papers_count > 0 and scored_count == 0:
            cursor.execute("SELECT COUNT(*) FROM scores")
            total_scores = cursor.fetchone()[0]
            if total_scores > 0:
                logger.info("回填papers.latest_score...")
                cursor.execute("""
                    UPDATE papers SET latest_score = COALESCE(
                        (SELECT MAX(s.score) FROM scores s WHERE s.paper_id = papers.id), 0
                    )
                """)
                logger.info("latest_score回填完成")

        conn.commit()
        logger.info(f"数据库初始化完成: {db_path}")







