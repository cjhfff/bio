"""GitHub 工具数据源"""
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


class GitHubSource(BaseSource):
    """GitHub 工具数据源"""
    
    def __init__(self, window_days: int = None):
        super().__init__("GitHub", window_days or Config.DEFAULT_WINDOW_DAYS)
        # 扩展查询词，使用更通用的词
        self.queries = [
            # 固氮相关
            "nitrogen+fixation",
            "nitrogenase",
            "rhizobium+symbiosis",
            # 信号转导相关
            "signal+transduction+biology",
            "receptor+kinase+plant",
            "phosphorylation+signaling",
            # 植物免疫受体相关（新增）
            "plant+immune+receptor",
            "receptor+ligand+interaction+plant",
            "nlr+plant",
            "resistosome+structure",
            # 酶结构相关
            "enzyme+structure",
            "protein+structure+cryo-EM",
            "crystal+structure+enzyme",
            # 通用生物工具
            "bioinformatics+protein",
            "structural+biology+tool",
        ]
    
    def fetch(self, sent_ids: Set[str], exclude_keywords: List[str]) -> SourceResult:
        papers = []
        all_keywords = Config.get_all_keywords()
        target_categories = [c.lower() for c in Config.TARGET_CATEGORIES]
        
        # 限流统计
        rate_limit_errors = 0
        max_rate_limit_errors = 3  # 如果连续3次限流，停止查询
        
        for query_idx, query in enumerate(self.queries):
            # 在请求之间添加延迟，避免触发限流
            if query_idx > 0:
                time.sleep(1)  # 每个查询之间延迟1秒
            
            # 如果限流错误过多，跳过剩余查询
            if rate_limit_errors >= max_rate_limit_errors:
                logger.warning(f"GitHub API 限流错误过多（{rate_limit_errors}次），跳过剩余 {len(self.queries) - query_idx} 个查询")
                break
            
            max_retries = 3
            retry_delay = 5  # 初始重试延迟（秒）
            
            for attempt in range(max_retries):
                try:
                    # 增加每个查询的结果数：3 -> 5
                    url = f"https://api.github.com/search/repositories?q={query}&sort=updated&order=desc&per_page=5"
                    response = requests.get(
                        url,
                        timeout=15,
                        proxies={'http': None, 'https': None},
                        headers={'Accept': 'application/vnd.github.v3+json'}
                    )
                    
                    # 检查限流错误
                    if response.status_code == 403:
                        error_msg = str(response.text)
                        if 'rate limit' in error_msg.lower():
                            rate_limit_errors += 1
                            if attempt < max_retries - 1:
                                # 指数退避：5秒、10秒、20秒
                                wait_time = retry_delay * (2 ** attempt)
                                logger.warning(f"GitHub API 限流，等待 {wait_time} 秒后重试（第 {attempt + 1}/{max_retries} 次）...")
                                time.sleep(wait_time)
                                continue
                            else:
                                logger.warning(f"GitHub 查询 '{query}' 达到最大重试次数，跳过")
                                break
                    
                    response.raise_for_status()
                    items = response.json().get('items', [])
                    
                    # 成功获取数据，重置限流错误计数
                    rate_limit_errors = 0
                    
                    # 处理返回的items
                    for item in items:
                        title = item.get('name', '')
                        description = item.get('description', '') or ''
                        text_lower = (title + " " + description).lower()
                        
                        # 放宽过滤：关键词匹配 OR 分类匹配
                        has_keyword = any(kw in text_lower for kw in all_keywords)
                        has_category = any(cat in text_lower for cat in target_categories)
                        
                        # 还可以检查 topics
                        topics = item.get('topics', []) or []
                        topics_lower = ' '.join(topics).lower()
                        has_topic = any(kw in topics_lower for kw in all_keywords)
                        
                        if has_keyword or has_category or has_topic:
                            paper = Paper(
                                title=f"GitHub工具: {title}",
                                abstract=description,
                                date=self._extract_date(item),
                                source='GitHub',
                                doi='',
                                link=item.get('html_url', '')
                            )
                            
                            if should_exclude_paper(paper, exclude_keywords):
                                continue
                            if not is_recent_date(paper.date, days=self.window_days):
                                continue
                            
                            item_id = self.get_item_id(paper)
                            if item_id and item_id not in sent_ids:
                                papers.append(paper)
                    
                    # 成功处理，跳出重试循环
                    break
                    
                except requests.exceptions.HTTPError as e:
                    if e.response and e.response.status_code == 403:
                        # 403错误已在上面处理
                        continue
                    else:
                        logger.warning(f"GitHub 查询 '{query}' HTTP错误: {e}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay * (2 ** attempt))
                            continue
                        break
                except Exception as e:
                    logger.warning(f"GitHub 查询 '{query}' 失败（第 {attempt + 1}/{max_retries} 次）: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (2 ** attempt))
                        continue
                    break
        
        logger.info(f"GitHub 共抓取 {len(papers)} 条仓库")
        return SourceResult(source_name=self.name, papers=papers)
    
    def _extract_date(self, item) -> str:
        """提取更新日期"""
        updated_date = item.get('updated_at', '')
        if updated_date:
            try:
                dt = datetime.datetime.fromisoformat(updated_date.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d')
            except:
                pass
        return datetime.date.today().strftime('%Y-%m-%d')




