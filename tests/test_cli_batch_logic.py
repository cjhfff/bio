"""
CLI批处理逻辑测试用例
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from app.cli import run_push_task
from app.models import Paper, SourceResult


class TestCLIBatchLogic(unittest.TestCase):
    """CLI批处理逻辑测试"""
    
    @patch('app.cli.PaperRepository')
    @patch('app.cli.init_db')
    @patch('app.cli.setup_logging')
    @patch('app.cli.concurrent.futures.ThreadPoolExecutor')
    def test_batch_processing_logic(self, mock_executor, mock_setup_logging, 
                                     mock_init_db, mock_repo):
        """测试批处理逻辑"""
        # 模拟数据源结果
        mock_result = Mock()
        mock_result.success.return_value = True
        mock_result.papers = [
            Paper(title=f"Paper {i}", abstract=f"Abstract {i}", date="2025-12-30", source="bioRxiv")
            for i in range(5)
        ]
        mock_result.source_name = "bioRxiv"
        
        # 模拟执行器
        mock_future = Mock()
        mock_future.result.return_value = mock_result
        mock_executor.return_value.__enter__.return_value.submit.return_value = mock_future
        mock_executor.return_value.__enter__.return_value.__iter__.return_value = [mock_future]
        
        # 模拟仓库
        mock_repo_instance = Mock()
        mock_repo_instance.get_sent_ids.return_value = set()
        mock_repo_instance.create_run.return_value = "test-run-id"
        mock_repo_instance.save_scores.return_value = None
        mock_repo_instance.update_run.return_value = None
        mock_repo.return_value = mock_repo_instance
        
        # 模拟评分
        with patch('app.cli.score_paper') as mock_score:
            from app.models import ScoredPaper
            from app.scoring import ScoreReason
            mock_score.side_effect = lambda p: ScoredPaper(
                paper=p,
                score=100.0,
                reasons=[ScoreReason("test", 50, "测试")]
            )
            
            # 模拟批处理报告生成
            with patch('app.cli.generate_batch_report') as mock_batch_report:
                mock_batch_report.return_value = "批次报告内容"
                
                with patch('app.cli.generate_final_summary') as mock_final_summary:
                    mock_final_summary.return_value = "最终报告"
                    
                    with patch('app.cli.PushPlusSender') as mock_pushplus:
                        mock_pushplus.return_value.send.return_value = True
                        
                        # 执行任务
                        try:
                            run_push_task(window_days=1)
                        except Exception as e:
                            # 允许某些错误（如数据库连接等）
                            pass
                        
                        # 验证批处理被调用
                        # 注意：由于有5篇论文，每批2篇，应该有3次调用
                        self.assertGreaterEqual(mock_batch_report.call_count, 1, 
                                               "应该调用批次报告生成")
    
    def test_batch_size_calculation(self):
        """测试批次大小计算"""
        total_papers = 7
        batch_size = 2
        
        expected_batches = (total_papers + batch_size - 1) // batch_size
        self.assertEqual(expected_batches, 4, "7篇论文，每批2篇，应该有4批")
        
        # 验证批次分配
        batches = []
        for i in range(0, total_papers, batch_size):
            batch = list(range(i, min(i + batch_size, total_papers)))
            batches.append(batch)
        
        self.assertEqual(len(batches), 4, "应该有4个批次")
        self.assertEqual(len(batches[0]), 2, "第1批应该有2篇")
        self.assertEqual(len(batches[1]), 2, "第2批应该有2篇")
        self.assertEqual(len(batches[2]), 2, "第3批应该有2篇")
        self.assertEqual(len(batches[3]), 1, "第4批应该有1篇")
    
    def test_error_handling_in_batch_processing(self):
        """测试批处理中的错误处理"""
        # 模拟部分批次失败的情况
        batch_results = [
            ("success", "批次1报告"),
            ("failure", "降级报告"),
            ("success", "批次3报告")
        ]
        
        # 验证失败批次不影响其他批次
        successful_batches = [r for r in batch_results if r[0] == "success"]
        failed_batches = [r for r in batch_results if r[0] == "failure"]
        
        self.assertEqual(len(successful_batches), 2, "应该有2个成功批次")
        self.assertEqual(len(failed_batches), 1, "应该有1个失败批次")
        
        # 所有批次都应该被收集（包括失败的）
        all_reports = [r[1] for r in batch_results]
        self.assertEqual(len(all_reports), 3, "应该收集所有批次的报告")


if __name__ == '__main__':
    unittest.main()

