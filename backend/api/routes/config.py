"""
Configuration management routes
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging
from backend.core.config import Config
from backend.core.config_manager import update_config as save_config, update_keywords
from backend.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
async def get_config(user: dict = Depends(get_current_user)):
    """Get current configuration"""
    try:
        from backend.core.config_manager import load_keywords
        
        # 从文件加载关键词（如果存在），否则使用默认配置
        keywords_dict = load_keywords()
        
        config_data = {
            "keywords": {
                "nitrogen": keywords_dict.get("Nitrogen_Fixation", list(Config.RESEARCH_TOPICS.get("Nitrogen_Fixation", []))),
                "signal": keywords_dict.get("Signal_Transduction", list(Config.RESEARCH_TOPICS.get("Signal_Transduction", []))),
                "enzyme": keywords_dict.get("Enzyme_Mechanism", list(Config.RESEARCH_TOPICS.get("Enzyme_Mechanism", [])))
            },
            "scoring": {
                "keywordWeight": 80,
                "journalBonus": 60,
                "citationWeight": 70,
                "freshnessWeight": 50
            },
            "dataSources": [
                {"name": "bioRxiv", "enabled": True, "windowDays": Config.DEFAULT_WINDOW_DAYS},
                {"name": "PubMed", "enabled": True, "windowDays": Config.DEFAULT_WINDOW_DAYS},
                {"name": "Europe PMC", "enabled": True, "windowDays": Config.EUROPEPMC_WINDOW_DAYS},
                {"name": "GitHub", "enabled": True, "windowDays": Config.DEFAULT_WINDOW_DAYS},
                {"name": "Semantic Scholar", "enabled": False, "windowDays": Config.DEFAULT_WINDOW_DAYS}
            ],
            "push": {
                "pushplusTokens": Config.PUSHPLUS_TOKENS if Config.PUSHPLUS_TOKENS else [],
                "email": Config.RECEIVER_EMAIL
            },
            "general": {
                "defaultWindowDays": Config.DEFAULT_WINDOW_DAYS,
                "topK": Config.TOP_K,
                "quickFilterThreshold": Config.QUICK_FILTER_THRESHOLD
            },
            "schedule": {
                "enabled": False,
                "time": "08:30"
            }
        }
        
        # 加载定时任务配置
        from backend.core.config_manager import load_config_from_env
        schedule_config = load_config_from_env().get('schedule', {})
        config_data["schedule"] = {
            "enabled": schedule_config.get('enabled', False),
            "time": schedule_config.get('time', '08:30')
        }
        
        # 获取定时任务状态
        from backend.core.scheduler import get_schedule_status
        schedule_status = get_schedule_status()
        config_data["schedule"].update(schedule_status)
        
        return {"status": "success", "data": config_data}
    except Exception as e:
        logger.error(f"Failed to get config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("")
async def update_config(config: Dict[str, Any], user: dict = Depends(get_current_user)):
    """
    Update configuration and save to .env file
    
    Note: Some changes (like keywords) require restart to take effect
    """
    try:
        logger.info("Configuration update requested")
        
        # 更新关键词（如果提供）
        if 'keywords' in config:
            update_keywords(config['keywords'])
        
        # 更新定时任务配置（如果提供）
        if 'schedule' in config:
            from backend.core.scheduler import update_schedule
            schedule = config['schedule']
            enabled = schedule.get('enabled', False)
            time = schedule.get('time', '08:30')
            update_schedule(enabled, time)
        
        # 更新其他配置并保存到 .env
        env_updates = save_config(config)
        
        message = "配置已保存"
        if env_updates:
            message += f"。已更新: {', '.join(env_updates.keys())}"
        message += "。部分配置（如关键词）需要重启服务才能生效。"
        
        return {
            "status": "success",
            "message": message,
            "updated": list(env_updates.keys())
        }
    except Exception as e:
        logger.error(f"Failed to update config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-push")
async def test_push(request: Dict[str, Any], user: dict = Depends(get_current_user)):
    """测试推送功能"""
    try:
        from backend.push.pushplus import PushPlusSender
        
        token = request.get('token') if request else None
        test_token = token or (Config.PUSHPLUS_TOKENS[0] if Config.PUSHPLUS_TOKENS else None)
        if not test_token:
            raise HTTPException(status_code=400, detail="未提供 PushPlus Token")
        
        sender = PushPlusSender([test_token])
        success = sender.send(
            title="测试推送",
            content="这是一条测试推送消息，如果您收到此消息，说明推送功能正常工作。"
        )
        
        if success:
            return {"status": "success", "message": "测试推送已发送"}
        else:
            raise HTTPException(status_code=500, detail="推送发送失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试推送失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_config(user: dict = Depends(get_current_user)):
    """重新加载配置（热重载）"""
    try:
        from backend.core.config_manager import load_keywords
        
        # 重新加载关键词配置
        keywords_dict = load_keywords()
        Config.RESEARCH_TOPICS.update({
            "Nitrogen_Fixation": keywords_dict.get("Nitrogen_Fixation", []),
            "Signal_Transduction": keywords_dict.get("Signal_Transduction", []),
            "Enzyme_Mechanism": keywords_dict.get("Enzyme_Mechanism", [])
        })
        
        logger.info("配置已热重载，关键词已更新")
        return {
            "status": "success", 
            "message": "配置已重新加载，关键词立即生效，无需重启服务"
        }
    except Exception as e:
        logger.error(f"重新加载配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-database")
async def clear_database(user: dict = Depends(get_current_user)):
    """清除数据库内容"""
    try:
        from backend.storage.db import get_db
        import logging
        
        logger.info("Executing database clear operation requested via API")
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 清除所有表的数据（保留表结构）
            tables = ['pushes', 'scores', 'dedup_keys', 'papers', 'runs']
            for table in tables:
                cursor.execute(f"DELETE FROM {table}")
            
            # 重置自增ID
            cursor.execute("DELETE FROM sqlite_sequence")
        
        logger.info("Database cleared successfully via API")
        return {"status": "success", "message": "数据库已成功清空"}
    except Exception as e:
        logger.error(f"Failed to clear database: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
