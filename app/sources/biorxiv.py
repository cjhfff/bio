"""
bioRxiv 数据源
"""
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

# 默认分页配置（向后兼容）
DEFAULT_MAX_PAGES = 5
PAGE_SIZE = 100


class BioRxivSource(BaseSource):
    """
    bioRxiv 数据源
    支持动态分页、诊断日志、豁免机制
    """
    
    def __init__(self, window_days: int = None, max_pages: int = None, 
                 enable_diagnostic: bool = None, enable_exemption: bool = None):
        super().__init__("bioRxiv", window_days or Config.DEFAULT_WINDOW_DAYS)
        # 参数化配置，支持向后兼容
        self.max_pages = max_pages if max_pages is not None else Config.BIORXIV_MAX_PAGES
        self.enable_diagnostic = enable_diagnostic if enable_diagnostic is not None else Config.ENABLE_DIAGNOSTIC
        self.enable_exemption = enable_exemption if enable_exemption is not None else Config.ENABLE_EXEMPTION
    
    def _fetch_page_with_retry(self, session: requests.Session, url: str, max_retries: int = 3) -> dict:
        """
        带重试机制的页面抓取
        
        Args:
            session: requests.Session 对象（复用连接）
            url: 请求URL
            max_retries: 最大重试次数
            
        Returns:
            解析后的JSON数据
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # 指数退避：第1次立即，第2次等2秒，第3次等4秒
                if attempt > 0:
                    wait_time = 2 ** (attempt - 1)
                    logger.warning(f"bioRxiv 请求失败，{wait_time}秒后重试（第 {attempt + 1}/{max_retries} 次）...")
                    time.sleep(wait_time)
                
                # 增加超时时间到60秒，使用会话复用连接
                response = session.get(
                    url,
                    timeout=60,  # 从30秒增加到60秒
                    proxies={'http': None, 'https': None}
                )
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.Timeout as e:
                last_error = e
                logger.warning(f"bioRxiv 请求超时（第 {attempt + 1}/{max_retries} 次）: {e}")
            except requests.exceptions.ConnectionError as e:
                last_error = e
                error_msg = str(e)
                if "RemoteDisconnected" in error_msg or "Connection aborted" in error_msg:
                    logger.warning(f"bioRxiv 连接被中断（第 {attempt + 1}/{max_retries} 次）: {error_msg[:100]}")
                else:
                    logger.warning(f"bioRxiv 连接错误（第 {attempt + 1}/{max_retries} 次）: {error_msg[:100]}")
            except requests.exceptions.HTTPError as e:
                last_error = e
                logger.warning(f"bioRxiv HTTP错误（第 {attempt + 1}/{max_retries} 次）: {e}")
            except Exception as e:
                last_error = e
                logger.warning(f"bioRxiv 请求异常（第 {attempt + 1}/{max_retries} 次）: {type(e).__name__}: {e}")
        
        # 所有重试都失败
        raise Exception(f"bioRxiv 请求失败（已重试 {max_retries} 次）: {last_error}")
    
    def fetch(self, sent_ids: Set[str], exclude_keywords: List[str]) -> SourceResult:
        """
        从 bioRxiv 获取论文（支持动态分页、诊断日志、豁免机制、重试机制）
        """
        try:
            # 只检索前一天的论文（不包括今天）
            yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            start_date = yesterday
            start_date_obj = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            
            papers = []
            all_keywords = Config.get_all_keywords()
            
            # 创建会话，复用连接（提高性能，减少连接开销）
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            # 诊断计数器
            stat = {
                "total": 0,
                "cat_match": 0,
                "kw_match": 0,
                "cat_or_kw": 0,
                "excluded": 0,
                "exempted": 0,  # 豁免数
                "date_filtered": 0,
                "duplicate": 0,
                "final": 0
            }
            
            # 动态分页抓取
            for page in range(self.max_pages):
                cursor = page * PAGE_SIZE
                url = f"https://api.biorxiv.org/details/biorxiv/{start_date}/{yesterday}/{cursor}"
                
                try:
                    # 使用带重试机制的抓取
                    json_data = self._fetch_page_with_retry(session, url, max_retries=3)
                    data = json_data.get('collection', [])
                except Exception as e:
                    logger.error(f"bioRxiv 第{page+1}页抓取失败: {e}")
                    # 如果第一页就失败，直接返回错误
                    if page == 0:
                        raise
                    # 如果不是第一页，记录错误但继续处理已获取的数据
                    break
                
                if not data:
                    logger.debug(f"bioRxiv 第{page+1}页无数据，停止抓取")
                    break
                
                # 检查时间边界（早退机制）
                oldest_date = None
                for p in data:
                    paper_date_str = p.get('date', '')
                    if paper_date_str:
                        try:
                            paper_date = datetime.datetime.strptime(paper_date_str[:10], '%Y-%m-%d').date()
                            if oldest_date is None or paper_date < oldest_date:
                                oldest_date = paper_date
                        except:
                            pass
                
                # 如果最老的论文超出窗口期，提前终止
                if oldest_date and oldest_date < start_date_obj:
                    logger.debug(f"bioRxiv 第{page+1}页最老论文日期 {oldest_date} 已超出窗口期 {start_date_obj}，提前终止")
                    # 仍然处理当前页，然后结束
                    should_break = True
                else:
                    should_break = False
                
                for p in data:
                    stat["total"] += 1
                    
                    category = p.get('category', '').lower()
                    abstract = p.get('abstract', '').lower()
                    title = p.get('title', '').lower()
                    text_to_search = title + " " + abstract
                    
                    # 检查分类
                    is_target_category = any(c in category for c in Config.TARGET_CATEGORIES)
                    if is_target_category:
                        stat["cat_match"] += 1
                    
                    # 检查关键词
                    is_kw_match = any(kw in text_to_search for kw in all_keywords)
                    if is_kw_match:
                        stat["kw_match"] += 1
                    
                    # 放宽条件：分类 OR 关键词（任一满足即可）
                    if not (is_target_category or is_kw_match):
                        continue
                    
                    stat["cat_or_kw"] += 1
                    
                    # 提取并验证日期
                    paper_date_str = p.get('date', '') or yesterday
                    # 检查日期年份是否异常（如果年份是去年但当前是年初，可能是数据源问题）
                    if paper_date_str:
                        try:
                            paper_date = datetime.datetime.strptime(paper_date_str[:10], '%Y-%m-%d').date()
                            today = datetime.date.today()
                            # 如果日期是去年但距离今天超过30天，记录警告
                            if paper_date.year < today.year and (today - paper_date).days > 30:
                                logger.warning(f"[日期异常] bioRxiv论文日期可能异常: 标题='{p.get('title', '')[:50]}...', 日期={paper_date_str}, 当前日期={today}")
                        except:
                            pass
                    
                    paper = Paper(
                        title=p.get('title', '无标题'),
                        abstract=p.get('abstract', '无摘要'),
                        date=paper_date_str,
                        source='bioRxiv',
                        doi=p.get('doi', ''),
                        link=''
                    )
                    
                    # 豁免机制：检查是否包含结构生物学关键词
                    is_structure_paper = False
                    if self.enable_exemption:
                        is_structure_paper = any(sk in text_to_search for sk in Config.STRUCTURE_KEYWORDS)
                    
                    # 排除过滤（结构生物学论文豁免）
                    if should_exclude_paper(paper, exclude_keywords):
                        if is_structure_paper:
                            stat["exempted"] += 1
                            logger.debug(f"豁免论文：{paper.title[:50]}...")
                        else:
                            stat["excluded"] += 1
                            continue
                    
                    # 日期过滤
                    if not is_recent_date(paper.date, days=self.window_days):
                        stat["date_filtered"] += 1
                        continue
                    
                    # 去重检查
                    item_id = self.get_item_id(paper)
                    if item_id and item_id in sent_ids:
                        stat["duplicate"] += 1
                        continue
                    
                    papers.append(paper)
                    stat["final"] += 1
                
                logger.debug(f"bioRxiv 第{page+1}页抓取完成，累计 {len(papers)} 条")
                
                # 请求之间添加短暂延迟，避免请求过快导致连接被中断
                if page < self.max_pages - 1:  # 最后一页不需要延迟
                    time.sleep(0.5)  # 延迟0.5秒
                
                # 如果返回数据少于100条，说明已经是最后一页
                if len(data) < PAGE_SIZE:
                    logger.debug(f"bioRxiv 第{page+1}页数据不足100条，停止抓取")
                    break
                
                # 早退机制
                if should_break:
                    break
            
            # 输出诊断日志
            if self.enable_diagnostic:
                import json
                logger.info(f"bioRxiv 数据漏斗分析: {json.dumps(stat, ensure_ascii=False)}")
                logger.info(f"  - 总计: {stat['total']} 条")
                logger.info(f"  - 分类匹配: {stat['cat_match']} 条 ({stat['cat_match']*100//max(stat['total'],1)}%)")
                logger.info(f"  - 关键词匹配: {stat['kw_match']} 条 ({stat['kw_match']*100//max(stat['total'],1)}%)")
                logger.info(f"  - 初筛通过: {stat['cat_or_kw']} 条")
                logger.info(f"  - 排除词过滤: {stat['excluded']} 条")
                logger.info(f"  - 豁免通过: {stat['exempted']} 条")
                logger.info(f"  - 日期过滤: {stat['date_filtered']} 条")
                logger.info(f"  - 重复过滤: {stat['duplicate']} 条")
                logger.info(f"  - 最终入选: {stat['final']} 条")
            
            logger.info(f"bioRxiv 共抓取 {len(papers)} 条论文")
            return SourceResult(source_name=self.name, papers=papers)
        except Exception as e:
            logger.error(f"bioRxiv 抓取失败: {e}", exc_info=True)
            return SourceResult(source_name=self.name, papers=[], error=str(e))
        finally:
            # 确保会话被关闭
            if 'session' in locals():
                try:
                    session.close()
                except:
                    pass




