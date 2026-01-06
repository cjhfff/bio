"""
FastAPI 服务：提供API接口
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import asyncio
import logging
from backend.core.config import Config
from backend.core.logging import setup_logging, get_logger
from backend.storage import init_db, PaperRepository
from backend.cli import run_push_task, test_sources

# Import routes
from backend.api.routes import papers, config, logs, auth, admin_users

logger = get_logger(__name__)

app = FastAPI(
    title="智能论文推送系统API",
    version="2.0.0",
    description="Bio Paper Push System - Intelligent paper recommendation and push service"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(papers.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(admin_users.router, prefix="/api")


@app.on_event("startup")
async def startup():
    """启动时初始化"""
    setup_logging()
    init_db()
    
    # 初始化默认管理员账户
    try:
        from backend.storage.user_repo import UserRepository
        repo = UserRepository()
        repo.init_default_admin()
    except Exception as e:
        logger.warning(f"初始化默认管理员失败: {e}")
    
    # 初始化定时任务调度器
    try:
        from backend.core.scheduler import init_scheduler
        init_scheduler()
    except Exception as e:
        logger.warning(f"定时任务调度器初始化失败: {e}")
    
    logger.info("API服务启动")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "智能论文推送系统API",
        "version": "2.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.get("/api/run/status")
async def get_run_status():
    """检查是否有任务正在运行"""
    try:
        repo = PaperRepository()
        # 获取最新的运行记录
        runs = repo.get_run_history(1)
        if runs and len(runs) > 0:
            latest_run = runs[0]
            # 如果最新运行记录的状态是running，说明任务正在运行
            if latest_run.get('status') == 'running':
                return {
                    "status": "success",
                    "running": True,
                    "run_id": latest_run.get('run_id'),
                    "start_time": latest_run.get('start_time')
                }
        return {"status": "success", "running": False}
    except Exception as e:
        logger.error(f"检查任务状态失败: {e}", exc_info=True)
        return {"status": "error", "running": False, "error": str(e)}


@app.post("/api/run")
async def trigger_run(window_days: int = None, top_k: int = None):
    """触发推送任务"""
    try:
        # 检查是否有任务正在运行
        repo = PaperRepository()
        runs = repo.get_run_history(1)
        if runs and len(runs) > 0:
            latest_run = runs[0]
            if latest_run.get('status') == 'running':
                return {
                    "status": "error",
                    "message": "已有任务正在运行中，请等待当前任务完成后再试",
                    "running": True,
                    "run_id": latest_run.get('run_id')
                }
        
        # 在后台执行任务（不等待完成，立即返回）
        import threading
        thread = threading.Thread(
            target=run_push_task,
            args=(window_days, top_k),
            daemon=True
        )
        thread.start()
        return {"status": "success", "message": "任务已启动，正在后台执行"}
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







