"""
API连接稳定性测试用例
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import time
from backend.config import Config
from backend.llm.generator import generate_batch_report
from backend.models import Paper, ScoredPaper
from backend.scoring import ScoreReason


class TestAPIConnection(unittest.TestCase):
    """API连接稳定性测试"""
    
    def setUp(self):
        """设置测试数据"""
        self.paper = Paper(
            title="Test Paper",
            abstract="Test abstract",
            date="2025-12-30",
            source="bioRxiv"
        )
        self.scored_paper = ScoredPaper(
            paper=self.paper,
            score=100.0,
            reasons=[ScoreReason("test", 50, "测试")]
        )
    
    def test_api_timeout_config(self):
        """测试API超时配置"""
        self.assertGreaterEqual(Config.API_TIMEOUT, 300, "超时时间应该至少300秒")
        self.assertLessEqual(Config.API_TIMEOUT, 1200, "超时时间不应该超过1200秒")
    
    def test_api_retry_config(self):
        """测试API重试配置"""
        self.assertGreaterEqual(Config.API_MAX_RETRIES, 2, "重试次数应该至少2次")
        self.assertLessEqual(Config.API_MAX_RETRIES, 5, "重试次数不应该超过5次")
    
    def test_retry_delay_calculation(self):
        """测试重试延迟计算（指数退避）"""
        base_delay = Config.API_RETRY_BASE_DELAY
        max_delay = Config.API_RETRY_MAX_DELAY
        
        # 测试指数退避计算
        for attempt in range(5):
            delay = min(base_delay * (2 ** attempt), max_delay)
            self.assertGreaterEqual(delay, base_delay, f"第{attempt+1}次重试延迟应该>=基础延迟")
            self.assertLessEqual(delay, max_delay, f"第{attempt+1}次重试延迟应该<=最大延迟")
    
    @patch('app.llm.generator.OpenAI')
    def test_api_retry_on_connection_error(self, mock_openai):
        """测试连接错误时的重试机制"""
        # 模拟前2次失败，第3次成功
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "成功响应"
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            Exception("Connection error"),
            Exception("Connection error"),
            mock_response
        ]
        mock_openai.return_value = mock_client
        
        scored_papers = [self.scored_paper]
        result = generate_batch_report(scored_papers, batch_num=1)
        
        # 应该重试并最终成功
        self.assertEqual(mock_client.chat.completions.create.call_count, 3, "应该重试3次")
        self.assertIn("成功响应", result, "应该返回成功响应")
    
    @patch('app.llm.generator.OpenAI')
    def test_api_key_switching(self, mock_openai):
        """测试API密钥切换机制"""
        # 模拟第一个密钥失败，第二个密钥成功
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "备用密钥成功"
        
        def create_side_effect(*args, **kwargs):
            # 根据api_key判断使用哪个密钥
            if hasattr(create_side_effect, 'call_count'):
                create_side_effect.call_count += 1
            else:
                create_side_effect.call_count = 1
            
            if create_side_effect.call_count <= 3:  # 第一个密钥的3次重试都失败
                raise Exception("Connection error")
            else:  # 第二个密钥成功
                return mock_response
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = create_side_effect
        mock_openai.return_value = mock_client
        
        scored_papers = [self.scored_paper]
        result = generate_batch_report(scored_papers, batch_num=1)
        
        # 应该尝试多个密钥
        self.assertGreater(mock_client.chat.completions.create.call_count, 3, "应该尝试多个密钥")
        self.assertIn("备用密钥成功", result, "应该使用备用密钥成功")
    
    @patch('app.llm.generator.OpenAI')
    def test_fresh_client_instance(self, mock_openai):
        """测试每次重试都创建新的客户端实例"""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "成功"
        
        call_count = {'count': 0}
        
        def create_client(*args, **kwargs):
            call_count['count'] += 1
            client = MagicMock()
            if call_count['count'] == 1:
                client.chat.completions.create.side_effect = Exception("Connection error")
            else:
                client.chat.completions.create.return_value = mock_response
            return client
        
        mock_openai.side_effect = create_client
        
        scored_papers = [self.scored_paper]
        result = generate_batch_report(scored_papers, batch_num=1)
        
        # 应该创建多个客户端实例
        self.assertGreater(mock_openai.call_count, 1, "应该创建多个客户端实例")
        self.assertIn("成功", result, "应该最终成功")


if __name__ == '__main__':
    unittest.main()

