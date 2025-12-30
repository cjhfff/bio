"""
批处理功能测试用例
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from typing import List
from app.models import Paper, ScoredPaper
from app.llm.generator import generate_batch_report, generate_final_summary, prepare_papers_for_llm
from app.scoring import ScoreReason
import datetime


class TestBatchProcessing(unittest.TestCase):
    """批处理功能测试"""
    
    def setUp(self):
        """设置测试数据"""
        # 创建测试论文
        self.paper1 = Paper(
            title="Test Paper 1: Structural basis for enzyme mechanism",
            abstract="This paper studies the structural basis of enzyme mechanism using cryo-EM.",
            date="2025-12-30",
            source="bioRxiv",
            doi="10.1234/test1",
            link="https://example.com/paper1"
        )
        
        self.paper2 = Paper(
            title="Test Paper 2: Signal transduction in plant immunity",
            abstract="This paper investigates signal transduction mechanisms in plant immune receptors.",
            date="2025-12-30",
            source="PubMed",
            doi="10.1234/test2",
            link="https://example.com/paper2"
        )
        
        self.paper3 = Paper(
            title="Test Paper 3: Nitrogen fixation in rhizobia",
            abstract="This paper explores nitrogen fixation mechanisms in rhizobia-legume symbiosis.",
            date="2025-12-29",
            source="bioRxiv",
            doi="10.1234/test3",
            link="https://example.com/paper3"
        )
        
        # 创建带评分的论文
        self.scored_paper1 = ScoredPaper(
            paper=self.paper1,
            score=135.0,
            reasons=[
                ScoreReason("keyword_match", 80, "命中结构核心词: cryo-em"),
                ScoreReason("core_content", 20, "直接命中三大研究方向核心内容"),
                ScoreReason("freshness", 10.0, "新鲜度: 0天前")
            ]
        )
        
        self.scored_paper2 = ScoredPaper(
            paper=self.paper2,
            score=124.0,
            reasons=[
                ScoreReason("keyword_match", 60, "命中信号转导核心词"),
                ScoreReason("core_content", 20, "直接命中三大研究方向核心内容"),
                ScoreReason("freshness", 10.0, "新鲜度: 0天前")
            ]
        )
        
        self.scored_paper3 = ScoredPaper(
            paper=self.paper3,
            score=100.0,
            reasons=[
                ScoreReason("keyword_match", 70, "命中固氮核心词"),
                ScoreReason("core_content", 20, "直接命中三大研究方向核心内容"),
                ScoreReason("freshness", 5.0, "新鲜度: 1天前")
            ]
        )
    
    def test_prepare_papers_for_llm_batch_mode(self):
        """测试批量模式下的论文准备"""
        scored_papers = [self.scored_paper1, self.scored_paper2]
        
        papers_text, count, tokens = prepare_papers_for_llm(scored_papers, batch_size=2)
        
        # 验证返回结果
        self.assertEqual(count, 2, "应该包含2篇论文")
        self.assertGreater(tokens, 0, "Token数应该大于0")
        self.assertIn("论文 1", papers_text, "应该包含论文1")
        self.assertIn("论文 2", papers_text, "应该包含论文2")
        self.assertIn(self.paper1.title, papers_text, "应该包含论文1的标题")
        self.assertIn(self.paper2.title, papers_text, "应该包含论文2的标题")
        self.assertIn("评分: 135.0分", papers_text, "应该包含论文1的评分")
        self.assertIn("评分: 124.0分", papers_text, "应该包含论文2的评分")
        self.assertIn("发布时间: 2025-12-30", papers_text, "应该包含日期")
    
    def test_prepare_papers_for_llm_single_paper(self):
        """测试单篇论文准备"""
        scored_papers = [self.scored_paper1]
        
        papers_text, count, tokens = prepare_papers_for_llm(scored_papers, batch_size=1)
        
        self.assertEqual(count, 1, "应该包含1篇论文")
        self.assertIn(self.paper1.title, papers_text, "应该包含论文标题")
        self.assertIn(self.paper1.abstract, papers_text, "应该包含完整摘要")
    
    def test_prepare_papers_for_llm_empty_list(self):
        """测试空论文列表"""
        papers_text, count, tokens = prepare_papers_for_llm([], batch_size=2)
        
        self.assertEqual(count, 0, "应该返回0篇论文")
        self.assertEqual(tokens, 0, "Token数应该为0")
        self.assertEqual(papers_text, "", "文本应该为空")
    
    @patch('app.llm.generator.OpenAI')
    def test_generate_batch_report_success(self, mock_openai):
        """测试批次报告生成成功"""
        # 模拟API响应
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "这是测试报告内容"
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        scored_papers = [self.scored_paper1, self.scored_paper2]
        result = generate_batch_report(scored_papers, batch_num=1)
        
        self.assertIsNotNone(result, "应该返回报告内容")
        self.assertIn("测试报告内容", result, "应该包含API返回的内容")
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('app.llm.generator.OpenAI')
    def test_generate_batch_report_api_failure(self, mock_openai):
        """测试批次报告生成失败（API错误）"""
        # 模拟API失败
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Connection error")
        mock_openai.return_value = mock_client
        
        scored_papers = [self.scored_paper1, self.scored_paper2]
        result = generate_batch_report(scored_papers, batch_num=1)
        
        # 应该返回降级报告
        self.assertIsNotNone(result, "应该返回降级报告")
        self.assertIn("报告生成说明", result, "应该包含降级报告标识")
        self.assertIn(self.paper1.title, result, "降级报告应该包含论文信息")
    
    def test_generate_batch_report_empty_papers(self):
        """测试空论文列表的批次报告生成"""
        result = generate_batch_report([], batch_num=1)
        
        self.assertEqual(result, "", "空论文列表应该返回空字符串")
    
    def test_generate_batch_report_more_than_two_papers(self):
        """测试超过2篇论文的批次处理"""
        scored_papers = [self.scored_paper1, self.scored_paper2, self.scored_paper3]
        
        # 应该只处理前2篇
        papers_text, count, tokens = prepare_papers_for_llm(scored_papers, batch_size=2)
        
        self.assertEqual(count, 2, "应该只处理2篇论文")
        self.assertIn(self.paper1.title, papers_text, "应该包含论文1")
        self.assertIn(self.paper2.title, papers_text, "应该包含论文2")
        self.assertNotIn(self.paper3.title, papers_text, "不应该包含论文3")
    
    @patch('app.llm.generator.OpenAI')
    def test_generate_final_summary_success(self, mock_openai):
        """测试最终总结报告生成成功"""
        # 模拟API响应
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "这是最终总结报告"
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        batch_reports = [
            "批次1详细分析内容",
            "批次2详细分析内容"
        ]
        
        result = generate_final_summary(batch_reports, total_papers=4)
        
        self.assertIsNotNone(result, "应该返回最终报告")
        self.assertIn("最终总结报告", result, "应该包含API返回的内容")
    
    @patch('app.llm.generator.OpenAI')
    def test_generate_final_summary_api_failure(self, mock_openai):
        """测试最终总结报告生成失败"""
        # 模拟API失败
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Connection error")
        mock_openai.return_value = mock_client
        
        batch_reports = [
            "批次1详细分析内容",
            "批次2详细分析内容"
        ]
        
        result = generate_final_summary(batch_reports, total_papers=4)
        
        # 应该返回简单拼接的报告
        self.assertIsNotNone(result, "应该返回拼接报告")
        self.assertIn("批次1详细分析内容", result, "应该包含批次1内容")
        self.assertIn("批次2详细分析内容", result, "应该包含批次2内容")
        self.assertIn("未进行总结归纳", result, "应该说明未进行总结")
    
    def test_generate_final_summary_empty_reports(self):
        """测试空报告列表的最终总结"""
        result = generate_final_summary([], total_papers=0)
        
        self.assertIn("未发现相关论文", result, "应该返回提示信息")


class TestBatchProcessingIntegration(unittest.TestCase):
    """批处理集成测试"""
    
    def test_batch_processing_workflow(self):
        """测试完整的批处理工作流程"""
        # 创建多篇论文
        papers = []
        for i in range(5):
            paper = Paper(
                title=f"Test Paper {i+1}",
                abstract=f"Abstract for paper {i+1}",
                date="2025-12-30",
                source="bioRxiv",
                doi=f"10.1234/test{i+1}"
            )
            scored = ScoredPaper(
                paper=paper,
                score=100.0 - i * 10,
                reasons=[ScoreReason("test", 50, "测试理由")]
            )
            papers.append(scored)
        
        # 测试分批逻辑
        batch_size = 2
        batches = []
        for i in range(0, len(papers), batch_size):
            batch = papers[i:i + batch_size]
            batches.append(batch)
        
        # 验证批次分配
        self.assertEqual(len(batches), 3, "应该有3个批次")
        self.assertEqual(len(batches[0]), 2, "第1批应该有2篇")
        self.assertEqual(len(batches[1]), 2, "第2批应该有2篇")
        self.assertEqual(len(batches[2]), 1, "第3批应该有1篇")
        
        # 验证每批论文准备
        for i, batch in enumerate(batches, 1):
            papers_text, count, tokens = prepare_papers_for_llm(batch, batch_size=batch_size)
            self.assertEqual(count, len(batch), f"批次{i}应该包含正确数量的论文")
            self.assertGreater(tokens, 0, f"批次{i}的Token数应该大于0")


if __name__ == '__main__':
    unittest.main()

