"""
数据源基类
"""
from abc import ABC, abstractmethod
from typing import List
from backend.models import Paper, SourceResult
from backend.deduplication import get_item_id


class BaseSource(ABC):
    """数据源基类"""
    
    def __init__(self, name: str, window_days: int = 7):
        self.name = name
        self.window_days = window_days
    
    @abstractmethod
    def fetch(self, sent_ids: set, exclude_keywords: list) -> SourceResult:
        """
        抓取数据
        
        Args:
            sent_ids: 已推送的ID集合（用于去重）
            exclude_keywords: 排除关键词列表
            
        Returns:
            SourceResult
        """
        pass
    
    def _normalize_link(self, link: str) -> str:
        """
        标准化链接，用于提高去重稳定性
        
        已废弃：请使用 app.deduplication.normalize_link
        
        Args:
            link: 原始链接
        
        Returns:
            str: 标准化后的链接
        """
        from backend.deduplication import normalize_link
        return normalize_link(link)
    
    def _generate_link_hash(self, link: str) -> str:
        """
        生成链接的 SHA256 哈希值（截取前 16 位）
        
        已废弃：请使用 app.deduplication.generate_link_hash
        
        Args:
            link: 链接
        
        Returns:
            str: 哈希值
        """
        from backend.deduplication import generate_link_hash
        return generate_link_hash(link)
    
    def get_item_id(self, paper: Paper) -> str:
        """
        获取论文的唯一标识符（增强版：支持链接哈希去重）
        
        已迁移：调用 app.deduplication.get_item_id 统一处理
        
        Args:
            paper: 论文对象
        
        Returns:
            str: 唯一标识符，如果无法生成则返回 None
        """
        return get_item_id(paper)







