"""RSS 数据源"""
import datetime
import requests
import logging
from typing import Set, List
from backend.models import Paper, SourceResult
from backend.sources.base import BaseSource
from backend.core.config import Config
from backend.core.filtering import should_exclude_paper, is_recent_date

logger = logging.getLogger(__name__)

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False


class RSSSource(BaseSource):
    """RSS 顶级期刊数据源"""
    
    def __init__(self, window_days: int = None):
        super().__init__("RSS_TopJournal", window_days or Config.DEFAULT_WINDOW_DAYS)
        # 扩展 RSS 源列表
        self.feeds = [
            "https://www.nature.com/nplants.rss",      # Nature Plants
            "https://www.nature.com/nature.rss",       # Nature Main
            "https://www.nature.com/nchembio.rss",     # Nature Chemical Biology
            "https://www.nature.com/nsmb.rss",         # Nature Structural & Molecular Biology
            "https://science.sciencemag.org/rss/express.xml",  # Science First Release
            "https://www.cell.com/cell/rss",           # Cell
            "https://www.cell.com/molecular-cell/rss", # Molecular Cell
        ]
    
    def _extract_doi_from_entry(self, entry) -> str:
        """
        从 RSS entry 中提取 DOI
        
        优先级：
        1. entry.id 字段（可能包含 doi.org 链接或 doi: 前缀）
        2. entry.doi 字段（部分 feed 提供）
        3. entry.link 字段（可能包含 doi.org 链接）
        
        Args:
            entry: feedparser 解析的 entry 对象
        
        Returns:
            str: 标准化的 DOI（不含前缀），未找到则返回空字符串
        """
        # 检查 entry.id
        if hasattr(entry, 'id') and entry.id:
            entry_id = entry.id
            # 检查是否包含 doi.org
            if 'doi.org/' in entry_id:
                doi = entry_id.split('doi.org/')[-1]
                logger.debug(f"[DOI提取] 从 entry.id 提取: {doi}")
                return doi
            # 检查是否以 doi: 开头
            if entry_id.startswith('doi:'):
                doi = entry_id.replace('doi:', '').strip()
                logger.debug(f"[DOI提取] 从 entry.id (doi:前缀) 提取: {doi}")
                return doi
        
        # 检查 entry.doi 字段
        if hasattr(entry, 'doi') and entry.doi:
            doi = entry.doi
            # 清理可能的前缀
            doi = doi.replace('https://doi.org/', '').replace('http://doi.org/', '').replace('doi:', '').strip()
            if doi:
                logger.debug(f"[DOI提取] 从 entry.doi 提取: {doi}")
                return doi
        
        # 检查 entry.link
        if hasattr(entry, 'link') and entry.link:
            if 'doi.org/' in entry.link:
                doi = entry.link.split('doi.org/')[-1]
                logger.debug(f"[DOI提取] 从 entry.link 提取: {doi}")
                return doi
        
        return ''
    
    def fetch(self, sent_ids: Set[str], exclude_keywords: List[str]) -> SourceResult:
        if not HAS_FEEDPARSER:
            return SourceResult(source_name=self.name, papers=[], error="feedparser 未安装")
        
        papers = []
        all_keywords = Config.get_all_keywords()
        target_categories = [c.lower() for c in Config.TARGET_CATEGORIES]
        
        # 获取差异化过滤策略配置
        broad_keywords = [kw.lower() for kw in Config.BROAD_KEYWORDS]
        top_tier_domains = Config.TOP_TIER_DOMAINS
        
        for url in self.feeds:
            try:
                # 判断当前源是否为顶级期刊
                is_top_tier = any(domain in url for domain in top_tier_domains)
                
                if is_top_tier:
                    # 提取期刊域名用于日志
                    matched_domain = next((domain for domain in top_tier_domains if domain in url), "unknown")
                    logger.info(f"[顶刊源识别] URL={url}, 期刊域名={matched_domain}")
                
                rss_response = requests.get(url, timeout=30, proxies={'http': None, 'https': None})
                feed = feedparser.parse(rss_response.content)
                
                # 移除数量限制，处理所有条目以确保不遗漏
                for entry in feed.entries:
                    title_lower = entry.title.lower()
                    summary_lower = entry.get('summary', '').lower()
                    text_to_search = title_lower + " " + summary_lower
                    
                    # 差异化过滤策略
                    matched_keyword = None
                    if is_top_tier:
                        # 顶刊：宽松过滤，只需包含领域大词即可
                        for bk in broad_keywords:
                            if bk in text_to_search:
                                matched_keyword = bk
                                is_relevant = True
                                logger.debug(f"[顶刊白名单] 通过领域大词: 关键词='{matched_keyword}', 标题='{entry.title[:50]}...'")
                                break
                        else:
                            is_relevant = False
                    else:
                        # 普通源：严格过滤，必须命中精确关键词或目标分类
                        has_keyword = any(k in text_to_search for k in all_keywords)
                        has_category = any(cat in text_to_search for cat in target_categories)
                        is_relevant = has_keyword or has_category
                    
                    if is_relevant:
                        # 提取 DOI
                        doi = self._extract_doi_from_entry(entry)
                        
                        paper = Paper(
                            title=entry.title,
                            abstract=entry.get('summary', ''),
                            date=entry.get('published', '') or entry.get('updated', ''),
                            source='RSS_TopJournal',
                            doi=doi,
                            link=entry.link
                        )
                        
                        # 排除词检查
                        if should_exclude_paper(paper, exclude_keywords):
                            # 记录排除词拦截日志
                            text_for_check = (paper.title + " " + paper.abstract).lower()
                            matched_exclude = next((ex for ex in exclude_keywords if ex in text_for_check), "unknown")
                            logger.debug(f"[排除词拦截] 命中词='{matched_exclude}', 来源={paper.source}, 标题='{paper.title[:50]}...'")
                            continue
                        
                        # 日期验证（传递 is_top_tier 参数启用容错机制）
                        if not is_recent_date(paper.date, days=self.window_days, is_top_tier=is_top_tier):
                            continue
                        
                        item_id = self.get_item_id(paper)
                        if item_id and item_id not in sent_ids:
                            papers.append(paper)
            except Exception as e:
                logger.warning(f"RSS 源 {url} 抓取失败: {e}")
        
        logger.info(f"RSS 共抓取 {len(papers)} 条论文")
        return SourceResult(source_name=self.name, papers=papers)







