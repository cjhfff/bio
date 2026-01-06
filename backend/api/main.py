"""
FastAPI 服务：提供API接口
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import asyncio
import logging
from backend.core.config import Config
from backend.core.logging import setup_logging, get_logger
from backend.storage import init_db, PaperRepository
from backend.cli import run_push_task, test_sources

logger = get_logger(__name__)

app = FastAPI(title="智能论文推送系统API", version="1.0.0")


@app.on_event("startup")
async def startup():
    """启动时初始化"""
    setup_logging()
    init_db()
    logger.info("API服务启动")


@app.get("/")
async def root():
    """根路径"""
    return {"message": "智能论文推送系统API", "version": "1.0.0"}


@app.post("/api/run")
async def trigger_run(window_days: int = None, top_k: int = None):
    """触发推送任务"""
    try:
        # 在后台执行任务
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run_push_task, window_days, top_k)
        return {"status": "success", "message": "任务已启动"}
    except Exception as e:
        logger.error(f"触发任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/runs")
async def get_runs(limit: int = 10):
    """获取运行历史"""
    try:
        repo = PaperRepository()
        runs = repo.get_run_history(limit)
        return {"status": "success", "data": runs}
    except Exception as e:
        logger.error(f"获取运行历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/runs/{run_id}/scores")
async def get_run_scores(run_id: str):
    """获取某次运行的评分详情"""
    try:
        repo = PaperRepository()
        scores = repo.get_paper_scores(run_id)
        return {"status": "success", "data": scores}
    except Exception as e:
        logger.error(f"获取评分详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test-sources")
async def trigger_test_sources():
    """测试所有数据源"""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, test_sources)
        return {"status": "success", "message": "测试完成，请查看日志"}
    except Exception as e:
        logger.error(f"测试数据源失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)







