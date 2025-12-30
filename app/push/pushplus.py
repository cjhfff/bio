"""
PushPlus 推送
"""
import requests
import logging
from typing import List
from app.config import Config

logger = logging.getLogger(__name__)


class PushPlusSender:
    """PushPlus 微信推送"""
    
    def __init__(self, tokens: List[str] = None):
        self.tokens = tokens or Config.PUSHPLUS_TOKENS
        self.url = "https://www.pushplus.plus/send"
    
    def send(self, title: str, content: str) -> bool:
        """发送推送，返回是否至少有一个成功"""
        success_count = 0
        
        for token in self.tokens:
            try:
                data = {
                    "token": token,
                    "title": title,
                    "content": content,
                    "template": "markdown"
                }
                
                response = requests.post(
                    self.url,
                    json=data,
                    timeout=20,
                    proxies={'http': None, 'https': None}
                )
                response.raise_for_status()
                
                logger.info(f"Token {token[:8]}... 发送成功")
                success_count += 1
            except Exception as e:
                logger.error(f"Token {token[:8]}... 发送失败: {e}")
        
        if success_count > 0:
            logger.info(f"群发完成，共成功发送 {success_count}/{len(self.tokens)} 个")
            return True
        else:
            logger.error("所有 token 均发送失败")
            return False







