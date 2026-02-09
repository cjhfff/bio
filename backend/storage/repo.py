"""
数据仓库：论文、运行、评分、推送的CRUD操作
"""
import re
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


def _parse_search_query(search: str) -> str:
    """
    将用户输入的搜索词转换为FTS5查询语法。
    支持:
      - 简单关键词: "nitrogen fixation" -> nitrogen fixation
      - 双引号精确匹配: '"nitrogen fixation"' -> "nitrogen fixation"
      - AND/OR/NOT 布尔操作: "nitrogen AND enzyme NOT cancer"
      - 加减号: "+nitrogen -cancer" -> nitrogen NOT cancer
    """
    search = search.strip()
    if not search:
        return ""

    # 如果用户已经在用FTS5语法（包含AND/OR/NOT/NEAR），直接使用
    if re.search(r'\b(AND|OR|NOT|NEAR)\b', search):
        return search

    # 处理 +/- 前缀语法
    tokens = []
    # 先提取引号内的短语
    parts = re.split(r'(".*?")', search)
    for part in parts:
        if part.startswith('"') and part.endswith('"'):
            tokens.append(part)
        else:
            for word in part.split():
                if word.startswith('-'):
                    keyword = word[1:]
                    if keyword:
                        tokens.append(f'NOT {keyword}')
                elif word.startswith('+'):
                    keyword = word[1:]
                    if keyword:
                        tokens.append(keyword)
                else:
                    tokens.append(word)

    return " ".join(tokens)


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

                # 更新papers表的latest_score（取最高分）
                cursor.execute("""
                    UPDATE papers SET latest_score = MAX(
                        COALESCE(latest_score, 0), ?
                    ) WHERE id = ?
                """, (scored.score, paper_id))
    
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
        min_score: Optional[float] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort_by: str = "score",
        sort_order: str = "desc"
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        获取论文列表（支持FTS5全文检索、布尔搜索、多字段筛选、分页）

        搜索语法:
          - 普通关键词: "nitrogen fixation"
          - 精确匹配: '"nitrogen fixation"'（双引号包裹短语）
          - 布尔操作: "nitrogen AND enzyme NOT cancer"
          - 加减号: "+nitrogen -cancer"
          - 字段前缀: "source:biorxiv", "doi:10.1234"

        返回: (论文列表, 总数)
        """
        with get_db() as conn:
            cursor = conn.cursor()

            # 构建查询条件
            conditions = []
            params = []
            use_fts = False
            fts_query = ""

            if search:
                # 提取字段前缀过滤（source:xxx, doi:xxx）
                field_filters = re.findall(r'(source|doi|date):(\S+)', search, re.IGNORECASE)
                # 移除字段前缀部分，剩余作为全文检索关键词
                remaining_search = re.sub(r'(source|doi|date):\S+', '', search, flags=re.IGNORECASE).strip()

                for field, value in field_filters:
                    field_lower = field.lower()
                    if field_lower == 'source':
                        conditions.append("LOWER(p.source) LIKE ?")
                        params.append(f"%{value.lower()}%")
                    elif field_lower == 'doi':
                        conditions.append("p.doi LIKE ?")
                        params.append(f"%{value}%")
                    elif field_lower == 'date':
                        conditions.append("p.date LIKE ?")
                        params.append(f"%{value}%")

                # 全文检索
                if remaining_search:
                    fts_query = _parse_search_query(remaining_search)
                    if fts_query:
                        use_fts = True

            if source:
                conditions.append("p.source = ?")
                params.append(source)

            if min_score is not None:
                conditions.append("p.latest_score >= ?")
                params.append(min_score)

            if date_from:
                conditions.append("p.date >= ?")
                params.append(date_from)

            if date_to:
                conditions.append("p.date <= ?")
                params.append(date_to)

            # 验证排序字段
            allowed_sort = {"score", "date", "citation_count", "created_at"}
            if sort_by not in allowed_sort:
                sort_by = "score"
            sort_col = {
                "score": "p.latest_score",
                "date": "p.date",
                "citation_count": "p.citation_count",
                "created_at": "p.created_at"
            }[sort_by]
            order = "DESC" if sort_order.lower() == "desc" else "ASC"

            if use_fts:
                # FTS5全文检索路径 - 高性能
                where_clause = "WHERE p.id IN (SELECT rowid FROM papers_fts WHERE papers_fts MATCH ?)"
                fts_params = [fts_query]
                if conditions:
                    where_clause += " AND " + " AND ".join(conditions)
                    fts_params.extend(params)

                # 获取总数
                try:
                    count_query = f"SELECT COUNT(*) FROM papers p {where_clause}"
                    cursor.execute(count_query, fts_params)
                    total = cursor.fetchone()[0]
                except Exception as e:
                    # FTS查询语法错误时回退到LIKE
                    logger.warning(f"FTS5查询失败，回退到LIKE搜索: {e}")
                    return self._get_papers_like_fallback(
                        cursor, search, source, min_score, date_from, date_to,
                        sort_col, order, page, page_size
                    )

                # 获取分页数据
                offset = (page - 1) * page_size
                query = f"""
                    SELECT
                        p.id, p.item_id, p.title, p.abstract, p.date,
                        p.source, p.doi, p.link, p.citation_count,
                        p.influential_count, COALESCE(p.latest_score, 0) as score
                    FROM papers p
                    {where_clause}
                    ORDER BY {sort_col} {order}, p.created_at DESC
                    LIMIT ? OFFSET ?
                """
                fts_params.extend([page_size, offset])
                cursor.execute(query, fts_params)
            else:
                # 非全文检索路径 - 使用索引
                where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

                # 获取总数
                count_query = f"SELECT COUNT(*) FROM papers p {where_clause}"
                cursor.execute(count_query, params)
                total = cursor.fetchone()[0]

                # 获取分页数据（使用papers表的latest_score，无需JOIN）
                offset = (page - 1) * page_size
                query = f"""
                    SELECT
                        p.id, p.item_id, p.title, p.abstract, p.date,
                        p.source, p.doi, p.link, p.citation_count,
                        p.influential_count, COALESCE(p.latest_score, 0) as score
                    FROM papers p
                    {where_clause}
                    ORDER BY {sort_col} {order}, p.created_at DESC
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

    def _get_papers_like_fallback(
        self, cursor, search, source, min_score, date_from, date_to,
        sort_col, order, page, page_size
    ) -> tuple[List[Dict[str, Any]], int]:
        """FTS5查询失败时的LIKE回退方案"""
        conditions = []
        params = []

        if search:
            conditions.append("(p.title LIKE ? OR p.abstract LIKE ?)")
            pattern = f"%{search}%"
            params.extend([pattern, pattern])
        if source:
            conditions.append("p.source = ?")
            params.append(source)
        if min_score is not None:
            conditions.append("p.latest_score >= ?")
            params.append(min_score)
        if date_from:
            conditions.append("p.date >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("p.date <= ?")
            params.append(date_to)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        count_query = f"SELECT COUNT(*) FROM papers p {where_clause}"
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]

        offset = (page - 1) * page_size
        query = f"""
            SELECT
                p.id, p.item_id, p.title, p.abstract, p.date,
                p.source, p.doi, p.link, p.citation_count,
                p.influential_count, COALESCE(p.latest_score, 0) as score
            FROM papers p
            {where_clause}
            ORDER BY {sort_col} {order}, p.created_at DESC
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
        """根据 ID 获取单篇论文（无需JOIN，使用冗余分数字段）"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    p.id, p.item_id, p.title, p.abstract, p.date,
                    p.source, p.doi, p.link, p.citation_count,
                    p.influential_count, COALESCE(p.latest_score, 0) as score
                FROM papers p
                WHERE p.id = ?
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

