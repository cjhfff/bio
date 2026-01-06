"""
Configuration management routes
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
from backend.core.config import Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
async def get_config():
    """Get current configuration"""
    try:
        config_data = {
            "keywords": {
                "nitrogen": list(Config.RESEARCH_TOPICS.get("Nitrogen_Fixation", [])),
                "signal": list(Config.RESEARCH_TOPICS.get("Signal_Transduction", [])),
                "enzyme": list(Config.RESEARCH_TOPICS.get("Enzyme_Mechanism", []))
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
            }
        }
        
        return {"status": "success", "data": config_data}
    except Exception as e:
        logger.error(f"Failed to get config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("")
async def update_config(config: Dict[str, Any]):
    """
    Update configuration
    
    Note: This is a stub. In a real implementation, you would:
    1. Validate the configuration
    2. Update the .env file or a config database
    3. Reload the configuration
    """
    try:
        # TODO: Implement configuration update logic
        logger.info("Configuration update requested")
        
        return {
            "status": "success",
            "message": "Configuration updated (note: changes require restart to take effect)"
        }
    except Exception as e:
        logger.error(f"Failed to update config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
