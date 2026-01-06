"""
Logs viewing routes
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import logging
from pathlib import Path
import re

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("")
async def get_logs(
    level: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get recent logs
    
    Args:
        level: Filter by log level (INFO, WARNING, ERROR)
        search: Search keyword
        limit: Maximum number of log entries to return
    """
    try:
        logs = []
        
        # Find the most recent log file
        logs_dir = Path("data/logs")
        if not logs_dir.exists():
            logs_dir = Path("logs")  # Fallback to old location
        
        if logs_dir.exists():
            log_files = sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
            
            if log_files:
                # Read the most recent log file
                log_file = log_files[0]
                
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Parse log lines
                log_pattern = re.compile(
                    r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - .+ - (\w+) - (.+)'
                )
                
                for line in reversed(lines[-limit:]):  # Get last N lines
                    match = log_pattern.match(line.strip())
                    if match:
                        time_str, log_level, message = match.groups()
                        
                        # Apply filters
                        if level and log_level != level:
                            continue
                        if search and search.lower() not in message.lower():
                            continue
                        
                        logs.append({
                            "time": time_str,
                            "level": log_level,
                            "message": message
                        })
                
                # Reverse to show newest first
                logs.reverse()
        
        return {"status": "success", "data": logs}
    except Exception as e:
        logger.error(f"Failed to get logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files")
async def list_log_files():
    """List available log files"""
    try:
        logs_dir = Path("data/logs")
        if not logs_dir.exists():
            logs_dir = Path("logs")
        
        log_files = []
        if logs_dir.exists():
            for log_file in sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True):
                log_files.append({
                    "name": log_file.name,
                    "size": log_file.stat().st_size,
                    "modified": log_file.stat().st_mtime
                })
        
        return {"status": "success", "data": log_files}
    except Exception as e:
        logger.error(f"Failed to list log files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
