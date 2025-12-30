"""
邮件推送
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import Config

logger = logging.getLogger(__name__)


class EmailSender:
    """邮件推送"""
    
    def __init__(self):
        self.sender_email = Config.SENDER_EMAIL
        self.auth_code = Config.SENDER_AUTH_CODE
        self.receiver_email = Config.RECEIVER_EMAIL
    
    def send(self, subject: str, content: str) -> bool:
        """发送邮件"""
        if not self.sender_email or not self.auth_code:
            logger.warning("未配置发送邮箱，跳过邮件发送")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.receiver_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            server = smtplib.SMTP('smtp.qq.com', 587)
            server.starttls()
            server.login(self.sender_email, self.auth_code)
            
            text = msg.as_string()
            server.sendmail(self.sender_email, self.receiver_email, text)
            server.quit()
            
            logger.info(f"邮件已成功发送到 {self.receiver_email}")
            return True
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False







