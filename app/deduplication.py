"""
去重逻辑统一模块(支持标题指纹去重)

该模块提供统一的论文去重ID生成逻辑，避免代码重复。
所有需要生成去重ID的模块都应该调用此模块的函数。
"""
import hashlib
import logging
import re
from typing import Optional
from app.models import Paper
from app.config import Config

logger = logging.getLogger(__name__)


def normalize_link(link: str) -> str:
    """
    标准化链接，用于提高去重稳定性
    
    标准化规则：
    1. 统一协议：HTTP -> HTTPS
    2. 域名小写化
    3. 移除尾部斜杠
    4. 移除追踪参数（UTM、会话 ID 等）
    
    Args:
        link: 原始链接
    
    Returns:
        str: 标准化后的链接
    """
    if not link:
        return ""
    
    try:
        from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
        
        # 解析 URL
        parsed = urlparse(link)
        
        # 1. 统一协议：HTTP -> HTTPS
        scheme = 'https' if parsed.scheme == 'http' else parsed.scheme
        
        # 2. 域名小写化
        netloc = parsed.netloc.lower()
        
        # 3. 移除尾部斜杠
        path = parsed.path.rstrip('/')
        
        # 4. 移除追踪参数（UTM、会话 ID 等）
        if parsed.query:
            params = parse_qs(parsed.query)
            # 移除常见追踪参数
            tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                               'fbclid', 'gclid', 'ref', 'source', 'from']
            cleaned_params = {k: v for k, v in params.items() if k not in tracking_params}
            
            # 重新构建查询字符串（按字母顺序排序以保证一致性）
            if cleaned_params:
                query = urlencode(sorted(cleaned_params.items()))
            else:
                query = ''
        else:
            query = ''
        
        # 重新构建 URL
        normalized = urlunparse((scheme, netloc, path, '', query, ''))
        return normalized
    except Exception:
        # 解析失败，返回原始链接
        return link


def generate_link_hash(link: str) -> str:
    """
    生成链接的 SHA256 哈希值（截取前 16 位）
    
    Args:
        link: 链接
    
    Returns:
        str: 哈希值（16位十六进制字符串）
    """
    normalized = normalize_link(link)
    hash_obj = hashlib.sha256(normalized.encode('utf-8'))
    return hash_obj.hexdigest()[:16]


def generate_title_fingerprint(title: str) -> str:
    """
    生成标题指纹(用于预印本转正识别)
    
    标准化规则:
    1. 转小写
    2. 希腊字母映射为英文名称
    3. 移除所有非字母数字字符(包括空格、标点等)
    4. SHA256哈希后截取16位
    
    示例:
        "Cryo-EM structure of α-subunit" -> "cryoemstructureofalphasubunit" -> "a3f5c8..."
    
    Args:
        title: 论文标题
    
    Returns:
        str: 16位指纹哈希值
    """
    if not title:
        return ""
    
    # 步骤1: 转小写
    normalized = title.lower()
    
    # 步骤2: 希腊字母映射
    greek_map = {
        'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta', 'ε': 'epsilon',
        'ζ': 'zeta', 'η': 'eta', 'θ': 'theta', 'ι': 'iota', 'κ': 'kappa',
        'λ': 'lambda', 'μ': 'mu', 'ν': 'nu', 'ξ': 'xi', 'ο': 'omicron',
        'π': 'pi', 'ρ': 'rho', 'σ': 'sigma', 'τ': 'tau', 'υ': 'upsilon',
        'φ': 'phi', 'χ': 'chi', 'ψ': 'psi', 'ω': 'omega'
    }
    for greek, english in greek_map.items():
        normalized = normalized.replace(greek, english)
    
    # 步骤3: 移除所有非字母数字字符 (\W+ 匹配所有非字母数字和下划线)
    normalized = re.sub(r'\W+', '', normalized)
    
    # 步骤4: SHA256哈希并截取16位
    hash_obj = hashlib.sha256(normalized.encode('utf-8'))
    fingerprint = hash_obj.hexdigest()[:16]
    
    logger.debug(f"[标题指纹] '{title[:50]}...' -> '{normalized[:30]}...' -> {fingerprint}")
    
    return fingerprint


def get_item_id(paper: Paper) -> Optional[str]:
    """
    获取论文的唯一标识符（增强版：支持标题指纹去重）
    
    优先级：
    1. DOI 标识
    2. 标题指纹（启用 ENABLE_TITLE_FINGERPRINT_DEDUP 时）
    3. 链接哈希（启用 ENABLE_LINK_HASH_DEDUP 时）
    4. 链接原始值
    5. 标题+来源
    
    Args:
        paper: 论文对象
    
    Returns:
        str: 唯一标识符，如果无法生成则返回 None
    """
    # 优先级1: DOI
    if paper.doi:
        doi_clean = paper.doi.replace('https://doi.org/', '').replace('http://doi.org/', '').replace('doi:', '').strip()
        if doi_clean:
            item_id = f"DOI:{doi_clean}"
            logger.debug(f"[去重 ID] 类型=DOI, ID={item_id[:50]}, 标题='{paper.title[:50]}...'")
            return item_id
    
    # 优先级2: 标题指纹（用于预印本转正识别）
    if Config.ENABLE_TITLE_FINGERPRINT_DEDUP and paper.title:
        fingerprint = generate_title_fingerprint(paper.title)
        if fingerprint:
            item_id = f"TITLE_FP:{fingerprint}"
            logger.debug(f"[去重 ID] 类型=TITLE_FP, ID={item_id}, 标题='{paper.title[:50]}...'")
            return item_id
    
    # 优先级3: 链接（支持哈希或原始值）
    if paper.link:
        if Config.ENABLE_LINK_HASH_DEDUP:
            # 使用哈希去重
            link_hash = generate_link_hash(paper.link)
            item_id = f"LINK_HASH:{link_hash}"
            logger.debug(f"[去重 ID] 类型=LINK_HASH, ID={item_id}, 标题='{paper.title[:50]}...'")
            return item_id
        else:
            # 使用原始链接
            item_id = f"LINK:{paper.link}"
            logger.debug(f"[去重 ID] 类型=LINK, ID={item_id[:50]}, 标题='{paper.title[:50]}...'")
            return item_id
    
    # 优先级4: 标题+来源（兼容性处理）
    if paper.title:
        # 使用标题哈希以提高稳定性
        title_hash = hashlib.sha256(paper.title.encode('utf-8')).hexdigest()[:16]
        if paper.source:
            item_id = f"TITLE:{paper.source}:{title_hash}"
        else:
            item_id = f"TITLE:{title_hash}"
        logger.debug(f"[去重 ID] 类型=TITLE, ID={item_id}, 标题='{paper.title[:50]}...'")
        return item_id
    
    logger.error(f"[去重 ID] 无法生成 ID: DOI/Link/Title 均为空")
    return None
