"""Science News (EurekAlert) 数据源(支持User-Agent伪装和部分容错)"""
import datetime
import requests
import logging
import time
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


class ScienceNewsSource(BaseSource):
    """EurekAlert 科学新闻数据源"""
    
    def __init__(self, window_days: int = None):
        super().__init__("ScienceNews", window_days or Config.DEFAULT_WINDOW_DAYS)
        self.news_urls = [
            "https://www.eurekalert.org/rss/agriculture.xml",
            "https://www.eurekalert.org/rss/biology.xml"
        ]
    
    def fetch(self, sent_ids: Set[str], exclude_keywords: List[str]) -> SourceResult:
        if not HAS_FEEDPARSER:
            return SourceResult(source_name=self.name, papers=[], error="feedparser 未安装")
        
        papers = []
        all_keywords = Config.get_all_keywords()
        
        start_time = time.time()
        failed_urls = []
        successful_urls = 0
        
        # User-Agent伪装,避免被识别为爬虫
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # 逐个RSS源独立处理,一个失败不影响其他
        for url in self.news_urls:
            try:
                rss_response = requests.get(
                    url, 
                    headers=headers,
                    timeout=30, 
                    proxies={'http': None, 'https': None}
                )
                rss_response.raise_for_status()  # 检查HTTP状态码
                
                feed = feedparser.parse(rss_response.content)
                
                # 检查feed是否有效
                if not hasattr(feed, 'entries') or not feed.entries:
                    logger.warning(f"[ScienceNews] RSS源 {url} 返回空数据")
                    failed_urls.append(url)
                    continue
                
                for entry in feed.entries[:3]:
                    try:
                        title_lower = entry.title.lower()
                        summary_lower = entry.get('summary', '').lower()
                        
                        if any(k in title_lower or k in summary_lower for k in all_keywords):
                            paper = Paper(
                                title=entry.title,
                                abstract=entry.get('summary', ''),
                                date=entry.get('published', '') or entry.get('updated', ''),
                                source='ScienceNews',
                                doi='',
                                link=entry.link
                            )
                            
                            if should_exclude_paper(paper, exclude_keywords):
                                continue
                            if not is_recent_date(paper.date, days=self.window_days):
                                continue
                            
                            item_id = self.get_item_id(paper)
                            if item_id and item_id not in sent_ids:
                                papers.append(paper)
                    except Exception as e:
                        logger.debug(f"[ScienceNews] 处理单条新闻失败: {e}")
                        continue
                
                successful_urls += 1
                logger.info(f"[ScienceNews] RSS源 {url} 成功")
                
            except requests.exceptions.Timeout:
                logger.warning(f"[ScienceNews] RSS源 {url} 超时")
                failed_urls.append(url)
            except requests.exceptions.RequestException as e:
                logger.warning(f"[ScienceNews] RSS源 {url} 请求失败: {e}")
                failed_urls.append(url)
            except Exception as e:
                logger.warning(f"[ScienceNews] RSS源 {url} 处理异常: {e}")
                failed_urls.append(url)
        
        # 计算延迟
        latency = time.time() - start_time
        
        # 判断是否降级
        is_degraded = len(failed_urls) > 0
        degraded_reason = None
        error = None
        
        if successful_urls == 0:
            # 全部失败
            error = f"所有RSS源均失败({len(failed_urls)}/{len(self.news_urls)})"
            degraded_reason = error
        elif failed_urls:
            # 部分失败
            degraded_reason = f"部分RSS源失败({len(failed_urls)}/{len(self.news_urls)}): {', '.join([u.split('/')[-1] for u in failed_urls])}"
        
        logger.info(
            f"[ScienceNews] 完成: {successful_urls}/{len(self.news_urls)}个RSS源成功, "
            f"抓取{len(papers)}篇新闻, 耗时{latency:.2f}秒"
        )
        
        return SourceResult(
            source_name=self.name, 
            papers=papers,
            error=error,
            is_degraded=is_degraded,
            degraded_reason=degraded_reason,
            latency=latency if Config.ENABLE_LATENCY_TRACKING else None
        )







