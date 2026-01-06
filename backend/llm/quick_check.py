"""
快速AI预筛选：判断论文是否属于三大研究方向
"""
import logging
import time
from typing import Optional
from openai import OpenAI
from backend.models import Paper
from backend.core.config import Config

logger = logging.getLogger(__name__)


def quick_relevance_check(paper: Paper, max_retries: int = 2) -> Optional[bool]:
    """
    快速判断论文是否属于三大研究方向
    
    Args:
        paper: 论文对象
        max_retries: 最大重试次数
        
    Returns:
        True: 属于三大方向
        False: 不属于三大方向
        None: 判断失败（API错误等）
    """
    # 构建简化的提示词（只判断是否相关，不生成详细报告）
    prompt = f"""请快速判断以下论文是否属于以下三个研究方向之一：

1. 生物固氮（Biological Nitrogen Fixation）
2. 胞外信号感知与传递（Extracellular Signal Perception and Transduction，包含细胞膜表面受体/PRR/RLK 介导的 PTI 等植物免疫信号）
3. 酶的结构与作用机制（Enzyme Structure and Mechanism）

**论文信息：**
标题: {paper.title}
摘要: {paper.abstract[:500] if paper.abstract else "无摘要"}

**要求：**
- 只回答 "是" 或 "否"
- 如果论文属于三大研究方向之一，回答 "是"
- 如果论文不属于三大研究方向（例如：癌症研究、临床医学、植物发育、微生物生态等），回答 "否"

**只回答一个字：是 或 否**
"""
    
    # 获取所有 API 密钥
    all_api_keys = Config.get_all_api_keys()
    
    for key_index, api_key in enumerate(all_api_keys):
        key_name = "主密钥" if key_index == 0 else f"备用密钥{key_index}"
        
        for attempt in range(max_retries):
            try:
                # 创建新的客户端实例
                client = OpenAI(
                    api_key=api_key,
                    base_url=Config.DEEPSEEK_BASE_URL,
                    timeout=30,  # 快速判断，使用较短的超时时间
                    max_retries=0
                )
                
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一位生物化学与分子生物学领域的专家，擅长快速判断论文的研究方向。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,  # 低温度，确保判断稳定
                    max_tokens=10  # 只需要回答"是"或"否"
                )
                
                result_text = response.choices[0].message.content.strip()
                
                # 解析结果
                if "是" in result_text or "yes" in result_text.lower() or "true" in result_text.lower():
                    logger.debug(f"[快速检查] 论文 '{paper.title[:50]}...' 判断为：相关")
                    return True
                elif "否" in result_text or "no" in result_text.lower() or "false" in result_text.lower():
                    logger.debug(f"[快速检查] 论文 '{paper.title[:50]}...' 判断为：不相关")
                    return False
                else:
                    # 无法解析，默认返回True（保守策略，避免误过滤）
                    logger.warning(f"[快速检查] 无法解析AI回答: '{result_text}'，默认判断为相关")
                    return True
                    
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                logger.debug(f"[快速检查] API调用失败（{key_name}, 第 {attempt + 1} 次）: {error_type}: {error_msg[:100]}")
                
                if attempt < max_retries - 1:
                    time.sleep(2)  # 短暂等待后重试
                else:
                    if key_index < len(all_api_keys) - 1:
                        time.sleep(1)  # 切换密钥前短暂等待
                        break  # 尝试下一个密钥
                    else:
                        # 所有密钥都失败，返回None
                        logger.warning(f"[快速检查] 所有API密钥均失败，无法判断论文相关性，默认保留")
                        return None
    
    # 所有尝试都失败
    return None

