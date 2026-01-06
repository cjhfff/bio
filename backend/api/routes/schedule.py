"""
Scheduled task management routes
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import logging
import json
import os
from pathlib import Path
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedule", tags=["schedule"])


class ScheduleTask(BaseModel):
    """Scheduled task model"""
    enabled: bool
    cron: str  # Cron expression, e.g., "0 9 * * *" for daily at 9 AM
    window_days: int = 1
    top_k: int = 12
    description: str = ""


@router.get("")
async def get_schedule():
    """Get current scheduled task configuration"""
    try:
        schedule_file = Path.cwd() / "data" / "schedule.json"
        
        if not schedule_file.exists():
            # Return default schedule
            return {
                "status": "success",
                "data": {
                    "enabled": False,
                    "cron": "0 9 * * *",  # Daily at 9 AM
                    "window_days": 1,
                    "top_k": 12,
                    "description": "Daily paper push task"
                }
            }
        
        with open(schedule_file, 'r', encoding='utf-8') as f:
            schedule_data = json.load(f)
        
        return {"status": "success", "data": schedule_data}
    except Exception as e:
        logger.error(f"Failed to get schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("")
async def update_schedule(task: ScheduleTask):
    """
    Update scheduled task configuration
    
    This saves the schedule configuration to a JSON file.
    To activate the schedule, you need to set up a system cron job or
    Windows Task Scheduler to call the API endpoint based on the cron expression.
    """
    try:
        logger.info(f"Schedule update requested: {task}")
        
        # Ensure data directory exists
        data_dir = Path.cwd() / "data"
        data_dir.mkdir(exist_ok=True)
        
        schedule_file = data_dir / "schedule.json"
        
        # Save schedule configuration
        schedule_data = task.dict()
        with open(schedule_file, 'w', encoding='utf-8') as f:
            json.dump(schedule_data, f, indent=2, ensure_ascii=False)
        
        logger.info("Schedule configuration updated successfully")
        
        # Generate cron command hint
        cron_hint = _generate_cron_hint(task.cron)
        
        return {
            "status": "success",
            "message": "Schedule configuration updated successfully",
            "cron_hint": cron_hint
        }
    except Exception as e:
        logger.error(f"Failed to update schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cron-examples")
async def get_cron_examples():
    """Get common cron expression examples"""
    return {
        "status": "success",
        "data": [
            {"expression": "0 9 * * *", "description": "每天上午9点"},
            {"expression": "0 */6 * * *", "description": "每6小时"},
            {"expression": "0 9,18 * * *", "description": "每天上午9点和下午6点"},
            {"expression": "0 9 * * 1", "description": "每周一上午9点"},
            {"expression": "0 9 1 * *", "description": "每月1日上午9点"},
            {"expression": "*/30 * * * *", "description": "每30分钟"},
        ]
    }


def _generate_cron_hint(cron_expression: str) -> Dict[str, str]:
    """Generate system-specific cron setup hints"""
    
    # Get the API endpoint URL
    api_url = os.getenv("API_URL", "http://localhost:8000")
    
    linux_hint = f"""
# Add to crontab (crontab -e):
{cron_expression} curl -X POST {api_url}/api/run
"""
    
    windows_hint = f"""
# PowerShell script for Windows Task Scheduler:
Invoke-RestMethod -Uri "{api_url}/api/run" -Method POST
"""
    
    docker_hint = f"""
# Add to host crontab:
{cron_expression} docker exec bio-backend curl -X POST http://localhost:8000/api/run
"""
    
    return {
        "linux": linux_hint.strip(),
        "windows": windows_hint.strip(),
        "docker": docker_hint.strip()
    }
