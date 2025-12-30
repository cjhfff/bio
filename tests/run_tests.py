"""
运行所有测试用例
"""
import unittest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入所有测试模块
from tests.test_batch_processing import TestBatchProcessing, TestBatchProcessingIntegration
from tests.test_api_connection import TestAPIConnection
from tests.test_cli_batch_logic import TestCLIBatchLogic


def run_all_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试用例
    suite.addTests(loader.loadTestsFromTestCase(TestBatchProcessing))
    suite.addTests(loader.loadTestsFromTestCase(TestBatchProcessingIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIConnection))
    suite.addTests(loader.loadTestsFromTestCase(TestCLIBatchLogic))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)


