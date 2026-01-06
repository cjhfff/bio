"""
结构化日志配置
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from backend.config import Config

def setup_logging(run_id: str = None):
    """
    配置结构化日志
    
    Args:
        run_id: 运行ID，如果提供，会包含在日志文件名中
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # 确定日志文件路径
    log_file_path = Path(Config.LOG_FILE)
    
    # 如果日志文件路径不包含目录分隔符，则将其放在 data/logs/ 文件夹中
    # 如果环境变量设置了完整路径，则使用该路径
    if '/' not in str(log_file_path) and '\\' not in str(log_file_path):
        # 默认情况：将日志文件放在 data/logs/ 文件夹中
        logs_dir = Path("data/logs")
        logs_dir.mkdir(parents=True, exist_ok=True)  # 确保 data/logs/ 文件夹存在
        
        # 生成带时间戳的日志文件名
        base_name = log_file_path.stem  # 文件名（不含扩展名）
        extension = log_file_path.suffix  # 扩展名
        
        # 生成时间戳：日期_时分秒
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        
        # 如果提供了 run_id，使用 run_id 的前8位作为标识
        if run_id:
            run_short = run_id[:8] if len(run_id) >= 8 else run_id
            log_filename = f"{base_name}_{timestamp}_{run_short}{extension}"
        else:
            log_filename = f"{base_name}_{timestamp}{extension}"
        
        log_file_path = logs_dir / log_filename
    else:
        # 如果环境变量设置了完整路径，确保其父目录存在
        log_file_path = Path(log_file_path)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 文件输出（使用追加模式，但每次运行都是新文件）
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8', mode='a')
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # 根logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO))
    
    # 清除之前的处理器（避免重复添加）
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # 记录日志文件路径
    root_logger.info(f"日志文件: {log_file_path}")
    
    # 修复 Windows 控制台编码
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    
    return root_logger

def get_logger(name: str) -> logging.Logger:
    """获取logger"""
    return logging.getLogger(name)



