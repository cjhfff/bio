"""
数据源抓取模块
"""
from .base import BaseSource
from .biorxiv import BioRxivSource
from .pubmed import PubMedSource
from .rss import RSSSource
from .europepmc import EuropePMCSource
from .sciencenews import ScienceNewsSource
from .github import GitHubSource
from .semanticscholar import SemanticScholarSource

__all__ = [
    'BaseSource',
    'BioRxivSource',
    'PubMedSource',
    'RSSSource',
    'EuropePMCSource',
    'ScienceNewsSource',
    'GitHubSource',
    'SemanticScholarSource',
]
