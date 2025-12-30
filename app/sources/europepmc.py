"""Europe PMC 数据源"""
import datetime
import requests
import logging
from typing import Set, List
from app.models import Paper, SourceResult
from app.sources.base import BaseSource
from app.config import Config
from app.filtering import should_exclude_paper, is_recent_date

logger = logging.getLogger(__name__)


class EuropePMCSource(BaseSource):
    """Europe PMC 数据源（默认1天窗口）"""
    
    def __init__(self, window_days: int = None):
        super().__init__("EuropePMC", window_days or Config.EUROPEPMC_WINDOW_DAYS)
    
    def fetch(self, sent_ids: Set[str], exclude_keywords: List[str]) -> SourceResult:
        try:
            today = datetime.date.today().strftime("%Y-%m-%d")
            start_date = (datetime.date.today() - datetime.timedelta(days=self.window_days)).strftime("%Y-%m-%d")
            
            # 优化查询：使用更灵活的关键词匹配（去掉部分引号，允许更宽松的匹配）
            # 固氮相关
            q_nitro = '(nitrogen fixation OR biological nitrogen fixation OR natural biological nitrogen fixation OR nitrogenase OR rhizobia OR root nodule OR symbiosis OR diazotroph OR nif genes OR nitrogen fixing)'
            # 信号转导相关
            q_signal = '(extracellular signal OR signal perception OR signal transduction OR receptor kinase OR receptor-like kinase OR G-protein coupled receptor OR GPCR OR ligand binding OR ligand recognition OR hormone perception OR hormone signaling OR phosphorylation cascade OR signaling pathway OR two-component system OR histidine kinase)'
            # 酶结构相关（放宽匹配，使用OR连接关键词）
            q_enzyme = '(enzyme structure OR enzyme mechanism OR catalytic mechanism OR active site OR catalytic site OR allosteric regulation OR allosteric site OR enzyme kinetics OR cryo-EM OR cryo-electron microscopy OR crystal structure OR X-ray crystallography OR substrate specificity OR enzyme catalysis OR catalytic domain OR enzyme structure determination OR protein structure OR molecular structure OR structural biology)'
            
            # 构建查询（使用OR连接三个方向，更宽松）
            query = f'FIRST_PDATE:[{start_date} TO {today}] AND ({q_nitro} OR {q_signal} OR {q_enzyme})'
            url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={query}&format=json&pageSize=50"
            
            # 添加调试日志
            logger.debug(f"EuropePMC 查询URL: {url}")
            logger.debug(f"EuropePMC 查询条件: {query}")
            
            # 明确禁用代理
            response = requests.get(url, timeout=30, proxies={'http': None, 'https': None})
            response.raise_for_status()
            data = response.json().get('resultList', {}).get('result', [])
            
            # 记录查询结果
            total_hits = response.json().get('hitCount', 0)
            logger.info(f"EuropePMC 查询返回: 总命中 {total_hits} 篇，实际返回 {len(data)} 篇")
            
            papers = []
            
            for r in data:
                title = r.get('title', '无标题')
                abstract = r.get('abstractText', '')
                
                # 信任 API 结果：已在服务端完成精准检索，本地不再二次匹配关键词
                # 仅执行排除词检查
                
                # 增强 ID 生成容错：doi -> pmid -> pmcid 级联回退
                doi = r.get('doi', '')
                pmid = r.get('pmid', '')
                pmcid = r.get('pmcid', '')
                
                paper = Paper(
                    title=title,
                    abstract=abstract,
                    date=r.get('firstPublicationDate', '') or f"{r.get('pubYear', datetime.date.today().year)}-01-01",
                    source='EuropePMC',
                    doi=doi or pmid or pmcid,  # 级联回退
                    link=pmcid or pmid or doi  # 优先使用 pmcid 作为链接
                )
                
                if should_exclude_paper(paper, exclude_keywords):
                    continue
                if not is_recent_date(paper.date, days=self.window_days):
                    continue
                
                item_id = self.get_item_id(paper)
                if item_id and item_id not in sent_ids:
                    papers.append(paper)
            
            logger.info(f"Europe PMC 共抓取 {len(papers)} 条论文")
            return SourceResult(source_name=self.name, papers=papers)
        except Exception as e:
            logger.error(f"Europe PMC 抓取失败: {e}", exc_info=True)
            return SourceResult(source_name=self.name, papers=[], error=str(e))



