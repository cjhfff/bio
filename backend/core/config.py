"""
配置管理：从环境变量和.env文件加载配置
"""
import os
from typing import List, Dict
from pathlib import Path

# 尝试加载python-dotenv（可选）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    """统一配置类"""
    
    # 安全配置 (JWT 和 Admin)
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-please-change-it")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天
    
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # 简单默认密码，建议修改
    
    # DeepSeek API
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    
    # 备用 DeepSeek API 密钥（在主密钥失败时自动切换）
    @classmethod
    def get_backup_api_keys(cls) -> List[str]:
        """获取备用 API 密钥列表"""
        backup_keys = []
        # 从环境变量读取备用密钥
        for i in range(1, 10):  # 支持最多9个备用密钥
            key = os.getenv(f"DEEPSEEK_API_KEY_{i}", "")
            if key:
                backup_keys.append(key)
        return backup_keys
    
    @classmethod
    def get_all_api_keys(cls) -> List[str]:
        """获取所有 API 密钥（主密钥 + 备用密钥）"""
        keys = [cls.DEEPSEEK_API_KEY]
        keys.extend(cls.get_backup_api_keys())
        return keys
    
    # PubMed
    PUBMED_EMAIL = os.getenv("PUBMED_EMAIL", "")
    
    # 研究方向配置（三大方向）
    RESEARCH_TOPICS: Dict[str, List[str]] = {
        "Nitrogen_Fixation": [
            # 生物固氮核心词
            "nitrogen fixation", "biological nitrogen fixation", "nitrogenase", 
            "rhizobia", "rhizobium", "root nodule", "nodulation", "symbiosis", 
            "diazotroph", "nif genes", "nitrogen-fixing", "nitrogen fixing bacteria", 
            "legume-rhizobium", "symbiosome", "nitrogenase complex", "nif cluster",
            # 扩展词
            "nitrogen metabolism", "ammonia", "legume", "soybean", "bradyrhizobium",
            "sinorhizobium", "azotobacter", "cyanobacteria", "heterocyst"
        ],
        "Signal_Transduction": [
            # 信号转导核心词
            "extracellular signal", "extracellular signal perception", "signal perception",
            "signal transduction", "receptor kinase", "receptor-like kinase", "RLK",
            "G-protein coupled receptor", "GPCR", "ligand binding", "ligand recognition",
            "phosphorylation cascade", "signal pathway", "signaling pathway",
            "two-component system", "histidine kinase", "response regulator",
            "receptor activation", "signal receptor", "membrane receptor",
            # 扩展词
            "kinase", "phosphorylation", "protein kinase", "MAP kinase", "MAPK",
            "calcium signaling", "hormone signaling", "plant immunity", "defense response",
            "pattern recognition", "PRR", "elicitor", "PAMP", "effector",
            # 植物免疫受体相关（新增）
            "NLR", "NLR receptor", "NLR complex", "resistosome",
            "RPP", "ATR", "effector recognition", "effector-triggered immunity",
            "CPK", "calcium-dependent protein kinase", "CDPK",
            "plant immune receptor", "immune signaling", "plant immunity receptor",
            # 细胞膜表面受体/PRR 介导的 PTI（补充：用户研究方向）
            "cell surface receptor", "plasma membrane receptor", "membrane receptor",
            "pattern-triggered immunity", "pattern triggered immunity", "pti",
            "pattern recognition receptor", "PRR",
            "FLS2", "EFR", "BAK1", "SERK", "BIK1",
            "flagellin", "flg22", "elf18",
            "ROS burst", "oxidative burst", "callose deposition",
            "MAPK cascade", "MPK3", "MPK6"
        ],
        "Enzyme_Mechanism": [
            # 酶结构与机制核心词
            "enzyme structure", "enzyme mechanism", "catalytic mechanism", 
            "active site", "catalytic site", "allosteric regulation", "allosteric site",
            "enzyme kinetics", "cryo-EM structure", "cryo-EM", "cryo-electron microscopy",
            "crystal structure", "X-ray crystallography", "substrate specificity",
            "substrate binding", "transition state", "cofactor", "enzyme-substrate complex",
            "enzyme catalysis", "catalytic domain", "enzyme conformation", "structural biology",
            # 扩展词
            "protein structure", "3D structure", "molecular structure", "binding site",
            "conformational change", "protein folding", "metalloenzyme", "oxidoreductase",
            "hydrolase", "transferase", "isomerase", "ligase", "lyase",
            # 免疫受体结构相关（新增）
            "NLR structure", "resistosome structure"
        ]
    }
    
    # 合并所有关键词
    @classmethod
    def get_all_keywords(cls) -> List[str]:
        keywords = []
        for kws in cls.RESEARCH_TOPICS.values():
            keywords.extend(kws)
        return keywords
    
    # BioRxiv 目标分类（扩展版，覆盖结构生物学相关领域）
    TARGET_CATEGORIES = [
        'plant biology', 'biochemistry', 'biophysics', 
        'microbiology', '分子生物学', '细胞生物学',
        'structural biology', 'cell biology', 'molecular biology'  # 新增：结构生物学相关
    ]
    
    # 排除关键词
    EXCLUDE_KEYWORDS = [
        "human", "patient", "clinical", "mouse", "mice", "rat", "rats", 
        "avian", "bird", "fish", "cancer", "tumor", "tumour", "carcinoma",
        "mammal", "vertebrate", "zebrafish", "drosophila", "drosophila melanogaster",
        "therapy", "treatment", "drug", "medicine", "medical", "hospital"
    ]
    
    # 结构生物学高价值关键词（用于豁免排除词检查）
    STRUCTURE_KEYWORDS = [
        'cryo-em', 'cryo-electron microscopy', 'crystal structure', 'x-ray crystallography',
        'atomic resolution', 'angstrom resolution', 'structural biology',
        'nlr', 'nlr structure', 'nlr receptor', 'nlr complex', 'resistosome', 'inflammasome', 
        'receptor structure', 'protein complex structure', 'conformational change', 'active site structure'
    ]
    
    # ========== 差异化过滤策略配置 ==========
    # 顶刊使用的领域大词列表（宽松过滤，提高召回率）
    BROAD_KEYWORDS = [
        "plant", "nitrogen", "legume",  # 生物固氮相关
        "receptor", "immune", "signal",  # 信号转导相关
        "structure", "protein", "enzyme"  # 酶结构机制相关
    ]
    
    # 顶刊域名白名单
    TOP_TIER_DOMAINS = [
        "nature.com",      # Nature 主刊及所有子刊
        "sciencemag.org",  # Science 主刊及子刊
        "cell.com"         # Cell 主刊及所有子刊
    ]
    
    # 是否启用顶刊日期容错机制
    ENABLE_TOP_TIER_DATE_TOLERANCE = os.getenv("ENABLE_TOP_TIER_DATE_TOLERANCE", "True") == "True"
    
    # 顶刊日期解析失败时的默认信任时长（小时）
    TOP_TIER_TRUST_HOURS = int(os.getenv("TOP_TIER_TRUST_HOURS", "48"))
    
    # 是否启用基于链接哈希的去重机制
    ENABLE_LINK_HASH_DEDUP = os.getenv("ENABLE_LINK_HASH_DEDUP", "True") == "True"
    
    # 研究方向描述
    RESEARCH_INTEREST = "生物固氮、胞外信号感知与传递（含细胞膜表面受体/PRR 介导的 PTI 等植物免疫信号）、酶的结构与作用机制（仅限这三个研究方向）"
    
    # 邮件配置
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
    SENDER_AUTH_CODE = os.getenv("SENDER_AUTH_CODE", "")
    RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "")
    
    # PushPlus 配置（支持多个token，用逗号分隔）
    PUSHPLUS_TOKENS: List[str] = [
        token.strip() 
        for token in os.getenv("PUSHPLUS_TOKENS", "").split(",")
        if token.strip()
    ]
    
    # 企业微信配置
    WECOM_WEBHOOK_URL = os.getenv("WECOM_WEBHOOK_URL", "")
    
    # 数据库路径
    DB_PATH = os.getenv("DB_PATH", "data/database/paper_push.db")
    
    # 抓取窗口配置（天数）
    DEFAULT_WINDOW_DAYS = int(os.getenv("DEFAULT_WINDOW_DAYS", "1"))  # 改为1天，只检索当天
    EUROPEPMC_WINDOW_DAYS = int(os.getenv("EUROPEPMC_WINDOW_DAYS", "1"))  # 1天窗口，只检索前一天
    
    # 快速AI预筛选配置
    QUICK_FILTER_THRESHOLD = int(os.getenv("QUICK_FILTER_THRESHOLD", "50"))  # 快速筛选阈值（只对≥此分数的论文进行AI判断）
    
    # 回退策略配置
    MIN_CANDIDATES = int(os.getenv("MIN_CANDIDATES", "5"))  # 候选不足时触发回退（降低阈值，确保更容易触发回退）
    TOP_K = int(os.getenv("TOP_K", "12"))  # 选择Top K篇（智能选择：P0全部+P1最多5篇+P2最多7篇）
    MAX_WINDOW_DAYS = int(os.getenv("MAX_WINDOW_DAYS", "60"))  # 最大回退窗口（扩大回退范围）
    
    # BioRxiv 优化配置
    BIORXIV_MAX_PAGES = int(os.getenv("BIORXIV_MAX_PAGES", "20"))  # 最大抓取页数（默认20页）
    ENABLE_EXEMPTION = os.getenv("ENABLE_EXEMPTION", "True") == "True"  # 启用豁免机制
    ENABLE_DIAGNOSTIC = os.getenv("ENABLE_DIAGNOSTIC", "True") == "True"  # 启用诊断日志
    
    # 期刊影响因子映射（用于评分系统）
    JOURNAL_IMPACT_MAP = {
        # 顶级期刊
        'nature': 15, 'science': 15, 'cell': 15,
        # Nature 子刊
        'nature plants': 12, 'nature chemical biology': 12, 'nature structural': 12,
        'nature structural & molecular biology': 12, 'nature communications': 10,
        # 植物/分子生物学顶刊
        'molecular plant': 10, 'plant cell': 10, 'molecular cell': 12,
        # 综合期刊
        'pnas': 8, 'plos biology': 8, 'elife': 8,
        # 预印本
        'biorxiv': 0, 'arxiv': 0
    }
    
    # ========== 评分系统关键词配置（用于协同增益机制） ==========
    # 结构生物学核心词（15分/词）
    STRUCT_KEYWORDS_SCORING = [
        'cryo-em', 'cryo-electron microscopy', 'crystal structure', 'x-ray crystallography',
        'atomic resolution', 'angstrom resolution', 'active site', 'conformation', 'mechanism',
        'nlr structure', 'resistosome', 'inflammasome', 'conformational change'
    ]
    
    # 生物固氮核心词（8分/词）
    NITRO_KEYWORDS = [
        'nitrogen fixation', 'nitrogenase', 'nif', 'nodulation', 'symbiosome',
        'rhizobia', 'root nodule', 'diazotroph', 'legume-rhizobium'
    ]
    
    # 信号转导核心词（8分/词）
    SIGNAL_KEYWORDS = [
        'signal transduction', 'receptor kinase', 'ligand', 'phosphorylation', 
        'signaling pathway', 'receptor-like kinase', 'rlk', 'two-component system',
        # PTI/细胞膜表面受体（补充：提高该方向命中率）
        'pattern-triggered immunity', 'pattern triggered immunity', 'pti',
        'pattern recognition receptor', 'prr',
        'cell surface receptor', 'plasma membrane receptor',
        'fls2', 'efr', 'bak1', 'serk', 'bik1',
        'flg22', 'elf18',
        'mapk', 'mpk3', 'mpk6',
        'ros burst', 'callose deposition'
    ]
    
    # 结构突破组合词（15分固定加分）
    BREAKTHROUGH_KEYWORDS = [
        'nlr', 'resistosome', 'inflammasome', 'cryo-em', 'cryo-electron microscopy', 'atomic resolution'
    ]
    
    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "paper_push.log")
    
    # ========== 优化系统配置 ==========
    # GitHub API配置（使用Token避免限流）
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

    # Semantic Scholar API配置
    SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
    
    # 豁免权重计分配置
    EXEMPTION_SCORE_THRESHOLD = int(os.getenv("EXEMPTION_SCORE_THRESHOLD", "10"))
    EXEMPTION_CORE_VERBS = [
        "resolved", "determined", "revealed", "elucidated",
        "complex structure of", "mechanism of", "architecture of"
    ]
    ENABLE_WEIGHT_BASED_EXEMPTION = os.getenv("ENABLE_WEIGHT_BASED_EXEMPTION", "True") == "True"
    
    # LLM上下文管理配置
    LLM_MAX_CONTEXT_TOKENS = int(os.getenv("LLM_MAX_CONTEXT_TOKENS", "32000"))  # 提升到32K，支持更多论文
    LLM_TOKEN_BUFFER_RATIO = float(os.getenv("LLM_TOKEN_BUFFER_RATIO", "1.2"))
    ENABLE_DYNAMIC_CONTEXT_MANAGEMENT = os.getenv("ENABLE_DYNAMIC_CONTEXT_MANAGEMENT", "True") == "True"
    
    # API连接优化配置
    API_TIMEOUT = int(os.getenv("API_TIMEOUT", "600"))  # 增加到600秒（10分钟）
    API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "3"))  # 每个密钥最多重试3次
    API_RETRY_BASE_DELAY = int(os.getenv("API_RETRY_BASE_DELAY", "10"))  # 基础延迟10秒
    API_RETRY_MAX_DELAY = int(os.getenv("API_RETRY_MAX_DELAY", "60"))  # 最大延迟60秒
    
    # 标题指纹去重配置
    ENABLE_TITLE_FINGERPRINT_DEDUP = os.getenv("ENABLE_TITLE_FINGERPRINT_DEDUP", "True") == "True"
    
    # 性能监控配置
    ENABLE_LATENCY_TRACKING = os.getenv("ENABLE_LATENCY_TRACKING", "True") == "True"
    
    @classmethod
    def validate(cls) -> List[str]:
        """验证配置，返回错误列表"""
        errors = []
        
        # 检查必需的DeepSeek API密钥
        if not cls.DEEPSEEK_API_KEY:
            errors.append("❌ DEEPSEEK_API_KEY 未设置，请在 .env 文件中配置")
        
        # 检查必需的PubMed邮箱
        if not cls.PUBMED_EMAIL:
            errors.append("❌ PUBMED_EMAIL 未设置，请在 .env 文件中配置 PubMed API 需要的邮箱地址")
        
        # 警告：如果没有配置任何推送渠道
        if not cls.PUSHPLUS_TOKENS and not cls.SENDER_EMAIL and not cls.WECOM_WEBHOOK_URL:
            errors.append("⚠️  警告：未配置任何推送渠道（PUSHPLUS_TOKENS、SENDER_EMAIL 或 WECOM_WEBHOOK_URL），报告将不会被推送")
        
        return errors
    
    @classmethod
    def validate_and_exit(cls):
        """验证配置，如果有错误则打印提示并退出程序"""
        errors = cls.validate()
        if errors:
            print("\n" + "="*60)
            print("❌ 配置验证失败，请检查以下问题：")
            print("="*60)
            for error in errors:
                print(f"  {error}")
            print("\n💡 提示：")
            print("  1. 复制 .env.example 到 .env")
            print("  2. 在 .env 文件中填写必需的配置项")
            print("  3. 重新运行程序")
            print("="*60 + "\n")
            import sys
            sys.exit(1)




