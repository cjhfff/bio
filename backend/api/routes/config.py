"""
Configuration management routes
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
import os
from pathlib import Path
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
    
    Updates the .env file with new configuration values.
    Note: Some changes require service restart to take effect.
    """
    try:
        logger.info(f"Configuration update requested: {config}")
        
        # Find .env file path
        env_path = Path.cwd() / ".env"
        if not env_path.exists():
            env_path = Path.cwd().parent / ".env"  # Try parent directory
        
        if not env_path.exists():
            raise HTTPException(status_code=404, detail=".env file not found")
        
        # Read current .env content
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Parse current env vars
        env_vars = {}
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
        
        # Update values based on config
        if 'general' in config:
            if 'defaultWindowDays' in config['general']:
                env_vars['DEFAULT_WINDOW_DAYS'] = str(config['general']['defaultWindowDays'])
            if 'topK' in config['general']:
                env_vars['TOP_K'] = str(config['general']['topK'])
        
        if 'push' in config:
            if 'pushplusTokens' in config['push']:
                tokens = config['push']['pushplusTokens']
                if isinstance(tokens, list):
                    env_vars['PUSHPLUS_TOKENS'] = ','.join(tokens)
                else:
                    env_vars['PUSHPLUS_TOKENS'] = str(tokens)
            if 'email' in config['push']:
                env_vars['RECEIVER_EMAIL'] = str(config['push']['email'])
        
        # Write back to .env file
        with open(env_path, 'w', encoding='utf-8') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        
        logger.info("Configuration file updated successfully")
        
        return {
            "status": "success",
            "message": "Configuration updated successfully. Some changes may require restart to take effect."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
