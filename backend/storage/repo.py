"""
数据仓库：论文、运行、评分、推送的CRUD操作
"""
import json
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Set
from backend.models import Paper, ScoredPaper
from backend.storage.db import get_db
from backend.core.deduplication import generate_title_fingerprint
from backend.core.config import Config

logger = logging.getLogger(__name__)


class PaperRepository:
    """论文数据仓库"""
    
    def get_sent_ids(self) -> Set[str]:
        """获取已推送的ID集合（用于去重）"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT item_id FROM dedup_keys")
            return {row[0] for row in cursor.fetchall()}
    
    def save_paper(self, paper: Paper, item_id: str) -> int:
        """保存论文，返回paper_id（支持标题指纹）"""
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                # 生成标题指纹
                title_fp = None
                if Config.ENABLE_TITLE_FINGERPRINT_DEDUP and paper.title:
                    title_fp = generate_title_fingerprint(paper.title)
                
                cursor.execute("""
                    INSERT OR IGNORE INTO papers 
                    (item_id, title, abstract, date, source, doi, link, citation_count, influential_count, title_fingerprint)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item_id, paper.title, paper.abstract, paper.date, paper.source,
                    paper.doi, paper.link, paper.citation_count, paper.influential_count, title_fp
                ))
                
                # 获取paper_id
                cursor.execute("SELECT id FROM papers WHERE item_id = ?", (item_id,))
                row = cursor.fetchone()
                if row:
                    paper_id = row[0]
                else:
                    # 如果INSERT OR IGNORE没有插入（已存在），获取现有ID
                    cursor.execute("SELECT id FROM papers WHERE item_id = ?", (item_id,))
                    paper_id = cursor.fetchone()[0]
                
                # 更新dedup_keys
                cursor.execute("""
                    INSERT OR IGNORE INTO dedup_keys (item_id, paper_id)
                    VALUES (?, ?)
                """, (item_id, paper_id))
                
                return paper_id
            except Exception as e:
                logger.error(f"保存论文失败: {e}")
                raise
    
    def create_run(self, window_days: int) -> str:
        """创建运行记录，返回run_id"""
        run_id = str(uuid.uuid4())
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO runs (run_id, window_days, start_time, status)
                VALUES (?, ?, ?, 'running')
            """, (run_id, window_days, datetime.now().isoformat()))
        return run_id
    
    def update_run(
        self,
        run_id: str,
        total_papers: int = None,
        unseen_papers: int = None,
        top_k: int = None,
        status: str = None,
        error: str = None
    ):
        """更新运行记录"""
        updates = []
        params = []
        
        if total_papers is not None:
            updates.append("total_papers = ?")
            params.append(total_papers)
        if unseen_papers is not None:
            updates.append("unseen_papers = ?")
            params.append(unseen_papers)
        if top_k is not None:
            updates.append("top_k = ?")
            params.append(top_k)
        if status:
            updates.append("status = ?")
            params.append(status)
        if error:
            updates.append("error = ?")
            params.append(error)
        
        if status == 'completed' or status == 'failed':
            updates.append("end_time = ?")
            params.append(datetime.now().isoformat())
        
        if updates:
            params.append(run_id)
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"UPDATE runs SET {', '.join(updates)} WHERE run_id = ?",
                    params
                )
    
    def save_scores(self, run_id: str, scored_papers: List[ScoredPaper]):
        """保存评分记录（防止同一run_id下重复评分）"""
        with get_db() as conn:
            cursor = conn.cursor()
            saved_paper_ids = set()  # 记录已保存的paper_id，防止重复
            
            for scored in scored_papers:
                item_id = self._get_item_id(scored.paper)
                if not item_id:
                    continue
                
                # 先确保论文已保存（在同一个连接中）
                paper = scored.paper
                try:
                    # 生成标题指纹
                    title_fp = None
                    if Config.ENABLE_TITLE_FINGERPRINT_DEDUP and paper.title:
                        title_fp = generate_title_fingerprint(paper.title)
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO papers 
                        (item_id, title, abstract, date, source, doi, link, citation_count, influential_count, title_fingerprint)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        item_id, paper.title, paper.abstract, paper.date, paper.source,
                        paper.doi, paper.link, paper.citation_count, paper.influential_count, title_fp
                    ))
                    
                    # 获取paper_id
                    cursor.execute("SELECT id FROM papers WHERE item_id = ?", (item_id,))
                    row = cursor.fetchone()
                    if not row:
                        continue
                    paper_id = row[0]
                    
                    # 防止同一次运行中重复评分
                    if paper_id in saved_paper_ids:
                        logger.debug(f"跳过重复评分: paper_id={paper_id}")
                        continue
                    saved_paper_ids.add(paper_id)
                    
                    # 注意：不再在这里更新dedup_keys
                    # dedup_keys应该在推送成功后才更新（在save_push中通过save_paper更新）
                except Exception as e:
                    logger.error(f"保存论文失败: {e}")
                    continue
                
                # 检查是否已经存在评分记录（防止数据库层面重复）
                cursor.execute("""
                    SELECT id FROM scores WHERE run_id = ? AND paper_id = ?
                """, (run_id, paper_id))
                if cursor.fetchone():
                    logger.debug(f"评分已存在: run_id={run_id[:8]}, paper_id={paper_id}")
                    continue
                
                # 保存评分
                reasons_json = json.dumps([
                    {
                        'category': r.category,
                        'points': r.points,
                        'description': r.description
                    }
                    for r in scored.reasons
                ], ensure_ascii=False)
                
                cursor.execute("""
                    INSERT INTO scores (run_id, paper_id, score, reasons_json)
                    VALUES (?, ?, ?, ?)
                """, (run_id, paper_id, scored.score, reasons_json))
    
    def save_push(
        self,
        run_id: str,
        paper: Paper,
        channel: str,
        status: str = 'success',
        error: str = None
    ):
        """保存推送记录"""
        item_id = self._get_item_id(paper)
        if not item_id:
            return
        
        paper_id = self.save_paper(paper, item_id)
        
        with get_db() as conn:
            cursor = conn.cursor()
            pushed_at = datetime.now().isoformat() if status == 'success' else None
            cursor.execute("""
                INSERT INTO pushes (run_id, paper_id, channel, status, error, pushed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (run_id, paper_id, channel, status, error, pushed_at))
    
    def _get_item_id(self, paper: Paper) -> str:
        """获取item_id（使用deduplication模块的统一逻辑）"""
        from backend.core.deduplication import get_item_id
        return get_item_id(paper)
    
    def get_run_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取运行历史"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT run_id, window_days, start_time, end_time, 
                       total_papers, unseen_papers, top_k, status, error
                FROM runs
                ORDER BY start_time DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            return [
                {
                    'run_id': row[0],
                    'window_days': row[1],
                    'start_time': row[2],
                    'end_time': row[3],
                    'total_papers': row[4],
                    'unseen_papers': row[5],
                    'top_k': row[6],
                    'status': row[7],
                    'error': row[8],
                }
                for row in rows
            ]
    
    def get_paper_scores(self, run_id: str) -> List[Dict[str, Any]]:
        """获取某次运行的论文评分详情"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.title, p.source, p.date, s.score, s.reasons_json
                FROM scores s
                JOIN papers p ON s.paper_id = p.id
                WHERE s.run_id = ?
                ORDER BY s.score DESC
            """, (run_id,))
            
            rows = cursor.fetchall()
            return [
                {
                    'title': row[0],
                    'source': row[1],
                    'date': row[2],
                    'score': row[3],
                    'reasons': json.loads(row[4]) if row[4] else []
                }
                for row in rows
            ]
    
    def get_papers(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        source: Optional[str] = None,
        min_score: Optional[float] = None
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        获取论文列表（支持分页、搜索、筛选）
        返回: (论文列表, 总数)
        """
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if search:
                conditions.append("(p.title LIKE ? OR p.abstract LIKE ?)")
                search_pattern = f"%{search}%"
                params.extend([search_pattern, search_pattern])
            
            if source:
                conditions.append("p.source = ?")
                params.append(source)
            
            if min_score is not None:
                # 需要关联 scores 表来筛选分数
                conditions.append("""
                    p.id IN (
                        SELECT paper_id FROM scores 
                        WHERE score >= ?
                    )
                """)
                params.append(min_score)
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            # 获取总数
            count_query = f"SELECT COUNT(DISTINCT p.id) FROM papers p {where_clause}"
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # 获取分页数据（关联最新的评分）
            offset = (page - 1) * page_size
            query = f"""
                SELECT DISTINCT
                    p.id,
                    p.item_id,
                    p.title,
                    p.abstract,
                    p.date,
                    p.source,
                    p.doi,
                    p.link,
                    p.citation_count,
                    p.influential_count,
                    COALESCE(MAX(s.score), 0) as score
                FROM papers p
                LEFT JOIN scores s ON p.id = s.paper_id
                {where_clause}
                GROUP BY p.id
                ORDER BY score DESC, p.created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([page_size, offset])
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            papers = [
                {
                    'id': row[0],
                    'item_id': row[1],
                    'title': row[2],
                    'abstract': row[3] or '',
                    'date': row[4] or '',
                    'source': row[5] or '',
                    'doi': row[6] or '',
                    'link': row[7] or '',
                    'citation_count': row[8] or 0,
                    'influential_count': row[9] or 0,
                    'score': row[10] or 0.0
                }
                for row in rows
            ]
            
            return papers, total
    
    def get_paper_by_id(self, paper_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取单篇论文"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    p.id,
                    p.item_id,
                    p.title,
                    p.abstract,
                    p.date,
                    p.source,
                    p.doi,
                    p.link,
                    p.citation_count,
                    p.influential_count,
                    COALESCE(MAX(s.score), 0) as score
                FROM papers p
                LEFT JOIN scores s ON p.id = s.paper_id
                WHERE p.id = ?
                GROUP BY p.id
            """, (paper_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'id': row[0],
                'item_id': row[1],
                'title': row[2],
                'abstract': row[3] or '',
                'date': row[4] or '',
                'source': row[5] or '',
                'doi': row[6] or '',
                'link': row[7] or '',
                'citation_count': row[8] or 0,
                'influential_count': row[9] or 0,
                'score': row[10] or 0.0
            }
    
    def delete_paper(self, paper_id: int) -> bool:
        """删除论文（级联删除相关记录）"""
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                # 先获取 item_id
                cursor.execute("SELECT item_id FROM papers WHERE id = ?", (paper_id,))
                row = cursor.fetchone()
                if not row:
                    return False
                
                item_id = row[0]
                
                # 删除相关记录（级联）
                cursor.execute("DELETE FROM scores WHERE paper_id = ?", (paper_id,))
                cursor.execute("DELETE FROM pushes WHERE paper_id = ?", (paper_id,))
                cursor.execute("DELETE FROM dedup_keys WHERE paper_id = ?", (paper_id,))
                cursor.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
                
                return True
            except Exception as e:
                logger.error(f"删除论文失败: {e}")
                return False

