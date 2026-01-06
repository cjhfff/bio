"""
企业微信推送
"""
import requests
import json
import logging
from backend.config import Config

logger = logging.getLogger(__name__)


class WeComSender:
    """企业微信机器人推送"""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or Config.WECOM_WEBHOOK_URL
    
    def send(self, title: str, content: str) -> bool:
        """发送企业微信消息"""
        if not self.webhook_url:
            logger.warning("未配置企业微信Webhook，跳过推送")
            return False
        
        try:
            # 企业微信Markdown格式
            markdown_content = f"## {title}\n\n{content}"
            
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": markdown_content
                }
            }
            
            response = requests.post(
                self.webhook_url,
                json=data,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('errcode') == 0:
                logger.info("企业微信推送成功")
                return True
            else:
                logger.error(f"企业微信推送失败: {result.get('errmsg', '未知错误')}")
                return False
        except Exception as e:
            logger.error(f"企业微信推送失败: {e}")
            return False







