"""
AI 报告生成（支持Token预算分配和动态截断）
"""
import time
import logging
from typing import List, Tuple
from openai import OpenAI
from backend.models import ScoredPaper, SourceResult
from backend.config import Config
from backend.ranking import get_priority_level

logger = logging.getLogger(__name__)

# 尝试导入tiktoken进行精确Token计算
try:
    import tiktoken
    HAS_TIKTOKEN = True
    # DeepSeek使用类似GPT的tokenizer，使用cl100k_base编码
    try:
        _tokenizer = tiktoken.get_encoding("cl100k_base")
    except:
        # 如果cl100k_base不可用，尝试其他编码
        try:
            _tokenizer = tiktoken.get_encoding("gpt2")
        except:
            _tokenizer = None
            HAS_TIKTOKEN = False
except ImportError:
    HAS_TIKTOKEN = False
    _tokenizer = None
    logger.warning("tiktoken未安装，将使用估算方法。建议安装: pip install tiktoken")


def _generate_fallback_report(scored_papers: List[ScoredPaper], error: Exception) -> str:
    """
    当AI调用失败时，生成降级报告
    """
    logger.warning("使用降级报告生成模式（AI调用失败）")
    
    report = "## ⚠️ 报告生成说明\n\n"
    report += f"由于AI服务暂时不可用（错误: {type(error).__name__}: {str(error)}），本次使用简化报告格式。\n\n"
    
    # 按优先级分组
    p0_papers = []
    p1_papers = []
    p2_papers = []
    
    for scored in scored_papers:
        priority = get_priority_level(scored.score)
        if priority == "P0":
            p0_papers.append(scored)
        elif priority == "P1":
            p1_papers.append(scored)
        else:
            p2_papers.append(scored)
    
    # P0 论文
    if p0_papers:
        report += "## 🔥 顶级论文 (P0 - 最高优先级)\n\n"
        for i, scored in enumerate(p0_papers[:5], 1):
            paper = scored.paper
            report += f"**{i}. {paper.title}**\n\n"
            report += f"- 来源: {paper.source}\n"
            report += f"- 日期: {paper.date}\n"
            if paper.doi:
                report += f"- DOI: {paper.doi}\n"
            if paper.link:
                report += f"- 链接: {paper.link}\n"
            if paper.abstract:
                # P0论文保留完整摘要（最多3000字符，与正常报告一致）
                if len(paper.abstract) > 3000:
                    abstract_preview = paper.abstract[:3000] + "\n[摘要过长，已截断，建议查看原文]"
                else:
                    abstract_preview = paper.abstract
                report += f"- 摘要: {abstract_preview}\n"
            report += f"- 评分: {scored.score:.1f}\n\n"
    
    # P1 工具
    if p1_papers:
        report += "## 🛠️ 新工具 (P1 - 技术前哨)\n\n"
        for i, scored in enumerate(p1_papers[:3], 1):
            paper = scored.paper
            report += f"**{i}. {paper.title}**\n\n"
            if paper.link:
                report += f"- 链接: {paper.link}\n"
            report += f"- 来源: {paper.source}\n"
            report += f"- 日期: {paper.date}\n"
            if paper.abstract:
                # P1论文保留前800字符（比P0少，但比原来的300多）
                if len(paper.abstract) > 800:
                    abstract_preview = paper.abstract[:800] + "..."
                else:
                    abstract_preview = paper.abstract
                report += f"- 摘要: {abstract_preview}\n"
            report += "\n"
    
    # P2 关联性挖掘
    if p2_papers and not p0_papers:
        report += "## 💡 关联性挖掘 (P2 - 启发价值)\n\n"
        report += "本次检索范围内未发现直接属于三大方向的核心更新，但发现以下可能相关的论文：\n\n"
        for i, scored in enumerate(p2_papers[:3], 1):
            paper = scored.paper
            report += f"**{i}. {paper.title}**\n\n"
            report += f"- 来源: {paper.source}\n"
            if paper.link:
                report += f"- 链接: {paper.link}\n"
            if paper.abstract:
                # P2论文保留前500字符
                if len(paper.abstract) > 500:
                    abstract_preview = paper.abstract[:500] + "..."
                else:
                    abstract_preview = paper.abstract
                report += f"- 摘要: {abstract_preview}\n"
            report += "\n"
    
    # 数据统计
    report += "## 📊 数据统计\n\n"
    report += f"- 本次检索范围内新增论文数: {len(scored_papers)}\n"
    report += f"- 优先级分布: P0={len(p0_papers)}篇, P1={len(p1_papers)}篇, P2={len(p2_papers)}篇\n\n"
    
    report += "---\n\n"
    report += "*注：由于AI服务暂时不可用，本报告为简化版本。建议稍后重新运行以获取完整AI分析报告。*\n"
    
    return report


def estimate_tokens(text: str) -> int:
    """
    精确计算文本的Token数（优先使用tiktoken，否则使用保守估算）
    
    考虑到生化领域的复杂术语（如Phosphatidylethanolamine、根瘤菌共生体等），
    使用精确的tokenizer可以避免非线性风险。
    
    Args:
        text: 待计算的文本
        
    Returns:
        Token数量（包含10%安全冗余）
    """
    if not text:
        return 0
    
    # 优先使用tiktoken进行精确计算
    if HAS_TIKTOKEN and _tokenizer:
        try:
            tokens = _tokenizer.encode(text)
            # 添加10%安全冗余（考虑到prompt中的指令等）
            return int(len(tokens) * 1.1)
        except Exception as e:
            logger.warning(f"tiktoken计算失败，使用估算方法: {e}")
    
    # 降级方案：保守估算（针对中英文混合+生化术语）
    # 考虑到复杂生化术语的subword切分，使用1.0-1.2倍率
    # 中文字符约0.6-1.5 token，英文单词约0.25-1.5 token（取决于长度）
    # 混合文本使用1.0倍率，然后添加20%冗余
    return int(len(text) * 1.0 * 1.2)


def prepare_papers_for_llm(scored_papers: List[ScoredPaper], max_tokens: int = None, batch_size: int = None) -> Tuple[str, int, int]:
    """
    为 LLM 准备论文输入（支持单篇精读模式和批量模式）
    
    Args:
        scored_papers: 带评分的论文列表
        max_tokens: 最大Token限制,默认使用Config.LLM_MAX_CONTEXT_TOKENS
        batch_size: 批次大小，如果为None则处理所有论文，如果指定则只处理前batch_size篇
    
    Returns:
        (papers_text, 包含的论文数, 估算Token数)
    """
    if max_tokens is None:
        max_tokens = Config.LLM_MAX_CONTEXT_TOKENS
    
    if len(scored_papers) == 0:
        return "", 0, 0
    
    # 如果指定了batch_size，只处理前batch_size篇
    papers_to_process = scored_papers[:batch_size] if batch_size else scored_papers
    
    paper_blocks = []
    total_tokens = 0
    
    for idx, scored in enumerate(papers_to_process, 1):
        paper = scored.paper
        priority = get_priority_level(scored.score)
        
        # 批量模式：保留完整摘要（不截断）
        abstract_text = paper.abstract if paper.abstract else ""
        # 仅在极端情况下（>5000字符）才截断
        if len(abstract_text) > 5000:
            abstract_text = abstract_text[:5000] + "\n[摘要过长，已截断，建议查看原文]"
        
        # 构建论文文本块（完整结构化信息）
        paper_block = f"【论文 {idx}】\n"
        paper_block += f"标题: {paper.title}\n\n"
        paper_block += f"期刊/来源: {paper.source}\n\n"
        paper_block += f"发布时间: {paper.date}\n\n"
        paper_block += f"摘要: {abstract_text}\n\n"
        
        # 添加评分信息（让AI知道为什么这篇论文被选中）
        paper_block += f"评分: {scored.score:.1f}分 (优先级: {priority})\n"
        if scored.reasons:
            # 添加所有评分理由（帮助AI理解论文与三大方向的关联）
            reason_summary = "; ".join([r.description for r in scored.reasons])
            paper_block += f"评分理由: {reason_summary}\n"
        paper_block += "\n"
        
        if paper.doi:
            paper_block += f"DOI: {paper.doi}\n\n"
        if paper.link:
            paper_block += f"链接: {paper.link}\n\n"
        if paper.citation_count > 0:
            paper_block += f"引用数: {paper.citation_count}\n"
            if paper.influential_count > 0:
                paper_block += f"高影响力引用: {paper.influential_count}\n"
        paper_block += "---\n\n"
        
        # 估算Token数
        block_tokens = estimate_tokens(paper_block)
        total_tokens += block_tokens
        paper_blocks.append(paper_block)
    
    papers_text = "".join(paper_blocks)
    
    mode_name = f"批量模式（{len(papers_to_process)}篇）" if batch_size else "单篇精读模式"
    logger.info(
        f"[{mode_name}] 包含 {len(papers_to_process)} 篇论文, 估算Token数: {total_tokens}/{max_tokens}"
    )
    
    return papers_text, len(papers_to_process), total_tokens


def generate_single_paper_report(scored_paper: ScoredPaper, paper_num: int) -> str:
    """
    生成单篇论文的重要研究成果总结
    
    Args:
        scored_paper: 带评分的论文
        paper_num: 论文编号
        
    Returns:
        生成的论文报告文本
    """
    if not scored_paper:
        return ""
    
    # 准备论文文本（单篇，包含完整信息）
    papers_text, _, _ = prepare_papers_for_llm([scored_paper], batch_size=1)
    
    # 构建提示词（简化版，只总结重要研究成果）
    prompt = f"""你是一名专注于生物化学与分子生物学研究的专家。请总结以下论文的重要研究成果。

**重要：检索范围仅限以下三个研究方向，其他方向的研究请忽略：**
1. 生物固氮（Biological Nitrogen Fixation）
2. 胞外信号感知与传递（Extracellular Signal Perception and Transduction，包含细胞膜表面受体/PRR/RLK 介导的 PTI 等植物免疫信号）
3. 酶的结构与作用机制（Enzyme Structure and Mechanism）

**任务要求：**
请简洁地总结这篇论文的重要研究成果，包含以下内容：

### 【论文标题】 (期刊: XXX, 发布日期: YYYY-MM-DD)

**重要研究成果：**
- 核心科学发现（1-2句话概括）
- 创新点和突破性成果（1-2句话）
- 对三大研究方向的重要意义（1句话）

**技术方法：**（如有结构生物学方法或新技术，简要说明）

**参考文献：**
- DOI: [如有]
- 链接: [如有]

**要求：**
- 总字数控制在200-400字
- 语言简洁明了，突出重点
- 必须标注发布日期（格式：发布日期: YYYY-MM-DD）
- **重要：如果论文不属于三大研究方向（生物固氮、胞外信号感知与传递、酶的结构与作用机制），请返回以下格式：**
  ```
  ## 不相关论文
  
  **论文标题：** [论文标题]
  
  **过滤原因：** [简要说明为什么不属于三大研究方向，例如：该研究主要关注XXX领域，与生物固氮、胞外信号感知与传递、酶的结构与作用机制无直接关联]
  
  此论文不属于指定的三大研究方向，已自动过滤。
  ```
  如果论文属于三大研究方向，请按正常格式返回。

{papers_text}
"""
    
    # 获取所有 API 密钥（主密钥 + 备用密钥）
    all_api_keys = Config.get_all_api_keys()
    logger.info(f"[论文 {paper_num}] 开始生成报告，可用 API 密钥数量: {len(all_api_keys)}")
    
    # 遍历所有 API 密钥，如果当前密钥失败，自动切换到下一个
    last_error = None
    for key_index, api_key in enumerate(all_api_keys):
        key_name = "主密钥" if key_index == 0 else f"备用密钥{key_index}"
        masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
        logger.info(f"[论文 {paper_num}] 尝试使用 {key_name}: {masked_key}")
        
        # 每个密钥的重试机制（指数退避策略）
        max_retries_per_key = Config.API_MAX_RETRIES
        for attempt in range(max_retries_per_key):
            try:
                logger.info(f"[论文 {paper_num}] 正在调用AI生成报告（{key_name}, 第 {attempt + 1}/{max_retries_per_key} 次尝试）...")
                
                # 每次重试都创建新的客户端实例，避免连接复用问题
                client = OpenAI(
                    api_key=api_key,
                    base_url=Config.DEEPSEEK_BASE_URL,
                    timeout=Config.API_TIMEOUT,
                    max_retries=0  # 禁用SDK内置重试，手动控制
                )
                
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一位生物化学与分子生物学领域的专家，擅长简洁地总结学术论文的重要研究成果。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                    max_tokens=1000  # 单篇总结，减少tokens
                )
                
                paper_report = response.choices[0].message.content
                logger.info(f"✅ [论文 {paper_num}] AI报告生成成功！(使用 {key_name}, 耗时约 {attempt + 1} 次尝试)")
                return paper_report
                
            except KeyboardInterrupt:
                logger.warning("用户手动中断了程序")
                raise
            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                error_msg = str(e)
                logger.error(f"[论文 {paper_num}] 调用大语言模型时出错（{key_name}, 第 {attempt + 1} 次尝试）: {error_type}: {error_msg[:200]}")
                
                # 如果是认证错误（401），直接切换到下一个密钥
                if "401" in error_msg or "Unauthorized" in error_msg or "invalid" in error_msg.lower():
                    logger.warning(f"[论文 {paper_num}] {key_name} 认证失败，切换到下一个密钥")
                    break
                
                # 如果是连接错误，使用指数退避策略重试
                if attempt < max_retries_per_key - 1:
                    # 指数退避：10秒、20秒、40秒，但不超过最大延迟
                    wait_time = min(Config.API_RETRY_BASE_DELAY * (2 ** attempt), Config.API_RETRY_MAX_DELAY)
                    logger.info(f"[论文 {paper_num}] 等待 {wait_time} 秒后重试（指数退避策略）...")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"[论文 {paper_num}] {key_name} 所有重试均失败，尝试下一个密钥")
                    if key_index < len(all_api_keys) - 1:
                        time.sleep(5)  # 切换密钥前等待更长时间
                    break
    
    # 所有密钥都失败，返回降级报告
    logger.error(f"[论文 {paper_num}] 所有 API 密钥（共 {len(all_api_keys)} 个）均失败，返回降级报告")
    return _generate_fallback_report([scored_paper], last_error)


def generate_final_summary(all_paper_reports: List[str], total_papers: int, source_results: List[SourceResult] = None) -> str:
    """
    生成最终总结报告（保留所有论文重要研究成果 + 总体总结）
    
    Args:
        all_paper_reports: 所有论文的重要研究成果报告列表
        total_papers: 总论文数
        source_results: 数据源抽取结果列表(可选,用于统计)
        
    Returns:
        生成的最终综合报告文本
    """
    if not all_paper_reports:
        return "本次检索范围内未发现相关论文。"
    
    # 合并所有论文的重要研究成果
    detailed_content = "\n\n".join([f"## 论文 {i+1} 重要研究成果\n\n{report}" for i, report in enumerate(all_paper_reports)])
    
    # 检查内容长度，如果超过阈值（20000字符），只传递前N篇论文给API
    MAX_CONTENT_LENGTH = 20000
    reports_to_use = all_paper_reports
    if len(detailed_content) > MAX_CONTENT_LENGTH:
        # 计算可以包含多少篇论文
        current_length = 0
        reports_to_use = []
        for i, report in enumerate(all_paper_reports):
            report_with_header = f"## 论文 {i+1} 重要研究成果\n\n{report}\n\n"
            if current_length + len(report_with_header) > MAX_CONTENT_LENGTH:
                break
            reports_to_use.append(report)
            current_length += len(report_with_header)
        
        logger.warning(f"论文报告总长度({len(detailed_content)}字符)超过阈值({MAX_CONTENT_LENGTH}字符)，仅使用前{len(reports_to_use)}篇论文生成最终总结")
        detailed_content = "\n\n".join([f"## 论文 {i+1} 重要研究成果\n\n{report}" for i, report in enumerate(reports_to_use)])
    
    # 构建数据源统计信息
    source_stats = ""
    if source_results:
        total_from_all_sources = sum(len(r.papers) for r in source_results)
        source_stats = "\n<metadata>\n"
        source_stats += "**数据源统计信息（元数据，仅供了解搜索覆盖广度）：**\n"
        for r in source_results:
            source_stats += f"- {r.source_name}: {len(r.papers)} 条\n"
        source_stats += f"- 总计: {total_from_all_sources} 条（所有数据源）\n"
        source_stats += f"- 经过评分筛选后，共 {total_papers} 篇进入最终分析\n"
        if len(reports_to_use) < len(all_paper_reports):
            source_stats += f"- 注意：由于内容过长，最终总结仅基于前 {len(reports_to_use)} 篇论文\n"
        source_stats += "</metadata>\n\n"
    
    # 构建最终总结的提示词
    prompt = f"""你是一名专注于生物化学与分子生物学研究的专家。以下是今天检索到的所有论文的重要研究成果总结。

{source_stats}

**重要：检索范围仅限以下三个研究方向：**
1. 生物固氮（Biological Nitrogen Fixation）
2. 胞外信号感知与传递（Extracellular Signal Perception and Transduction，包含细胞膜表面受体/PRR/RLK 介导的 PTI 等植物免疫信号）
3. 酶的结构与作用机制（Enzyme Structure and Mechanism）

**任务要求：**
1. **保留所有论文的重要研究成果**：完整保留下方列出的所有论文的重要研究成果内容
2. **添加总体总结**：在保留详细内容的基础上，添加以下总体分析：
   - 今日研究热点总结：概括今天所有论文反映的研究趋势
   - 跨论文关联分析：分析不同论文之间的关联性和协同价值
   - 领域发展动态：总结对三大研究方向的整体推动作用
   - 重要发现亮点：提炼今天最重要的科学发现和突破

**报告结构：**
1. 首先添加"## 📊 今日研究总结"部分（总体分析，300-500字）
2. 然后完整保留所有论文的重要研究成果内容
3. 最后添加"## 📈 数据统计"部分

请用通俗易懂的语言，生成一份综合性的每日情报内参。

以下是所有论文的重要研究成果：

{detailed_content}
"""
    
    # 获取所有 API 密钥
    all_api_keys = Config.get_all_api_keys()
    logger.info(f"开始生成最终总结报告，可用 API 密钥数量: {len(all_api_keys)}")
    
    # 遍历所有 API 密钥
    last_error = None
    for key_index, api_key in enumerate(all_api_keys):
        key_name = "主密钥" if key_index == 0 else f"备用密钥{key_index}"
        masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
        logger.info(f"尝试使用 {key_name}: {masked_key}")
        
        max_retries_per_key = Config.API_MAX_RETRIES
        for attempt in range(max_retries_per_key):
            try:
                logger.info(f"正在调用AI生成最终总结报告（{key_name}, 第 {attempt + 1}/{max_retries_per_key} 次尝试）...")
                
                # 每次重试都创建新的客户端实例，避免连接复用问题
                client = OpenAI(
                    api_key=api_key,
                    base_url=Config.DEEPSEEK_BASE_URL,
                    timeout=Config.API_TIMEOUT,
                    max_retries=0  # 禁用SDK内置重试，手动控制
                )
                
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一位生物化学与分子生物学领域的专家，擅长综合分析多篇论文，提炼研究趋势和重要发现。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                    max_tokens=4000
                )
                
                final_report = response.choices[0].message.content
                logger.info(f"✅ 最终总结报告生成成功！(使用 {key_name})")
                
                # 添加数据完整性提示
                if source_results:
                    degraded_sources = [sr for sr in source_results if sr.is_degraded or sr.error]
                    if degraded_sources:
                        final_report += "\n\n## ⚠️ 数据完整性说明\n\n"
                        final_report += "本次报告生成过程中,以下数据源未能完整获取:\n"
                        for sr in degraded_sources:
                            if sr.error:
                                final_report += f"- {sr.source_name}: 抽取失败 ({sr.error})\n"
                            elif sr.degraded_reason:
                                final_report += f"- {sr.source_name}: {sr.degraded_reason}\n"
                        final_report += "\n建议关注后续更新,或手动访问对应数据源确认。\n"
                
                return final_report
                
            except KeyboardInterrupt:
                logger.warning("用户手动中断了程序")
                raise
            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                error_msg = str(e)
                logger.error(f"调用大语言模型时出错（{key_name}, 第 {attempt + 1} 次尝试）: {error_type}: {error_msg[:200]}")
                
                if "401" in error_msg or "Unauthorized" in error_msg or "invalid" in error_msg.lower():
                    logger.warning(f"{key_name} 认证失败，切换到下一个密钥")
                    break
                
                if attempt < max_retries_per_key - 1:
                    # 指数退避策略
                    wait_time = min(Config.API_RETRY_BASE_DELAY * (2 ** attempt), Config.API_RETRY_MAX_DELAY)
                    logger.info(f"等待 {wait_time} 秒后重试（指数退避策略）...")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"{key_name} 所有重试均失败，尝试下一个密钥")
                    if key_index < len(all_api_keys) - 1:
                        time.sleep(2)
                    break
    
    # 所有密钥都失败，生成基于关键词的简单统计总结
    logger.error(f"所有 API 密钥（共 {len(all_api_keys)} 个）均失败，生成基于关键词的简单统计总结")
    
    # 提取关键词统计
    from collections import Counter
    keywords_found = []
    for report in all_paper_reports:
        # 简单提取可能的关键词（从报告标题和内容中）
        if "结构" in report or "structure" in report.lower() or "cryo-em" in report.lower():
            keywords_found.append("结构生物学")
        if "固氮" in report or "nitrogen" in report.lower():
            keywords_found.append("生物固氮")
        if "信号" in report or "signal" in report.lower() or "受体" in report:
            keywords_found.append("信号转导")
        if "酶" in report or "enzyme" in report.lower():
            keywords_found.append("酶机制")
    
    keyword_counts = Counter(keywords_found)
    keyword_summary = "、".join([f"{kw}({count}篇)" for kw, count in keyword_counts.most_common(5)])
    
    # 生成简单统计总结
    simple_summary = f"""## 📊 今日研究总结

**研究热点：** {keyword_summary if keyword_summary else "未检测到明显热点"}

**论文分布：** 共检索到 {total_papers} 篇相关论文，主要涉及结构生物学、酶机制、信号转导等方向。

**重要提示：** 由于API连接问题，未能生成详细的综合分析。以下是所有论文的重要研究成果总结：

{detailed_content}

*注：单篇论文分析已完成，最终总结报告因API连接问题未生成，建议稍后重新运行以获取完整的AI综合分析报告。*
"""
    
    return simple_summary


def generate_daily_report(scored_papers: List[ScoredPaper], source_results: List[SourceResult] = None) -> str:
    """
    使用 AI 生成每日报告(支持Token预算和数据完整性提示)
    
    Args:
        scored_papers: 带评分的论文列表
        source_results: 数据源抽取结果列表(可选,用于降级检测)
        
    Returns:
        生成的报告文本
    """
    if not scored_papers:
        return "本次检索范围内未发现直接属于三大研究方向（生物固氮、胞外信号感知与传递、酶的结构与作用机制）的核心更新。这可能是因为：1) 检索时间窗口内确实没有相关新论文；2) 数据源抓取存在问题。建议检查数据源连接或扩大检索范围。"
    
    # 使用动态上下文管理或传统全量拼接
    if Config.ENABLE_DYNAMIC_CONTEXT_MANAGEMENT:
        papers_text, included_count, token_count = prepare_papers_for_llm(scored_papers)
        logger.info(f"[动态上下文] 已启用, 包含 {included_count}/{len(scored_papers)} 篇论文")
    else:
        # 传统逻辑(向后兼容)
        papers_text = ""
        for i, scored in enumerate(scored_papers):
            paper = scored.paper
            papers_text += f"【论文 {i+1}】\n"
            papers_text += f"标题: {paper.title}\n\n"
            papers_text += f"期刊/来源: {paper.source}\n\n"
            papers_text += f"发布时间: {paper.date}\n\n"
            papers_text += f"摘要: {paper.abstract}\n\n"
            
            if paper.doi:
                papers_text += f"DOI: {paper.doi}\n\n"
            if paper.link:
                papers_text += f"链接: {paper.link}\n\n"
            if paper.citation_count > 0:
                papers_text += f"引用数: {paper.citation_count}\n"
                if paper.influential_count > 0:
                    papers_text += f"高影响力引用: {paper.influential_count}\n"
            papers_text += "---\n\n"
    
    # 构建数据源统计信息（使用metadata标签，避免AI注意力发散）
    source_stats = ""
    if source_results:
        total_from_all_sources = sum(len(r.papers) for r in source_results)
        source_stats = "\n<metadata>\n"
        source_stats += "**数据源统计信息（元数据，仅供了解搜索覆盖广度，无需在报告中详细分析）：**\n"
        for r in source_results:
            source_stats += f"- {r.source_name}: {len(r.papers)} 条\n"
        source_stats += f"- 总计: {total_from_all_sources} 条（所有数据源）\n"
        source_stats += f"- 经过评分筛选后，以下 {len(scored_papers)} 篇进入最终分析\n"
        source_stats += "</metadata>\n\n"
        source_stats += "**你的主要任务：解析下方列出的论文清单，生成每日情报内参。统计数据仅供参考，无需在报告中纠结为什么只选了这几篇。**\n\n"
    
    # 构建提示词
    prompt = f"""你是一名专注于生物化学与分子生物学研究的专家。以下是过去 7 天内从多个数据源抓取的学术动态，包括：
- 顶级论文（bioRxiv、PubMed、Europe PMC、顶刊 RSS）
- 科学新闻（EurekAlert）
- 技术工具（GitHub 新仓库）
- 高影响力论文（Semantic Scholar）

{source_stats}

**重要：检索范围仅限以下三个研究方向，其他方向的研究请忽略：**
1. 生物固氮（Biological Nitrogen Fixation）
2. 胞外信号感知与传递（Extracellular Signal Perception and Transduction，包含细胞膜表面受体/PRR/RLK 介导的 PTI 等植物免疫信号）
3. 酶的结构与作用机制（Enzyme Structure and Mechanism）

研究方向：{Config.RESEARCH_INTEREST}

**检索范围严格限制：仅限以上三个研究方向，其他方向的研究请忽略。**

**评分说明：**
- 论文已按评分从高到低排序，评分越高表示与三大方向的关联性越强
- P0（评分≥50分）：突破性工作，与三大方向高度相关
- P1（评分30-50分）：重要研究，与三大方向相关
- P2（评分<30分）：一般研究，可能与三大方向相关
- 每篇论文的"评分理由"说明了为什么它被选中，请重点关注与三大方向相关的理由

请按照以下结构输出一份"每日情报内参"：

## 🔥 顶级论文 (P0 - 最高优先级)
**价值：决定你的课题是否会被"抢发"**

识别出涉及【生物固氮、胞外信号感知与传递、酶的结构与作用机制】的重磅文章。
对于每篇重磅文章，请用中文深度总结：
- 研究目标/背景
- 核心发现/突破
- 对相关研究领域的意义
- 潜在应用价值
- **必须标注期刊来源和发布日期，格式：标题 (期刊: XXX, 发布日期: YYYY-MM-DD)**
- 附上 DOI 或链接

## 🛠️ 新工具 (P1 - 技术前哨)
**价值：提高你处理数据或序列分析的效率**

如果发现 GitHub 上的新算法、AlphaFold 新模型、生物信息学工具等，请总结：
- 工具名称和功能
- 对相关研究的潜在应用
- 链接地址
- **必须标注来源平台和发布/更新日期**

## 💡 关联性挖掘 (P2 - 启发价值)
**价值：从非直接研究中发现可借鉴的方法**

如果本次检索范围内没有直接属于三大方向的核心突破，请分析是否有其他方向的研究可以借鉴（但必须与三大方向相关）：
- 结构生物学方法（可应用到酶机制研究）
- 信号转导机制研究（可应用到胞外信号感知）
- 微生物组工程化改造（可启发固氮研究）

**重要提示：如果没有发现直接属于三大方向的核心论文，请明确说明"本次检索范围内未发现直接属于三大方向的核心更新"，然后重点进行关联性挖掘分析。不要简单地说"今日无更新"，因为可能是检索范围或数据源的问题。**

## 📊 数据统计 (P3 - 趋势分析)
**价值：了解领域动态**

简要统计：
- 本次检索范围内新增论文数（注意：这里指的是经过筛选后的Top论文数量，不是所有数据源的总数）
- 主要来源分布（根据下方列出的论文来源统计，不是所有数据源的完整统计）
- 研究热点关键词（基于下方列出的论文分析）

{papers_text}

请用通俗易懂的语言，详细阐述这些论文的科学价值和研究意义。字数要求：1000-2000字。

**特别提醒：如果本次检索范围内没有直接属于三大方向的核心论文，请明确说明"本次检索范围内未发现直接属于三大方向的核心更新"，然后重点进行跨领域的关联性挖掘和启发分析。不要使用"今日无更新"或"无重大公开更新"这样的表述。**
"""
    
    # 获取所有 API 密钥（主密钥 + 备用密钥）
    all_api_keys = Config.get_all_api_keys()
    logger.info(f"可用 API 密钥数量: {len(all_api_keys)} (主密钥 + {len(all_api_keys)-1} 个备用)")
    
    # 遍历所有 API 密钥，如果当前密钥失败，自动切换到下一个
    last_error = None
    for key_index, api_key in enumerate(all_api_keys):
        key_name = "主密钥" if key_index == 0 else f"备用密钥{key_index}"
        masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
        logger.info(f"尝试使用 {key_name}: {masked_key}")
        
        # 每个密钥的重试机制（使用配置的重试次数）
        max_retries_per_key = Config.API_MAX_RETRIES
        for attempt in range(max_retries_per_key):
            try:
                logger.info(f"正在调用AI生成报告（{key_name}, 第 {attempt + 1}/{max_retries_per_key} 次尝试）...")
                logger.info(f"API地址: {Config.DEEPSEEK_BASE_URL}, 超时设置: {Config.API_TIMEOUT}秒")
                
                # 每次重试都创建新的客户端实例，避免连接复用问题
                client = OpenAI(
                    api_key=api_key,
                    base_url=Config.DEEPSEEK_BASE_URL,
                    timeout=Config.API_TIMEOUT,
                    max_retries=0  # 禁用 SDK 内置重试，手动控制
                )
                
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一位生物化学与分子生物学领域的专家，擅长用通俗易懂的语言解读学术论文。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                    max_tokens=3000
                )
                
                daily_report = response.choices[0].message.content
                logger.info(f"✅ AI报告生成成功！(使用 {key_name})")
                
                # 添加数据完整性提示
                if source_results:
                    degraded_sources = [sr for sr in source_results if sr.is_degraded or sr.error]
                    if degraded_sources:
                        daily_report += "\n\n## ⚠️ 数据完整性说明\n\n"
                        daily_report += "本次报告生成过程中,以下数据源未能完整获取:\n"
                        for sr in degraded_sources:
                            if sr.error:
                                daily_report += f"- {sr.source_name}: 抽取失败 ({sr.error})\n"
                            elif sr.degraded_reason:
                                daily_report += f"- {sr.source_name}: {sr.degraded_reason}\n"
                        daily_report += "\n建议关注后续更新,或手动访问对应数据源确认。\n"
                
                return daily_report
            except KeyboardInterrupt:
                logger.warning("用户手动中断了程序")
                raise
            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                error_msg = str(e)
                logger.error(f"调用大语言模型时出错（{key_name}, 第 {attempt + 1} 次尝试）: {error_type}: {error_msg[:200]}")
                
                # 记录详细错误信息
                import traceback
                logger.debug(f"错误堆栈:\n{traceback.format_exc()}")
                
                # 如果是认证错误（401），直接切换到下一个密钥
                if "401" in error_msg or "Unauthorized" in error_msg or "invalid" in error_msg.lower():
                    logger.warning(f"{key_name} 认证失败，切换到下一个密钥")
                    break  # 跳出当前密钥的重试循环，尝试下一个密钥
                
                # 如果是连接错误，使用指数退避策略重试
                if attempt < max_retries_per_key - 1:
                    wait_time = min(Config.API_RETRY_BASE_DELAY * (2 ** attempt), Config.API_RETRY_MAX_DELAY)
                    logger.info(f"等待 {wait_time} 秒后重试（指数退避策略）...")
                    time.sleep(wait_time)
                else:
                    # 当前密钥的所有重试都失败，尝试下一个密钥
                    logger.warning(f"{key_name} 所有重试均失败，尝试下一个密钥")
                    if key_index < len(all_api_keys) - 1:
                        time.sleep(2)  # 切换密钥前稍作等待
                    break  # 跳出当前密钥的重试循环
    
    # 所有密钥都失败，返回降级报告
    logger.error(f"所有 API 密钥（共 {len(all_api_keys)} 个）均失败，返回降级报告")
    return _generate_fallback_report(scored_papers, last_error)



