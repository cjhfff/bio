"""
评分系统：可解释的评分算法
"""
import datetime
from typing import List, Tuple
from backend.models import Paper, ScoreReason, ScoredPaper
from backend.config import Config


def score_paper(paper: Paper) -> ScoredPaper:
    """
    智能权重算法：针对固氮、信号、酶结构进行评分
    增强版：增加期刊影响因子、提高结构关键词权重、协同增益机制
    返回可解释的评分结果
    """
    score = 0.0
    reasons: List[ScoreReason] = []
    text = (paper.title + " " + (paper.abstract or "")).lower()
    
    # --- 1. 关键词命中判定（增强版：上下文检查）---
    matched_struct = [kw for kw in Config.STRUCT_KEYWORDS_SCORING if kw in text]
    matched_nitro = [kw for kw in Config.NITRO_KEYWORDS if kw in text]
    matched_signal = [kw for kw in Config.SIGNAL_KEYWORDS if kw in text]
    
    # 检查是否包含明显的非相关领域词（如果包含，降低分数）
    non_relevant_contexts = [
        "cancer", "tumor", "oncology", "clinical", "disease", "pathology",
        "diagnostic", "biomarker", "therapeutic", "drug discovery",
        "pharmaceutical", "medical", "patient", "treatment",
        # 扩展：更多非相关领域
        "diabetes", "metabolic disease", "cardiovascular", "neurological",
        "immunotherapy", "chemotherapy", "surgery", "diagnosis",
        "prognosis", "epidemiology", "public health", "healthcare"
    ]
    has_non_relevant_context = any(ctx in text for ctx in non_relevant_contexts)
    
    # 检查是否在相关上下文中（结构词必须在相关上下文中才给高分）
    relevant_contexts = [
        "enzyme structure", "protein structure", "molecular structure",
        "catalytic", "mechanism", "active site", "substrate",
        "nitrogenase", "nitrogen fixation", "signal transduction",
        "receptor", "kinase", "phosphorylation",
        # 扩展：更多相关上下文
        "enzyme mechanism", "catalytic mechanism", "allosteric",
        "substrate binding", "enzyme-substrate", "catalytic domain",
        "root nodule", "symbiosis", "rhizobium", "legume",
        "receptor activation", "ligand binding", "signal pathway",
        "two-component", "histidine kinase", "response regulator"
    ]
    has_relevant_context = any(ctx in text for ctx in relevant_contexts)
    
    # 结构词得分 (20分/个，但需要上下文检查)
    if matched_struct:
        # 如果包含非相关上下文，且没有相关上下文，降低分数
        if has_non_relevant_context and not has_relevant_context:
            # 可能是"crystal structure of cancer biomarker"这类不相关论文
            pts = len(matched_struct) * 5  # 降低分数
            reasons.append(ScoreReason(
                category="struct_match_weak", 
                points=pts, 
                description=f"命中结构词但上下文不相关: {', '.join(matched_struct[:2])} (+{pts}分，已降分)"
            ))
        else:
            pts = len(matched_struct) * 20
            reasons.append(ScoreReason(
                category="struct_match", 
                points=pts, 
                description=f"命中结构核心词: {', '.join(matched_struct[:2])} (+{pts}分)"
            ))
        score += pts
    
    # 固氮/信号词得分 (12分/个，提高权重)
    field_pts = (len(matched_nitro) + len(matched_signal)) * 12
    if field_pts > 0:
        score += field_pts
        all_field_kws = matched_nitro + matched_signal
        reasons.append(ScoreReason(
            category="field_match", 
            points=field_pts, 
            description=f"命中固氮/信号词: {', '.join(all_field_kws[:2])} (+{field_pts}分)"
        ))
    
    # 核心方向匹配加分 (直接命中三大研究方向，+20分)
    # 但要求必须同时有相关上下文，避免误判
    if (matched_nitro or matched_signal or matched_struct) and has_relevant_context:
        core_pts = 20
        score += core_pts
        reasons.append(ScoreReason(
            category="core_direction_match", 
            points=core_pts, 
            description="直接命中三大研究方向核心内容 (+20分)"
        ))
    elif matched_nitro or matched_signal or matched_struct:
        # 只有关键词但没有相关上下文，降低分数
        core_pts = 5
        score += core_pts
        reasons.append(ScoreReason(
            category="core_direction_match_weak", 
            points=core_pts, 
            description="命中关键词但上下文不明确 (+5分，已降分)"
        ))
    
    # --- 2. 🔥 协同增益评分 (Synergy Bonus) ---
    # 如果同时包含"结构"和"领域词"，说明是高质量的机制研究
    if matched_struct and (matched_nitro or matched_signal):
        synergy_pts = 25  # 额外奖励25分（提高权重）
        score += synergy_pts
        reasons.append(ScoreReason(
            category="synergy_bonus", 
            points=synergy_pts, 
            description="[RELEVANT_CROSS_FIELD] 结构解析+固氮/信号机制交叉 (+25分)"
        ))
    
    # --- 3. 来源与突破加权 ---
    source_lower = paper.source.lower()
    
    # 3.1 顶刊来源加权
    if 'rss_topjournal' in source_lower or 'rss' in source_lower:
        source_points = 20
        score += source_points
        reasons.append(ScoreReason(
            category="top_journal_source",
            points=source_points,
            description=f"顶级期刊来源 (+{source_points}分)"
        ))
    
    # 3.2 Europe PMC 特异性加分
    if 'europepmc' in source_lower:
        europepmc_pts = 5
        score += europepmc_pts
        reasons.append(ScoreReason(
            category="source_bonus",
            points=europepmc_pts,
            description="Europe PMC 精准检索加分 (+5分)"
        ))
    
    # 3.3 结构突破关键词加权
    breakthrough_matched = [kw for kw in Config.BREAKTHROUGH_KEYWORDS if kw in text]
    if breakthrough_matched:
        breakthrough_points = 15
        score += breakthrough_points
        reasons.append(ScoreReason(
            category="structural_breakthrough",
            points=breakthrough_points,
            description=f"结构突破关键词: {', '.join(breakthrough_matched[:3])} (+{breakthrough_points}分)"
        ))
    
    # 3.4 预印本结构研究加权
    if 'biorxiv' in source_lower and 'structure' in text:
        preprint_structure_points = 10
        score += preprint_structure_points
        reasons.append(ScoreReason(
            category="preprint_structure",
            points=preprint_structure_points,
            description=f"预印本结构研究 (+{preprint_structure_points}分)"
        ))
    
    # --- 4. 期刊影响因子评分 ---
    journal_points = 0
    matched_journal = None
    
    for journal, impact in Config.JOURNAL_IMPACT_MAP.items():
        if journal in source_lower:
            journal_points = impact
            matched_journal = journal
            break
    
    if journal_points > 0:
        score += journal_points
        reasons.append(ScoreReason(
            category="journal_impact",
            points=journal_points,
            description=f"顶级期刊: {matched_journal} (+{journal_points}分)"
        ))
    
    # --- 5. 引用数加权 ---
    citation_count = paper.citation_count or 0
    if citation_count > 0:
        citation_points = citation_count * 2
        score += citation_points
        reasons.append(ScoreReason(
            category="citation",
            points=citation_points,
            description=f"引用数: {citation_count} (+{citation_points}分)"
        ))
    
    # --- 6. 新鲜度补偿 ---
    try:
        if paper.date and paper.date != '' and paper.date != '日期未知':
            paper_date = None
            if '-' in paper.date[:10]:
                try:
                    paper_date = datetime.datetime.strptime(paper.date[:10], '%Y-%m-%d').date()
                except:
                    pass
            elif '/' in paper.date[:10]:
                try:
                    paper_date = datetime.datetime.strptime(paper.date[:10], '%Y/%m/%d').date()
                except:
                    pass
            
            if paper_date:
                today = datetime.date.today()
                days_diff = (today - paper_date).days
                # 增强时间因素：当天论文最高优先级
                if days_diff == 0:  # 当天
                    freshness_points = 10.0  # 最高优先级
                elif days_diff == 1:  # 1天前
                    freshness_points = 5.0
                elif days_diff == 2:  # 2天前
                    freshness_points = 2.0
                elif 3 <= days_diff <= 30:  # 3-30天前
                    freshness_points = max(0, (30 - days_diff) * 0.1)  # 递减
                else:
                    freshness_points = 0.0
                
                if freshness_points > 0:
                    score += freshness_points
                    reasons.append(ScoreReason(
                        category="freshness",
                        points=freshness_points,
                        description=f"新鲜度: {days_diff}天前 (+{freshness_points:.1f}分)"
                    ))
    except Exception:
        pass
    
    return ScoredPaper(paper=paper, score=score, reasons=reasons)




