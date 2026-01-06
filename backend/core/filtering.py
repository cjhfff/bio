"""
过滤逻辑：排除词、领域判定等（增强版：支持结构生物学豁免权重计分）
"""
import logging
import re
from typing import List
from backend.models import Paper
from backend.core.config import Config

logger = logging.getLogger(__name__)


def calculate_exemption_score(paper: Paper) -> float:
    """
    计算论文的豁免权重分数
    
    权重规则:
    - Title包含结构关键词: +10
    - Abstract包含结构关键词: +3
    - 核心动词紧跟结构词: +5
    - 结构词在Abstract前50%位置: +2
    """
    score = 0
    title_lower = paper.title.lower()
    abstract_lower = (paper.abstract or "").lower()
    
    structure_keywords = [kw.lower() for kw in Config.STRUCTURE_KEYWORDS]
    core_verbs = [verb.lower() for verb in Config.EXEMPTION_CORE_VERBS]
    
    # 检查Title
    for struct_kw in structure_keywords:
        if struct_kw in title_lower:
            score += 10
            logger.debug(f"[豁免计分] Title匹配 '{struct_kw}': +10分")
    
    # 检查Abstract
    if abstract_lower:
        abstract_len = len(abstract_lower)
        for struct_kw in structure_keywords:
            if struct_kw in abstract_lower:
                score += 3
                logger.debug(f"[豁免计分] Abstract包含 '{struct_kw}': +3分")
                
                # 检查核心动词
                for verb in core_verbs:
                    # 构造模式: "verb + structure_keyword" 或 "verb structure_keyword of"
                    pattern1 = f"{verb}.*{struct_kw}"
                    pattern2 = f"{struct_kw}.*{verb}"
                    if re.search(pattern1, abstract_lower) or re.search(pattern2, abstract_lower):
                        score += 5
                        logger.debug(f"[豁免计分] 核心动词匹配 '{verb}' + '{struct_kw}': +5分")
                        break
                
                # 检查位置权重
                pos = abstract_lower.find(struct_kw)
                if pos >= 0 and pos < abstract_len / 2:
                    score += 2
                    logger.debug(f"[豁免计分] '{struct_kw}'在前50%位置: +2分")
    
    return score


def should_exclude_paper(paper: Paper, exclude_keywords: List[str]) -> bool:
    """检查论文是否应该被排除（支持结构生物学豁免权重计分）"""
    text_to_search = (paper.title + " " + (paper.abstract or "")).lower()
    
    # 检查是否命中排除词
    has_exclude_keyword = any(ex_keyword in text_to_search for ex_keyword in exclude_keywords)
    
    if has_exclude_keyword:
        # 使用新版权重计分机制或旧版布尔判断
        if Config.ENABLE_WEIGHT_BASED_EXEMPTION:
            # 计算豁免分数
            exemption_score = calculate_exemption_score(paper)
            
            # 检查是否包含目标关键词
            all_keywords = Config.get_all_keywords()
            has_target_keyword = any(kw.lower() in text_to_search for kw in all_keywords)
            
            # 判定逻辑: exemption_score >= 阈值 且 包含目标关键词
            if exemption_score >= Config.EXEMPTION_SCORE_THRESHOLD and has_target_keyword:
                logger.info(
                    f"[豁免通过] 论文包含排除词但保留: "
                    f"title='{paper.title[:50]}...', exemption_score={exemption_score}"
                )
                return False  # 豁免,不排除
            else:
                logger.debug(
                    f"[正常排除] 豁免分数不足: "
                    f"exemption_score={exemption_score}, threshold={Config.EXEMPTION_SCORE_THRESHOLD}"
                )
                return True  # 正常排除
        else:
            # 旧版布尔判断机制(向后兼容)
            has_struct_keyword = any(
                struct_kw in text_to_search 
                for struct_kw in Config.STRUCTURE_KEYWORDS
            )
            
            if has_struct_keyword:
                logger.debug(
                    f"[结构豁免] 论文包含排除词但保留: title='{paper.title[:50]}...'"
                )
                return False  # 不排除
            
            return True  # 正常排除
    
    return False  # 无排除词


def is_recent_date(date_str: str, days: int = 7, is_top_tier: bool = False) -> bool:
    """
    检查日期是否在最近 N 天内（增强版：支持时区容错和顶刊容错）
    
    Args:
        date_str: 日期字符串
        days: 时间窗口（天）
        is_top_tier: 是否为顶刊论文（如果是，启用日期容错机制）
    
    Returns:
        bool: 日期是否有效
    """
    if not date_str or date_str == '' or date_str == '日期未知':
        # 对于顶刊，缺失日期也默认信任
        if is_top_tier:
            from backend.core.config import Config
            if Config.ENABLE_TOP_TIER_DATE_TOLERANCE:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"[顶刊日期容错] 缺失日期但保留")
                return True
        return False
    
    try:
        import datetime
        from email.utils import parsedate_to_datetime
        
        paper_date = None
        
        # 优先处理 RSS 格式日期（RFC 822）
        if 'GMT' in date_str or 'UTC' in date_str or (',' in date_str and len(date_str) > 10):
            try:
                paper_date = parsedate_to_datetime(date_str).date()
            except:
                pass
        
        # 如果 RSS 格式解析失败，尝试标准格式
        if paper_date is None:
            date_part = date_str[:10] if len(date_str) >= 10 else date_str
            try:
                if '-' in date_part:
                    paper_date = datetime.datetime.strptime(date_part, '%Y-%m-%d').date()
                elif '/' in date_part:
                    paper_date = datetime.datetime.strptime(date_part, '%Y/%m/%d').date()
            except:
                pass
        
        # 如果解析失败，检查是否为顶刊并启用容错
        if paper_date is None:
            if is_top_tier:
                from backend.core.config import Config
                if Config.ENABLE_TOP_TIER_DATE_TOLERANCE:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"[顶刊日期容错] 解析失败但保留: 原始日期='{date_str[:50]}'")
                    return True
            return False
        
        today = datetime.date.today()
        days_diff = (today - paper_date).days
        
        # 只允许前一天的日期（days_diff == 1 表示昨天）
        # 允许 0 <= days_diff <= 1 以处理时区差异，但主要目标是前一天
        return days_diff == 1
    except Exception:
        # 异常情况，检查是否为顶刊
        if is_top_tier:
            from backend.core.config import Config
            if Config.ENABLE_TOP_TIER_DATE_TOLERANCE:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"[顶刊日期容错] 异常但保留: 原始日期='{date_str[:50]}'")
                return True
        return False


def filter_papers(papers: List[Paper], exclude_keywords: List[str], window_days: int = 7) -> List[Paper]:
    """批量过滤论文"""
    filtered = []
    for paper in papers:
        if should_exclude_paper(paper, exclude_keywords):
            continue
        if not is_recent_date(paper.date, days=window_days):
            continue
        filtered.append(paper)
    return filtered







