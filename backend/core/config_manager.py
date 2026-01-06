"""
配置管理器：负责配置的读取和持久化
"""
import os
from pathlib import Path
from typing import Dict, Any, List
import logging
from backend.core.config import Config

logger = logging.getLogger(__name__)


def get_env_file_path() -> Path:
    """获取 .env 文件路径"""
    env_file = Path(".env")
    if not env_file.exists():
        # 尝试在项目根目录查找
        env_file = Path.cwd() / ".env"
    return env_file


def load_env_file() -> Dict[str, str]:
    """读取 .env 文件内容"""
    env_file = get_env_file_path()
    env_vars = {}
    
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    return env_vars


def save_env_file(env_vars: Dict[str, str]):
    """保存 .env 文件"""
    env_file = get_env_file_path()
    
    # 读取现有文件，保留注释和格式
    existing_lines = []
    existing_vars = {}
    
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    existing_lines.append(line)
                elif '=' in stripped:
                    key, value = stripped.split('=', 1)
                    key = key.strip()
                    existing_vars[key] = line
                    existing_lines.append(line)
                else:
                    existing_lines.append(line)
    
    # 更新或添加变量
    for key, value in env_vars.items():
        if key in existing_vars:
            # 更新现有行
            for i, line in enumerate(existing_lines):
                if line.strip().startswith(f"{key}="):
                    existing_lines[i] = f"{key}={value}\n"
                    break
        else:
            # 添加新行
            existing_lines.append(f"{key}={value}\n")
    
    # 写入文件
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(existing_lines)
    
    logger.info(f"配置已保存到: {env_file}")


def update_config(config: Dict[str, Any]) -> Dict[str, str]:
    """
    更新配置并保存到 .env 文件
    返回需要更新的环境变量字典
    """
    env_updates = {}
    
    # 处理推送配置
    if 'push' in config:
        push_config = config['push']
        if 'pushplusTokens' in push_config:
            tokens = push_config['pushplusTokens']
            if isinstance(tokens, list):
                env_updates['PUSHPLUS_TOKENS'] = ','.join(tokens)
            elif isinstance(tokens, str):
                env_updates['PUSHPLUS_TOKENS'] = tokens
        
        if 'email' in push_config:
            env_updates['RECEIVER_EMAIL'] = push_config['email']
    
    # 处理通用配置
    if 'general' in config:
        general = config['general']
        if 'defaultWindowDays' in general:
            env_updates['DEFAULT_WINDOW_DAYS'] = str(general['defaultWindowDays'])
        if 'topK' in general:
            env_updates['TOP_K'] = str(general['topK'])
        if 'quickFilterThreshold' in general:
            env_updates['QUICK_FILTER_THRESHOLD'] = str(general['quickFilterThreshold'])
    
    # 处理数据源配置
    if 'dataSources' in config:
        # 这里可以保存数据源配置，但需要重新设计存储方式
        # 暂时只处理 EuropePMC
        for source in config['dataSources']:
            if source.get('name') == 'Europe PMC' and 'windowDays' in source:
                env_updates['EUROPEPMC_WINDOW_DAYS'] = str(source['windowDays'])
    
    # 保存到 .env 文件
    if env_updates:
        current_env = load_env_file()
        current_env.update(env_updates)
        save_env_file(current_env)
    
    return env_updates


def get_keywords_file_path() -> Path:
    """获取关键词配置文件路径"""
    keywords_file = Path("data/keywords.json")
    keywords_file.parent.mkdir(parents=True, exist_ok=True)
    return keywords_file


def load_keywords() -> Dict[str, List[str]]:
    """从文件加载关键词配置"""
    keywords_file = get_keywords_file_path()
    
    if keywords_file.exists():
        try:
            import json
            with open(keywords_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载关键词配置失败: {e}")
    
    # 如果文件不存在或加载失败，返回默认配置
    from backend.core.config import Config
    return {
        "Nitrogen_Fixation": list(Config.RESEARCH_TOPICS.get("Nitrogen_Fixation", [])),
        "Signal_Transduction": list(Config.RESEARCH_TOPICS.get("Signal_Transduction", [])),
        "Enzyme_Mechanism": list(Config.RESEARCH_TOPICS.get("Enzyme_Mechanism", []))
    }


def save_keywords(keywords: Dict[str, List[str]]):
    """保存关键词配置到文件"""
    keywords_file = get_keywords_file_path()
    
    try:
        import json
        # 转换前端格式到后端格式
        formatted_keywords = {
            "Nitrogen_Fixation": keywords.get("nitrogen", []),
            "Signal_Transduction": keywords.get("signal", []),
            "Enzyme_Mechanism": keywords.get("enzyme", [])
        }
        
        with open(keywords_file, 'w', encoding='utf-8') as f:
            json.dump(formatted_keywords, f, ensure_ascii=False, indent=2)
        
        logger.info(f"关键词配置已保存到: {keywords_file}")
    except Exception as e:
        logger.error(f"保存关键词配置失败: {e}")
        raise


def update_keywords(keywords: Dict[str, List[str]]):
    """
    更新关键词配置并保存到文件
    """
    logger.info(f"关键词配置更新请求: {keywords}")
    save_keywords(keywords)


def load_config_from_env() -> Dict[str, Any]:
    """从.env文件加载配置"""
    env_vars = load_env_file()
    config = {}
    
    # 解析定时任务配置
    schedule_enabled = env_vars.get('SCHEDULE_ENABLED', 'false').lower() == 'true'
    schedule_time = env_vars.get('SCHEDULE_TIME', '08:30')
    config['schedule'] = {
        'enabled': schedule_enabled,
        'time': schedule_time
    }
    
    return config


def save_config(config: Dict[str, Any]) -> Dict[str, str]:
    """
    保存配置到.env文件
    返回更新的环境变量字典
    """
    env_updates = {}
    
    # 处理定时任务配置
    if 'schedule' in config:
        schedule = config['schedule']
        if 'enabled' in schedule:
            env_updates['SCHEDULE_ENABLED'] = 'true' if schedule['enabled'] else 'false'
        if 'time' in schedule:
            env_updates['SCHEDULE_TIME'] = schedule['time']
    
    # 处理其他配置（复用update_config的逻辑）
    other_updates = update_config(config)
    env_updates.update(other_updates)
    
    # 保存到.env文件
    if env_updates:
        current_env = load_env_file()
        current_env.update(env_updates)
        save_env_file(current_env)
    
    return env_updates

