"""
app/deduplication.py 模块的单元测试
"""
import unittest
from unittest.mock import patch
from app.models import Paper
from app.deduplication import normalize_link, generate_link_hash, get_item_id


class TestNormalizeLink(unittest.TestCase):
    """测试链接标准化函数"""
    
    def test_http_to_https(self):
        """测试 HTTP 转 HTTPS"""
        link = "http://example.com/article"
        result = normalize_link(link)
        self.assertEqual(result, "https://example.com/article")
    
    def test_remove_trailing_slash(self):
        """测试移除尾部斜杠"""
        link = "https://example.com/article/"
        result = normalize_link(link)
        self.assertEqual(result, "https://example.com/article")
    
    def test_lowercase_domain(self):
        """测试域名小写化"""
        link = "https://Example.COM/article"
        result = normalize_link(link)
        self.assertEqual(result, "https://example.com/article")
    
    def test_remove_tracking_params(self):
        """测试移除追踪参数"""
        link = "https://example.com/article?utm_source=test&utm_campaign=test2&id=123"
        result = normalize_link(link)
        # 应该保留 id 参数，移除 utm 参数
        self.assertIn("id=", result)
        self.assertNotIn("utm_source", result)
        self.assertNotIn("utm_campaign", result)
    
    def test_empty_link(self):
        """测试空链接"""
        result = normalize_link("")
        self.assertEqual(result, "")
    
    def test_same_link_different_format(self):
        """测试不同格式的相同链接标准化后一致"""
        link1 = "http://Example.COM/article/?utm_source=test"
        link2 = "https://example.com/article"
        result1 = normalize_link(link1)
        result2 = normalize_link(link2)
        self.assertEqual(result1, result2)


class TestGenerateLinkHash(unittest.TestCase):
    """测试链接哈希生成函数"""
    
    def test_hash_length(self):
        """测试哈希值长度为16位"""
        link = "https://example.com/article"
        result = generate_link_hash(link)
        self.assertEqual(len(result), 16)
    
    def test_same_link_same_hash(self):
        """测试相同链接生成相同哈希"""
        link = "https://example.com/article"
        hash1 = generate_link_hash(link)
        hash2 = generate_link_hash(link)
        self.assertEqual(hash1, hash2)
    
    def test_different_link_different_hash(self):
        """测试不同链接生成不同哈希"""
        link1 = "https://example.com/article1"
        link2 = "https://example.com/article2"
        hash1 = generate_link_hash(link1)
        hash2 = generate_link_hash(link2)
        self.assertNotEqual(hash1, hash2)
    
    def test_normalized_links_same_hash(self):
        """测试标准化后相同的链接生成相同哈希"""
        link1 = "http://Example.COM/article/"
        link2 = "https://example.com/article"
        hash1 = generate_link_hash(link1)
        hash2 = generate_link_hash(link2)
        self.assertEqual(hash1, hash2)


class TestGetItemId(unittest.TestCase):
    """测试去重ID生成函数"""
    
    def test_doi_priority(self):
        """测试 DOI 优先级最高"""
        paper = Paper(
            title="Test Paper",
            abstract="Abstract",
            date="2024-12-28",
            source="TestSource",
            doi="10.1038/s41586-024-12345-6",
            link="https://example.com/article"
        )
        result = get_item_id(paper)
        self.assertTrue(result.startswith("DOI:"))
        self.assertEqual(result, "DOI:10.1038/s41586-024-12345-6")
    
    def test_doi_cleaning(self):
        """测试 DOI 前缀清理"""
        # 测试 https://doi.org/ 前缀
        paper1 = Paper(
            title="Test Paper",
            abstract="Abstract",
            date="2024-12-28",
            source="TestSource",
            doi="https://doi.org/10.1038/s41586-024-12345-6",
            link=""
        )
        result1 = get_item_id(paper1)
        self.assertEqual(result1, "DOI:10.1038/s41586-024-12345-6")
        
        # 测试 doi: 前缀
        paper2 = Paper(
            title="Test Paper",
            abstract="Abstract",
            date="2024-12-28",
            source="TestSource",
            doi="doi:10.1038/s41586-024-12345-6",
            link=""
        )
        result2 = get_item_id(paper2)
        self.assertEqual(result2, "DOI:10.1038/s41586-024-12345-6")
    
    @patch('app.deduplication.Config.ENABLE_LINK_HASH_DEDUP', True)
    def test_link_hash_when_enabled(self):
        """测试启用链接哈希时使用哈希"""
        paper = Paper(
            title="Test Paper",
            abstract="Abstract",
            date="2024-12-28",
            source="TestSource",
            doi="",
            link="https://example.com/article"
        )
        result = get_item_id(paper)
        self.assertTrue(result.startswith("LINK_HASH:"))
        self.assertEqual(len(result.split(":")[1]), 16)
    
    @patch('app.deduplication.Config.ENABLE_LINK_HASH_DEDUP', False)
    def test_link_original_when_disabled(self):
        """测试禁用链接哈希时使用原始链接"""
        paper = Paper(
            title="Test Paper",
            abstract="Abstract",
            date="2024-12-28",
            source="TestSource",
            doi="",
            link="https://example.com/article"
        )
        result = get_item_id(paper)
        self.assertTrue(result.startswith("LINK:"))
        self.assertEqual(result, "LINK:https://example.com/article")
    
    def test_title_fallback(self):
        """测试标题降级去重"""
        paper = Paper(
            title="Test Paper Title",
            abstract="Abstract",
            date="2024-12-28",
            source="TestSource",
            doi="",
            link=""
        )
        result = get_item_id(paper)
        self.assertTrue(result.startswith("TITLE:"))
        self.assertIn("TestSource", result)
    
    def test_title_hash_consistency(self):
        """测试相同标题生成相同哈希"""
        paper1 = Paper(
            title="Test Paper Title",
            abstract="Abstract",
            date="2024-12-28",
            source="TestSource",
            doi="",
            link=""
        )
        paper2 = Paper(
            title="Test Paper Title",
            abstract="Different Abstract",
            date="2024-12-29",
            source="TestSource",
            doi="",
            link=""
        )
        result1 = get_item_id(paper1)
        result2 = get_item_id(paper2)
        self.assertEqual(result1, result2)
    
    def test_none_when_all_empty(self):
        """测试所有字段为空时返回 None"""
        paper = Paper(
            title="",
            abstract="",
            date="",
            source="",
            doi="",
            link=""
        )
        result = get_item_id(paper)
        self.assertIsNone(result)


class TestCrossSourceDeduplication(unittest.TestCase):
    """测试跨数据源去重场景"""
    
    def test_rss_pubmed_same_doi(self):
        """测试 RSS 和 PubMed 返回相同 DOI 的文章能正确去重"""
        # 模拟 RSS 抓取到的论文（含DOI）
        rss_paper = Paper(
            title="Nitrogen fixation in legumes",
            abstract="Abstract from RSS",
            date="2024-12-28",
            source="RSS_TopJournal",
            doi="10.1038/s41477-024-12345-6",
            link="https://www.nature.com/articles/s41477-024-12345-6"
        )
        
        # 模拟 PubMed 抓取到的相同论文
        pubmed_paper = Paper(
            title="Nitrogen fixation in legumes",
            abstract="Abstract from PubMed",
            date="2024-12-28",
            source="PubMed",
            doi="10.1038/s41477-024-12345-6",
            link=""
        )
        
        rss_id = get_item_id(rss_paper)
        pubmed_id = get_item_id(pubmed_paper)
        
        # 两个ID应该相同
        self.assertEqual(rss_id, pubmed_id)
        self.assertEqual(rss_id, "DOI:10.1038/s41477-024-12345-6")


if __name__ == '__main__':
    unittest.main()
