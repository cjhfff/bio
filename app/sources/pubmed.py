"""
PubMed 数据源
"""
import os
import datetime
import logging
from typing import Set, List
from app.models import Paper, SourceResult
from app.sources.base import BaseSource
from app.config import Config
from app.filtering import should_exclude_paper, is_recent_date

logger = logging.getLogger(__name__)

# 尝试导入可选库
try:
    from Bio import Entrez
    HAS_BIOPYTHON = True
    # 禁用 Bio.Entrez 的代理（通过设置环境变量）
    os.environ.pop('http_proxy', None)
    os.environ.pop('https_proxy', None)
    os.environ.pop('all_proxy', None)
except ImportError:
    HAS_BIOPYTHON = False
    logger.warning("biopython 未安装，PubMed 功能将不可用")


class PubMedSource(BaseSource):
    """PubMed 数据源"""
    
    def __init__(self, window_days: int = None):
        super().__init__("PubMed", window_days or Config.DEFAULT_WINDOW_DAYS)
        if HAS_BIOPYTHON:
            Entrez.email = Config.PUBMED_EMAIL
            # 确保代理被禁用
            os.environ.pop('http_proxy', None)
            os.environ.pop('https_proxy', None)
            os.environ.pop('all_proxy', None)
    
    def fetch(self, sent_ids: Set[str], exclude_keywords: List[str]) -> SourceResult:
        """从 PubMed 获取论文（优化版：支持摘要提取、豁免机制、数据漏斗）"""
        if not HAS_BIOPYTHON:
            return SourceResult(source_name=self.name, papers=[], error="biopython 未安装")
        
        # 确保代理被禁用（Bio.Entrez 使用 urllib，会读取环境变量）
        os.environ.pop('http_proxy', None)
        os.environ.pop('https_proxy', None)
        os.environ.pop('all_proxy', None)
        
        # 诊断计数器
        stat = {"total": 0, "excluded": 0, "date_filtered": 0, "duplicate": 0, "final": 0}
        
        try:
            today = datetime.date.today().strftime("%Y/%m/%d")
            start_date = (datetime.date.today() - datetime.timedelta(days=self.window_days)).strftime("%Y/%m/%d")
            
            # 构建查询（优化：支持更灵活的匹配，如"GPCR-like"、"natural biological nitrogen fixation"）
            q_nitro = '("Nitrogen Fixation"[Mesh] OR "Nitrogenase"[Mesh] OR "biological nitrogen fixation" OR "natural biological nitrogen fixation" OR rhizobia OR "root nodule" OR symbiosis OR diazotroph OR "nif genes" OR "nitrogen fixing")'
            q_signal = '("Signal Transduction"[Mesh] OR "Receptors, Cell Surface"[Mesh] OR "extracellular signal perception" OR "signal perception" OR "receptor kinase" OR "GPCR" OR "GPCR-like" OR "G-protein coupled receptor" OR "ligand binding" OR "hormone perception" OR "hormone signaling" OR "two-component system")'
            q_enzyme = '("Enzymes/chemistry"[Mesh] OR "Catalytic Domain"[Mesh] OR "enzyme mechanism" OR "cryo-EM" OR "cryo-electron microscopy" OR "crystal structure" OR "active site" OR "catalytic mechanism" OR "enzyme structure" OR "enzyme structure determination")'
            
            combined_query = f"({q_nitro} OR {q_signal} OR {q_enzyme}) AND (\"{start_date}\"[Date - Publication] : \"{today}\"[Date - Publication])"
            
            # 搜索
            handle = Entrez.esearch(db="pubmed", term=combined_query, retmax=100, retmode="xml")
            record = Entrez.read(handle)
            id_list = record.get("IdList", [])
            
            if not id_list:
                return SourceResult(source_name=self.name, papers=[])
            
            # 获取详细信息
            handle = Entrez.efetch(db="pubmed", id=",".join(id_list), rettype="abstract", retmode="xml")
            records = Entrez.read(handle)
            
            papers = []
            for article in records.get('PubmedArticle', []):
                stat["total"] += 1
                try:
                    medline_cit = article['MedlineCitation']
                    article_data = medline_cit['Article']
                    title = article_data.get('ArticleTitle', '无标题')
                    
                    # --- 核心改进：提取摘要文本 ---
                    abstract_parts = []
                    abstract_data = article_data.get('Abstract', {}).get('AbstractText', [])
                    for part in abstract_data:
                        part_text = str(part).strip()
                        if part_text:
                            abstract_parts.append(part_text)
                    abstract = " ".join(abstract_parts)
                    
                    # 提取日期与 DOI
                    final_date = self._extract_date(article, today)
                    doi = self._extract_doi(article)
                    
                    # 提取 PMID 并生成链接
                    pmid = str(medline_cit.get('PMID', ''))
                    link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
                    
                    # 构建 Paper 对象用于过滤
                    paper = Paper(
                        title=title,
                        abstract=abstract,
                        date=final_date,
                        source='PubMed',
                        doi=doi,
                        link=link
                    )
                    
                    # --- 改进：多重过滤逻辑 ---
                    # 1. 排除过滤（包含结构生物学豁免）
                    if should_exclude_paper(paper, exclude_keywords):
                        stat["excluded"] += 1
                        continue
                    
                    # 2. 日期验证
                    if not is_recent_date(paper.date, days=self.window_days):
                        stat["date_filtered"] += 1
                        continue
                    
                    # 3. 统一去重
                    item_id = self.get_item_id(paper)
                    if item_id in sent_ids:
                        stat["duplicate"] += 1
                        continue
                    
                    papers.append(paper)
                    stat["final"] += 1
                    
                except (KeyError, TypeError, IndexError) as e:
                    logger.warning(f"解析 PubMed 单条记录失败: {e}")
                    continue
            
            # 4. 输出诊断日志
            logger.info(f"PubMed 数据漏斗: {stat}")
            return SourceResult(source_name=self.name, papers=papers)
        except Exception as e:
            logger.error(f"PubMed 抓取失败: {e}", exc_info=True)
            return SourceResult(source_name=self.name, papers=[], error=str(e))
    
    def _extract_date(self, article, default_date: str) -> str:
        """提取日期（增强版：支持格式化和异常处理）"""
        try:
            medline = article['MedlineCitation']
            if 'DateCompleted' in medline:
                date_completed = medline['DateCompleted']
                year = date_completed.get('Year', '')
                month = date_completed.get('Month', '01')
                day = date_completed.get('Day', '01')
                if year:
                    # 使用 zfill 确保月份和日期为两位数
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        except (KeyError, TypeError, AttributeError):
            pass
        
        try:
            pub_date_list = article['MedlineCitation']['Article']['ArticleDate']
            if pub_date_list:  # 检查是否为空列表
                pub_date_obj = pub_date_list[0]
                year = pub_date_obj.get('Year', '')
                month = pub_date_obj.get('Month', '01')
                day = pub_date_obj.get('Day', '01')
                if year:
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        except (KeyError, IndexError, TypeError, AttributeError):
            pass
        
        return default_date
    
    def _extract_doi(self, article) -> str:
        """提取DOI"""
        try:
            article_ids = article['PubmedData']['ArticleIdList']
            for aid in article_ids:
                if aid.attributes.get('IdType') == 'doi':
                    return str(aid)
        except (KeyError, TypeError):
            pass
        return ''



