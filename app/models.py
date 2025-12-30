"""
数据模型定义
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import date


@dataclass
class Paper:
    """论文数据模型"""
    title: str
    abstract: str
    date: str  # YYYY-MM-DD
    source: str  # 数据源名称
    doi: str = ""
    link: str = ""
    citation_count: int = 0
    influential_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'title': self.title,
            'abstract': self.abstract,
            'date': self.date,
            'doi': self.doi,
            'link': self.link,
            'source': self.source,
            'citation_count': self.citation_count,
            'influential_count': self.influential_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Paper':
        """从字典创建"""
        return cls(
            title=data.get('title', ''),
            abstract=data.get('abstract', ''),
            date=data.get('date', ''),
            source=data.get('source', ''),
            doi=data.get('doi', ''),
            link=data.get('link', ''),
            citation_count=data.get('citation_count', 0),
            influential_count=data.get('influential_count', 0),
        )


@dataclass
class ScoreReason:
    """评分原因（可解释性）"""
    category: str  # 如 "keyword_match", "top_journal", "citation", "freshness"
    points: float
    description: str  # 如 "命中关键词: nitrogenase (+8分)"


@dataclass
class ScoredPaper:
    """带评分的论文"""
    paper: Paper
    score: float
    reasons: List[ScoreReason] = field(default_factory=list)


@dataclass
class SourceResult:
    """数据源抓取结果"""
    source_name: str
    papers: List[Paper]
    error: Optional[str] = None
    is_degraded: bool = False  # 数据源是否处于降级状态
    degraded_reason: Optional[str] = None  # 降级原因描述
    latency: Optional[float] = None  # 数据源响应时间(秒)
    
    def success(self) -> bool:
        return self.error is None







