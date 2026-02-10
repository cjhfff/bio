"""
命令行入口
"""
import os
# 在导入任何网络库之前，先清除代理设置
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('all_proxy', None)
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('ALL_PROXY', None)

import argparse
import concurrent.futures
import datetime
import logging
from typing import List
from backend.core.config import Config
from backend.core.logging import setup_logging, get_logger
from backend.storage import init_db, PaperRepository
from backend.sources import (
    BioRxivSource, PubMedSource, RSSSource, EuropePMCSource,
    ScienceNewsSource, GitHubSource, SemanticScholarSource
)
from backend.core.ranking import rank_and_select, get_item_id
from backend.llm import generate_daily_report, generate_final_summary
from backend.push import PushPlusSender, EmailSender, WeComSender

logger = get_logger(__name__)


def run_push_task(window_days: int = None, top_k: int = None):
    """执行推送任务"""
    window_days = window_days or Config.DEFAULT_WINDOW_DAYS
    top_k = top_k or Config.TOP_K
    
    # 初始化数据库
    init_db()
    repo = PaperRepository()
    
    # 创建运行记录（在配置日志之前，以便日志文件名包含 run_id）
    run_id = repo.create_run(window_days)
    
    # 重新配置日志，使用 run_id 生成独立的日志文件
    setup_logging(run_id=run_id)
    logger = get_logger(__name__)
    
    logger.info("=" * 80)
    logger.info("开始执行生物化学研究资讯抓取与推送")
    logger.info(f"抓取窗口：{window_days}天（EuropePMC {Config.EUROPEPMC_WINDOW_DAYS}天），其余数据源均为近{window_days}天")
    logger.info("=" * 80)
    logger.info(f"运行ID: {run_id}")
    
    try:
        # 获取已处理的论文ID（去重用），避免多次点击导致重复计数
        logger.info("正在获取已处理论文ID以进行去重...")
        sent_ids = repo.get_sent_ids()
        logger.info(f"已处理 {len(sent_ids)} 篇论文")
        
        # 定义数据源
        # 注：暂时禁用 Semantic Scholar（API限流严重）和 ScienceNews（RSS源失效）
        sources = [
            BioRxivSource(window_days),
            PubMedSource(window_days),
            RSSSource(window_days),
            EuropePMCSource(Config.EUROPEPMC_WINDOW_DAYS),
            # ScienceNewsSource(window_days),  # 暂时禁用：RSS源返回404
            GitHubSource(window_days),
            # SemanticScholarSource(window_days),  # 暂时禁用：API限流严重，导致超时
        ]
        
        # 并发抓取（传入已存在的ID进行去重，避免重复计数）
        logger.info("\n开始并发抓取数据...")
        source_results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(sources)) as executor:
            future_to_source = {
                # 传入 repo.get_sent_ids() 获取的集合
                executor.submit(source.fetch, sent_ids, Config.EXCLUDE_KEYWORDS): source
                for source in sources
            }
            
            for future in concurrent.futures.as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    result = future.result()
                    source_results.append(result)
                    logger.info(f"{source.name}: 获取到 {len(result.papers)} 条结果")
                except Exception as e:
                    logger.error(f"{source.name} 搜索失败: {e}")
                    source_results.append(
                        type('SourceResult', (), {'source_name': source.name, 'papers': [], 'error': str(e)})()
                    )
        
        # 合并与筛选
        logger.info("\n开始合并与筛选...")
        
        # 获取所有论文（用于评分，不进行去重）
        all_papers = []
        for result in source_results:
            if result.success():
                all_papers.extend(result.papers)
        
        # 对当天所有论文进行评分
        logger.info(f"\n对当天所有论文进行评分（共{len(all_papers)}篇）...")
        from backend.core.scoring import score_paper
        all_scored_papers = [score_paper(p) for p in all_papers]
        
        # 按评分排序
        all_scored_papers.sort(key=lambda x: x.score, reverse=True)
        
        if not all_scored_papers:
            logger.info("当天没有新论文需要推送")
            repo.update_run(run_id, status='completed')
            return
        
        # 快速AI预筛选：对高分论文进行快速判断
        logger.info(f"\n开始快速AI预筛选（对高分论文进行相关性判断）...")
        from backend.llm.quick_check import quick_relevance_check
        from backend.models import ScoreReason
        
        RELEVANCE_CHECK_THRESHOLD = Config.QUICK_FILTER_THRESHOLD  # 从配置读取阈值
        # 动态调整阈值：论文数量少时降低阈值，避免漏掉相关论文
        if len(all_scored_papers) <= 5:
            RELEVANCE_CHECK_THRESHOLD = max(RELEVANCE_CHECK_THRESHOLD - 15, 20)
            logger.info(f"论文数量较少（{len(all_scored_papers)}篇），动态降低筛选阈值至 {RELEVANCE_CHECK_THRESHOLD}分")
        elif len(all_scored_papers) <= 10:
            RELEVANCE_CHECK_THRESHOLD = max(RELEVANCE_CHECK_THRESHOLD - 10, 30)
            logger.info(f"论文数量较少（{len(all_scored_papers)}篇），动态降低筛选阈值至 {RELEVANCE_CHECK_THRESHOLD}分")
        logger.info(f"快速筛选阈值: {RELEVANCE_CHECK_THRESHOLD}分（只对≥{RELEVANCE_CHECK_THRESHOLD}分的论文进行AI判断）")
        filtered_papers = []
        filtered_count = 0
        checked_count = 0
        
        for scored_paper in all_scored_papers:
            if scored_paper.score >= RELEVANCE_CHECK_THRESHOLD:
                checked_count += 1
                # 对高分论文进行快速AI判断
                is_relevant = quick_relevance_check(scored_paper.paper)
                
                if is_relevant is False:
                    # 不相关，直接过滤（不添加到列表中）
                    logger.info(f"⏭️ [快速筛选] 论文 '{scored_paper.paper.title[:60]}...' (评分: {scored_paper.score:.1f}) 被判断为不相关，已直接过滤")
                    filtered_count += 1
                    continue  # 跳过，不添加到filtered_papers
                elif is_relevant is None:
                    # 判断失败，保留论文（保守策略，避免误过滤）
                    logger.warning(f"⚠️ [快速筛选] 论文 '{scored_paper.paper.title[:60]}...' AI判断失败，保留论文（保守策略）")
                    filtered_papers.append(scored_paper)
                else:
                    # 相关，保留
                    filtered_papers.append(scored_paper)
            else:
                # 低分论文，直接保留（不进行快速检查，节省API调用）
                filtered_papers.append(scored_paper)
        
        # 重新排序
        filtered_papers.sort(key=lambda x: x.score, reverse=True)
        all_scored_papers = filtered_papers
        
        if checked_count > 0:
            logger.info(f"✅ [快速筛选] 完成：检查了 {checked_count} 篇高分论文，过滤了 {filtered_count} 篇不相关论文，保留了 {len(all_scored_papers)} 篇论文")
        
        # 保存所有论文的评分
        logger.info(f"保存所有论文的评分（共{len(all_scored_papers)}篇）...")
        repo.save_scores(run_id, all_scored_papers)
        
        # 更新运行记录
        repo.update_run(
            run_id,
            total_papers=sum(len(r.papers) for r in source_results),
            unseen_papers=len(all_papers),
            top_k=len(all_scored_papers),  # 所有论文都处理
            status='running'
        )
        
        # 单篇处理模式：一篇一篇处理
        logger.info(f"\n开始单篇处理模式：共 {len(all_scored_papers)} 篇论文，逐篇处理")
        
        all_paper_reports = []
        processed_papers = []  # 记录成功处理的论文
        
        for paper_idx, scored_paper in enumerate(all_scored_papers, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"处理论文 {paper_idx}/{len(all_scored_papers)}")
            logger.info(f"标题: {scored_paper.paper.title[:80]}...")
            logger.info(f"评分: {scored_paper.score:.1f}分")
            logger.info(f"{'='*80}\n")
            
            try:
                # 生成单篇论文报告（包含错误处理和重试机制）
                from backend.llm.generator import generate_single_paper_report
                paper_report = generate_single_paper_report(scored_paper, paper_idx)
                
                # 检查是否是降级报告
                is_fallback = paper_report and paper_report.startswith("## ⚠️ 报告生成说明")
                # 检查是否是不相关论文
                is_irrelevant = paper_report and paper_report.startswith("## 不相关论文")
                
                if is_irrelevant:
                    # 不相关论文，添加到报告中但单独标记（不标记为已推送）
                    all_paper_reports.append(paper_report)
                    logger.info(f"⏭️ 论文 {paper_idx} 不属于三大研究方向，已添加到报告但标记为不相关")
                elif paper_report and not is_fallback:
                    # 成功生成AI报告
                    all_paper_reports.append(paper_report)
                    # 记录成功处理的论文
                    processed_papers.append(scored_paper)
                    logger.info(f"✅ 论文 {paper_idx} 处理成功（AI分析完成）")
                else:
                    # 降级报告（API调用失败），仍然添加到报告中，但不标记为已推送
                    all_paper_reports.append(paper_report)
                    logger.warning(f"⚠️ 论文 {paper_idx} 使用降级报告（API调用失败），论文将不会标记为已推送，下次运行时会重新处理")
                
            except Exception as e:
                logger.error(f"❌ 论文 {paper_idx} 处理失败: {e}", exc_info=True)
                # 即使失败，也生成一个简单的降级报告
                from backend.llm.generator import _generate_fallback_report
                fallback_report = _generate_fallback_report([scored_paper], e)
                all_paper_reports.append(fallback_report)
                # 失败的论文不标记为已推送，下次会重新处理
                logger.warning(f"论文 {paper_idx} 将不会标记为已推送，下次运行时会重新处理")
        
        # 直接合并所有单篇报告（不生成最终总结）
        logger.info(f"\n{'='*80}")
        logger.info("所有论文处理完成，开始生成最终报告...")
        logger.info(f"{'='*80}\n")
        
        # 分离相关论文和不相关论文
        relevant_reports = []
        irrelevant_reports = []
        
        for report in all_paper_reports:
            if report.startswith("## 不相关论文"):
                irrelevant_reports.append(report)
            else:
                relevant_reports.append(report)
        
        # 构建报告
        if relevant_reports or irrelevant_reports:
            daily_report = "## 📊 今日研究总结\n\n"
            
            # 相关论文部分
            if relevant_reports:
                daily_report += f"### ✅ 相关论文（共 {len(relevant_reports)} 篇）\n\n"
                # 规范化报告格式：修复标题格式不一致问题（## 改为 ###）
                normalized_reports = []
                for report in relevant_reports:
                    # 修复标题格式：将 "## 【论文标题】" 改为 "### 【论文标题】"
                    normalized_report = report.replace("## 【论文标题】", "### 【论文标题】")
                    normalized_reports.append(normalized_report)
                daily_report += "\n\n".join([f"## 论文 {i} 重要研究成果\n\n{report}" 
                                            for i, report in enumerate(normalized_reports, 1)])
            
            # 不相关论文部分
            if irrelevant_reports:
                if relevant_reports:
                    daily_report += "\n\n---\n\n"
                daily_report += f"### ⏭️ 已过滤论文（共 {len(irrelevant_reports)} 篇，不属于三大研究方向）\n\n"
                # 规范化不相关论文格式：将 "## 不相关论文" 改为 "### 不相关论文"
                normalized_irrelevant = []
                for report in irrelevant_reports:
                    normalized = report.replace("## 不相关论文", "### 不相关论文")
                    normalized = normalized.replace("## 【论文标题】", "### 【论文标题】")
                    normalized_irrelevant.append(normalized)
                daily_report += "\n\n".join([f"## 已过滤论文 {i}\n\n{report}"
                                            for i, report in enumerate(normalized_irrelevant, 1)])
        else:
            daily_report = "## 📊 今日研究总结\n\n本次检索范围内未发现相关论文。"
        
        # 保存报告到文件（传入分类统计信息）
        save_report_to_file(daily_report, len(all_scored_papers), source_results, run_id,
                            relevant_count=len(relevant_reports), irrelevant_count=len(irrelevant_reports))
        
        # 推送最终报告（不标记已推送，每次运行内容一致）
        logger.info("\n开始推送最终报告...")
        push_success = False
        
        # PushPlus
        pushplus_sender = PushPlusSender()
        if pushplus_sender.send("生物化学研究精选论文", daily_report):
            push_success = True
        
        # 邮件
        email_sender = EmailSender()
        if email_sender.send("生物化学研究精选论文", daily_report):
            push_success = True
        
        # 企业微信
        wecom_sender = WeComSender()
        if wecom_sender.send("生物化学研究精选论文", daily_report):
            push_success = True
        
        logger.info(f"\n推送完成：处理 {len(processed_papers)} 篇论文，共 {len(all_paper_reports)} 篇论文报告（未标记已推送，下次运行将重新处理）")
        
        # 更新运行记录
        repo.update_run(run_id, status='completed' if push_success else 'failed')
        
        logger.info("\n" + "=" * 80)
        logger.info("执行完成！")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        repo.update_run(run_id, status='failed', error=str(e))
        raise


def save_report_to_file(content: str, papers_count: int, source_results: List, run_id: str,
                        relevant_count: int = 0, irrelevant_count: int = 0):
    """保存报告到文件"""
    from pathlib import Path

    today = datetime.date.today().strftime('%Y%m%d')
    filename = f"data/reports/生化领域突破汇总_{today}.txt"

    try:
        # 确保 reports 目录存在
        report_path = Path(filename)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        sources_info = [f"{r.source_name}({len(r.papers)})" for r in source_results]
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"运行ID: {run_id}\n")
            f.write(f"论文总数: {papers_count}（相关: {relevant_count} 篇，已过滤: {irrelevant_count} 篇）\n")
            f.write(f"数据源: {', '.join(sources_info)}\n")
            f.write("=" * 80 + "\n\n")
            f.write(content)
        logger.info(f"\n报告已保存到: {filename}")
    except Exception as e:
        logger.error(f"保存文件失败: {e}")


def test_sources(source_name: str = None):
    """
    测试数据源
    
    Args:
        source_name: 要测试的数据源名称（可选）。如果为 None，则测试所有数据源。
                    可选值: 'biorxiv', 'pubmed', 'rss', 'europepmc', 'sciencenews', 
                           'github', 'semanticscholar'
    """
    logger.info("=" * 80)
    if source_name:
        logger.info(f"开始测试数据源: {source_name}")
    else:
        logger.info("开始测试所有数据源")
    logger.info("=" * 80)
    
    init_db()
    # 不进行去重，测试时处理所有检索到的论文
    logger.info("测试模式：处理所有检索到的论文（不进行去重）")
    
    # 定义所有数据源
    all_sources = {
        'biorxiv': ("bioRxiv", BioRxivSource(Config.DEFAULT_WINDOW_DAYS)),
        'pubmed': ("PubMed", PubMedSource(Config.DEFAULT_WINDOW_DAYS)),
        'rss': ("RSS", RSSSource(Config.DEFAULT_WINDOW_DAYS)),
        'europepmc': ("Europe PMC", EuropePMCSource(Config.EUROPEPMC_WINDOW_DAYS)),
        'sciencenews': ("Science News", ScienceNewsSource(Config.DEFAULT_WINDOW_DAYS)),
        'github': ("GitHub", GitHubSource(Config.DEFAULT_WINDOW_DAYS)),
        'semanticscholar': ("Semantic Scholar", SemanticScholarSource(Config.DEFAULT_WINDOW_DAYS)),
    }
    
    # 如果指定了数据源，只测试该数据源
    if source_name:
        source_name_lower = source_name.lower()
        if source_name_lower not in all_sources:
            logger.error(f"未知的数据源: {source_name}")
            logger.info(f"可用的数据源: {', '.join(all_sources.keys())}")
            return
        sources = [(all_sources[source_name_lower][0], all_sources[source_name_lower][1])]
    else:
        # 测试所有数据源（排除已禁用的）
        sources = [
            ("bioRxiv", BioRxivSource(Config.DEFAULT_WINDOW_DAYS)),
            ("PubMed", PubMedSource(Config.DEFAULT_WINDOW_DAYS)),
            ("RSS", RSSSource(Config.DEFAULT_WINDOW_DAYS)),
            ("Europe PMC", EuropePMCSource(Config.EUROPEPMC_WINDOW_DAYS)),
            # ("Science News", ScienceNewsSource(Config.DEFAULT_WINDOW_DAYS)),  # 暂时禁用：RSS源失效
            ("GitHub", GitHubSource(Config.DEFAULT_WINDOW_DAYS)),
            # ("Semantic Scholar", SemanticScholarSource(Config.DEFAULT_WINDOW_DAYS)),  # 暂时禁用：API限流严重
        ]
    
    results = {}
    for name, source in sources:
        logger.info(f"\n测试数据源: {name}")
        logger.info(f"  时间窗口: {source.window_days} 天")
        if hasattr(source, 'max_pages'):
            logger.info(f"  最大页数: {source.max_pages}")
        
        try:
            result = source.fetch(set(), Config.EXCLUDE_KEYWORDS)  # 传入空集合，不进行去重
            success = result.success()
            count = len(result.papers)
            results[name] = {"success": success, "count": count, "error": result.error}
            
            if success:
                logger.info(f"✅ {name} 测试成功，获取到 {count} 条结果")
                if count > 0:
                    # 显示前3条结果作为示例
                    for i, paper in enumerate(result.papers[:3], 1):
                        logger.info(f"  示例 {i}: {paper.title[:60]}...")
            else:
                logger.error(f"❌ {name} 测试失败: {result.error}")
        except Exception as e:
            logger.error(f"❌ {name} 测试失败: {e}", exc_info=True)
            results[name] = {"success": False, "count": 0, "error": str(e)}
    
    logger.info("\n" + "=" * 80)
    logger.info("测试结果汇总")
    logger.info("=" * 80)
    for name, result in results.items():
        status = "✅ 成功" if result["success"] else "❌ 失败"
        logger.info(f"{name:20s} {status:10s} 结果数: {result['count']}")
        if not result["success"] and result.get("error"):
            logger.info(f"{'':20s} {'':10s} 错误: {result['error'][:100]}")


def main():
    """主入口"""
    parser = argparse.ArgumentParser(description="智能论文推送系统")
    parser.add_argument('command', choices=['run', 'test-sources'], help='命令')
    parser.add_argument('--window-days', type=int, help='抓取窗口天数（默认7天）')
    parser.add_argument('--top-k', type=int, help='选择Top K篇（默认5篇）')
    parser.add_argument('--source', type=str, help='测试单个数据源（仅用于test-sources命令）。可选值: biorxiv, pubmed, rss, europepmc, sciencenews, github, semanticscholar')
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging()
    
    # 验证配置
    errors = Config.validate()
    if errors:
        logger.error("配置错误:")
        for error in errors:
            logger.error(f"  - {error}")
        return
    
    # 代理已在文件开头清除
    
    if args.command == 'run':
        run_push_task(args.window_days, args.top_k)
    elif args.command == 'test-sources':
        test_sources(args.source)


if __name__ == "__main__":
    main()

