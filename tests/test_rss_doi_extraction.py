"""
RSS 数据源 DOI 提取功能的单元测试
"""
import unittest
from unittest.mock import Mock
from backend.sources.rss import RSSSource


class TestRSSDOIExtraction(unittest.TestCase):
    """测试 RSS 数据源的 DOI 提取功能"""
    
    def setUp(self):
        """初始化测试"""
        self.rss_source = RSSSource(window_days=7)
    
    def test_extract_doi_from_entry_id_with_doi_org(self):
        """测试从 entry.id 提取包含 doi.org 的 DOI"""
        entry = Mock()
        entry.id = "https://doi.org/10.1038/s41586-024-12345-6"
        entry.doi = None
        entry.link = "https://www.nature.com/articles/s41586-024-12345-6"
        
        result = self.rss_source._extract_doi_from_entry(entry)
        self.assertEqual(result, "10.1038/s41586-024-12345-6")
    
    def test_extract_doi_from_entry_id_with_doi_prefix(self):
        """测试从 entry.id 提取以 doi: 开头的 DOI"""
        entry = Mock()
        entry.id = "doi:10.1038/s41586-024-12345-6"
        entry.doi = None
        entry.link = "https://www.nature.com/articles/s41586-024-12345-6"
        
        result = self.rss_source._extract_doi_from_entry(entry)
        self.assertEqual(result, "10.1038/s41586-024-12345-6")
    
    def test_extract_doi_from_entry_doi_field(self):
        """测试从 entry.doi 字段直接提取"""
        entry = Mock()
        entry.id = "some-other-id"
        entry.doi = "10.1038/s41586-024-12345-6"
        entry.link = "https://www.nature.com/articles/s41586-024-12345-6"
        
        result = self.rss_source._extract_doi_from_entry(entry)
        self.assertEqual(result, "10.1038/s41586-024-12345-6")
    
    def test_extract_doi_from_entry_doi_field_with_prefix(self):
        """测试从 entry.doi 字段提取并清理前缀"""
        entry = Mock()
        entry.id = "some-other-id"
        entry.doi = "https://doi.org/10.1038/s41586-024-12345-6"
        entry.link = "https://www.nature.com/articles/s41586-024-12345-6"
        
        result = self.rss_source._extract_doi_from_entry(entry)
        self.assertEqual(result, "10.1038/s41586-024-12345-6")
    
    def test_extract_doi_from_link(self):
        """测试从 entry.link 提取包含 doi.org 的 DOI"""
        entry = Mock()
        entry.id = "some-other-id"
        entry.doi = None
        entry.link = "https://doi.org/10.1038/s41586-024-12345-6"
        
        result = self.rss_source._extract_doi_from_entry(entry)
        self.assertEqual(result, "10.1038/s41586-024-12345-6")
    
    def test_extract_doi_no_doi_found(self):
        """测试无 DOI 信息时返回空字符串"""
        entry = Mock()
        entry.id = "some-article-id"
        entry.doi = None
        entry.link = "https://www.nature.com/articles/s41586-024-12345-6"
        
        result = self.rss_source._extract_doi_from_entry(entry)
        self.assertEqual(result, "")
    
    def test_extract_doi_priority_id_over_doi_field(self):
        """测试 entry.id 优先级高于 entry.doi 字段"""
        entry = Mock()
        entry.id = "https://doi.org/10.1038/id-doi"
        entry.doi = "10.1038/field-doi"
        entry.link = "https://www.nature.com/articles/xxx"
        
        result = self.rss_source._extract_doi_from_entry(entry)
        # 应该使用 entry.id 中的 DOI
        self.assertEqual(result, "10.1038/id-doi")
    
    def test_extract_doi_priority_doi_field_over_link(self):
        """测试 entry.doi 字段优先级高于 entry.link"""
        entry = Mock()
        entry.id = "some-id"
        entry.doi = "10.1038/field-doi"
        entry.link = "https://doi.org/10.1038/link-doi"
        
        result = self.rss_source._extract_doi_from_entry(entry)
        # 应该使用 entry.doi 字段
        self.assertEqual(result, "10.1038/field-doi")
    
    def test_extract_doi_handles_missing_attributes(self):
        """测试处理缺失属性的情况"""
        entry = Mock(spec=[])  # 空 spec，没有任何属性
        
        result = self.rss_source._extract_doi_from_entry(entry)
        self.assertEqual(result, "")
    
    def test_extract_doi_handles_none_values(self):
        """测试处理 None 值的情况"""
        entry = Mock()
        entry.id = None
        entry.doi = None
        entry.link = None
        
        result = self.rss_source._extract_doi_from_entry(entry)
        self.assertEqual(result, "")
    
    def test_extract_doi_handles_empty_strings(self):
        """测试处理空字符串的情况"""
        entry = Mock()
        entry.id = ""
        entry.doi = ""
        entry.link = ""
        
        result = self.rss_source._extract_doi_from_entry(entry)
        self.assertEqual(result, "")
    
    def test_extract_doi_real_nature_format(self):
        """测试真实的 Nature 期刊 RSS entry 格式"""
        # 模拟真实的 Nature Plants entry
        entry = Mock()
        entry.id = "https://doi.org/10.1038/s41477-024-01602-x"
        entry.title = "Nitrogen fixation in legumes"
        entry.link = "https://www.nature.com/articles/s41477-024-01602-x"
        entry.doi = None
        
        result = self.rss_source._extract_doi_from_entry(entry)
        self.assertEqual(result, "10.1038/s41477-024-01602-x")
    
    def test_extract_doi_real_science_format(self):
        """测试真实的 Science 期刊 RSS entry 格式"""
        # 模拟真实的 Science entry
        entry = Mock()
        entry.id = "doi:10.1126/science.abc1234"
        entry.title = "Test Article"
        entry.link = "https://science.sciencemag.org/content/123/456/789"
        entry.doi = None
        
        result = self.rss_source._extract_doi_from_entry(entry)
        self.assertEqual(result, "10.1126/science.abc1234")
    
    def test_extract_doi_real_cell_format(self):
        """测试真实的 Cell 期刊 RSS entry 格式"""
        # 模拟真实的 Cell entry
        entry = Mock()
        entry.id = "https://doi.org/10.1016/j.cell.2024.12.001"
        entry.title = "Test Article"
        entry.link = "https://www.cell.com/cell/fulltext/S0092-8674(24)01234-5"
        entry.doi = None
        
        result = self.rss_source._extract_doi_from_entry(entry)
        self.assertEqual(result, "10.1016/j.cell.2024.12.001")


if __name__ == '__main__':
    unittest.main()
