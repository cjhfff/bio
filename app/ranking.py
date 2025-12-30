"""
排名与选择：合并、去重、TopK选择，包含回退策略
"""
from typing import List, Tuple, Set
from app.models import Paper, ScoredPaper, SourceResult
from app.scoring import score_paper
from app.config import Config
from app.deduplication import get_item_id
import logging

logger = logging.getLogger(__name__)


# 注意：get_item_id 已迁移到 app.deduplication 模块
# 请直接从 app.deduplication 导入


def deduplicate_papers(papers: List[Paper], sent_ids: Set[str]) -> Tuple[List[Paper], Set[str]]:
    """去重：过滤已推送的论文，返回新论文列表和更新后的sent_ids"""
    unseen = []
    new_ids = set()
    
    for paper in papers:
        item_id = get_item_id(paper)
        if item_id and item_id not in sent_ids:
            unseen.append(paper)
            new_ids.add(item_id)
    
    return unseen, new_ids


def get_priority_level(score: float) -> str:
    """
    根据评分返回优先级等级
    P0 (>50分): 突破性工作，自动置顶
    P1 (30-50分): 重要研究，正常推送
    P2 (<30分): 一般研究，可选推送
    """
    if score >= 50:
        return "P0"
    elif score >= 30:
        return "P1"
    else:
        return "P2"


def categorize_by_priority(scored_papers: List[ScoredPaper]) -> dict:
    """
    按优先级分类论文
    返回: {"P0": [...], "P1": [...], "P2": [...]}
    """
    categorized = {"P0": [], "P1": [], "P2": []}
    
    for scored in scored_papers:
        priority = get_priority_level(scored.score)
        categorized[priority].append(scored)
    
    return categorized


def rank_and_select(
    source_results: List[SourceResult],
    sent_ids: Set[str],
    top_k: int = None,
    min_candidates: int = None,
    enable_priority: bool = True
) -> Tuple[List[ScoredPaper], List[str]]:
    """
    合并、去重、评分、选择TopK（支持P0/P1/P2分层）
    
    Args:
        source_results: 各数据源的结果
        sent_ids: 已推送的ID集合
        top_k: 选择Top K篇（默认从Config读取）
        min_candidates: 最小候选数（用于判断是否需要回退）
        enable_priority: 是否启用优先级分层
    
    Returns:
        (top_papers, new_sent_ids): TopK论文列表和新增的sent_ids
    """
    if top_k is None:
        top_k = Config.TOP_K
    if min_candidates is None:
        min_candidates = Config.MIN_CANDIDATES
    
    # 合并所有结果
    all_papers = []
    for result in source_results:
        if result.success():
            all_papers.extend(result.papers)
        else:
            logger.warning(f"数据源 {result.source_name} 失败: {result.error}")
    
    # 去重
    unseen_papers, new_sent_ids = deduplicate_papers(all_papers, sent_ids)
    
    logger.info(f"总抓取论文数: {len(all_papers)}, 未推送论文数: {len(unseen_papers)}")
    
    if not unseen_papers:
        logger.info("今日所有论文均已推送过，无新论文可推送")
        return [], []
    
    # 评分
    scored_papers = []
    for paper in unseen_papers:
        scored = score_paper(paper)
        scored_papers.append(scored)
    
    # 按评分降序排序
    scored_papers.sort(key=lambda x: x.score, reverse=True)
    
    # 智能选择逻辑（如果启用优先级分层）
    if enable_priority:
        categorized = categorize_by_priority(scored_papers)
        logger.info(f"优先级分布: P0={len(categorized['P0'])}篇, P1={len(categorized['P1'])}篇, P2={len(categorized['P2'])}篇")
        
        # 智能选择：P0全部 + P1最多5篇 + P2最多7篇
        # P0论文：全部入选（不设上限，确保不遗漏重要突破）
        p0_selected = sorted(categorized['P0'], key=lambda x: x.score, reverse=True)
        
        # P1论文：最多5篇（按评分排序）
        p1_selected = sorted(categorized['P1'], key=lambda x: x.score, reverse=True)[:5]
        
        # P2论文：最多7篇（按评分排序）
        p2_selected = sorted(categorized['P2'], key=lambda x: x.score, reverse=True)[:7]
        
        # 合并选择结果
        # 重要：P0论文全部入选，不设上限（确保不遗漏重要突破）
        top_papers = p0_selected + p1_selected + p2_selected
        
        # 如果总数超过top_k，优先保证P0全部入选，然后从P1和P2中选择
        if len(top_papers) > top_k:
            # 先保证P0全部入选
            remaining_slots = top_k - len(p0_selected)
            if remaining_slots > 0:
                # 从P1和P2中按评分选择剩余位置
                p1_p2_combined = p1_selected + p2_selected
                p1_p2_combined.sort(key=lambda x: x.score, reverse=True)
                top_papers = p0_selected + p1_p2_combined[:remaining_slots]
            else:
                # 如果P0已经超过top_k，P0全部入选（不截断）
                # 这是合理的，因为P0是"可能被抢发"的重磅文章，必须全部推送
                top_papers = p0_selected
                logger.info(f"P0论文数量({len(p0_selected)})超过TOP_K({top_k})，P0论文将全部入选（不遗漏重要突破）")
        
        # 记录选择详情
        if p0_selected:
            logger.info(f"P0突破性论文 {len(p0_selected)} 篇将自动置顶推送")
        if p1_selected:
            logger.info(f"P1重要论文选择 {len(p1_selected)} 篇（最多5篇）")
        if p2_selected:
            logger.info(f"P2一般论文选择 {len(p2_selected)} 篇（最多7篇）")
    else:
        # 传统方式：简单选择Top K
        top_papers = scored_papers[:top_k]
    
    # 记录新增的sent_ids（只记录TopK的）
    top_sent_ids = []
    for scored in top_papers:
        item_id = get_item_id(scored.paper)
        if item_id:
            top_sent_ids.append(item_id)
    
    # 确保至少推送一篇论文（最低保障）
    if not top_papers and scored_papers:
        logger.warning(f"没有符合Top{top_k}的论文，但至少推送一篇")
        top_papers = [scored_papers[0]]
        item_id = get_item_id(top_papers[0].paper)
        if item_id:
            top_sent_ids = [item_id]
    
    logger.info(f"已选择Top {len(top_papers)}篇论文进行推送")
    
    # 输出详细分层信息
    if enable_priority and top_papers:
        p0_count = sum(1 for p in top_papers if get_priority_level(p.score) == "P0")
        p1_count = sum(1 for p in top_papers if get_priority_level(p.score) == "P1")
        p2_count = sum(1 for p in top_papers if get_priority_level(p.score) == "P2")
        logger.info(f"Top{len(top_papers)}中包含: P0={p0_count}篇, P1={p1_count}篇, P2={p2_count}篇")
    
    return top_papers, top_sent_ids

