"""Semantic Scholar 数据源(支持指数退避重试和API Key)"""
import datetime
import requests
import logging
import time
from typing import Set, List
from app.models import Paper, SourceResult
from app.sources.base import BaseSource
from app.config import Config
from app.filtering import should_exclude_paper, is_recent_date

logger = logging.getLogger(__name__)


class SemanticScholarSource(BaseSource):
    """Semantic Scholar 数据源"""
    
    def __init__(self, window_days: int = None):
        # 默认使用 30 天窗口，因为 Semantic Scholar 更新较慢
        super().__init__("SemanticScholar", window_days or 30)
        # 扩展查询词
        self.queries = [
            # 固氮相关
            "Biological Nitrogen Fixation",
            "nitrogenase enzyme mechanism",
            "rhizobium legume symbiosis",
            # 信号转导相关
            "signal transduction pathway",
            "receptor kinase signaling",
            "plant immunity signaling",
            # 酶结构相关
            "enzyme structure mechanism",
            "cryo-EM protein structure",
            "crystal structure catalytic",
        ]
    
    def fetch(self, sent_ids: Set[str], exclude_keywords: List[str]) -> SourceResult:
        papers = []
        all_keywords = Config.get_all_keywords()
        target_categories = [c.lower() for c in Config.TARGET_CATEGORIES]
        today = datetime.date.today()
        
        start_time = time.time()
        failed_queries = []
        successful_queries = 0
        
        # 准备API Key请求头
        headers = {}
        if Config.SEMANTIC_SCHOLAR_API_KEY:
            headers['x-api-key'] = Config.SEMANTIC_SCHOLAR_API_KEY
            logger.info("[Semantic Scholar] 使用API Key")
        else:
            logger.warning("[Semantic Scholar] 未配置API Key,使用公共API(可能遭遇限流)")
        
        for query in self.queries:
            max_retries = 3
            success = False
            
            for attempt in range(max_retries):
                try:
                    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=10&sort=year&order=desc&fields=title,abstract,citationCount,influentialCitationCount,year,publicationDate,externalIds"
                    
                    response = requests.get(
                        url, 
                        headers=headers,
                        timeout=15, 
                        proxies={'http': None, 'https': None}
                    )
                    
                    if response.status_code == 200:
                        data = response.json().get('data', [])
                        
                        for d in data:
                            title = d.get('title', '') or '无标题'
                            abstract = d.get('abstract', '') or ''
                            
                            text_lower = (title + " " + abstract).lower()
                            
                            # 放宽过滤：关键词匹配 OR 分类匹配
                            has_keyword = any(kw in text_lower for kw in all_keywords)
                            has_category = any(cat in text_lower for cat in target_categories)
                            
                            if not (has_keyword or has_category):
                                continue
                            
                            # 提取日期
                            pub_date = d.get('publicationDate', '')
                            if pub_date:
                                date_str = pub_date[:10]
                            else:
                                year = d.get('year', today.year)
                                date_str = f"{year}-01-01"
                            
                            paper = Paper(
                                title=title,
                                abstract=abstract,
                                date=date_str,
                                source='SemanticScholar',
                                doi=d.get('externalIds', {}).get('DOI', '') if isinstance(d.get('externalIds'), dict) else '',
                                link='',
                                citation_count=d.get('citationCount', 0) or 0,
                                influential_count=d.get('influentialCitationCount', 0) or 0
                            )
                            
                            if should_exclude_paper(paper, exclude_keywords):
                                continue
                            if not is_recent_date(date_str, days=self.window_days):
                                continue
                            
                            item_id = self.get_item_id(paper)
                            if item_id and item_id not in sent_ids:
                                papers.append(paper)
                        
                        successful_queries += 1
                        success = True
                        break  # 成功则跳出重试循环
                    
                    elif response.status_code == 429:
                        # API频率限制
                        wait_time = 2 ** attempt  # 指数退避: 1, 2, 4秒
                        logger.warning(
                            f"[Semantic Scholar] 429限流,查询'{query}' 第{attempt+1}次重试,等待{wait_time}秒"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.warning(
                            f"[Semantic Scholar] 查询'{query}'返回{response.status_code},第{attempt+1}次重试"
                        )
                        time.sleep(2 ** attempt)
                
                except Exception as e:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"[Semantic Scholar] 查询'{query}'异常: {e}, 第{attempt+1}/{max_retries}次重试"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
            
            if not success:
                failed_queries.append(query)
        
        # 计算延迟
        latency = time.time() - start_time
        
        # 判断是否降级
        is_degraded = len(failed_queries) > 0
        degraded_reason = None
        if failed_queries:
            degraded_reason = f"部分查询失败({len(failed_queries)}/{len(self.queries)}): {', '.join(failed_queries[:3])}"
        
        logger.info(
            f"[Semantic Scholar] 完成: {successful_queries}/{len(self.queries)}个查询成功, "
            f"抓取{len(papers)}篇论文, 耗时{latency:.2f}秒"
        )
        
        return SourceResult(
            source_name=self.name, 
            papers=papers,
            is_degraded=is_degraded,
            degraded_reason=degraded_reason,
            latency=latency if Config.ENABLE_LATENCY_TRACKING else None
        )







