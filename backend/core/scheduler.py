"""
定时任务调度器
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from typing import Optional, Dict, Any
from backend.core.config_manager import load_config_from_env, save_config

logger = logging.getLogger(__name__)

# 全局调度器实例
scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """获取或创建调度器实例"""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler()
    return scheduler


def init_scheduler():
    """初始化调度器并加载配置的定时任务"""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler()
    
    # 从配置加载定时任务设置
    config = load_config_from_env()
    schedule_config = config.get('schedule', {})
    
    if schedule_config.get('enabled', False):
        time_str = schedule_config.get('time', '08:30')
        hour, minute = map(int, time_str.split(':'))
        
        # 添加定时任务
        scheduler.add_job(
            trigger_daily_task,
            trigger=CronTrigger(hour=hour, minute=minute),
            id='daily_paper_push',
            name='每日论文推送任务',
            replace_existing=True
        )
        logger.info(f"定时任务已配置: 每天 {time_str} 执行")
    else:
        logger.info("定时任务未启用")
    
    if not scheduler.running:
        scheduler.start()
        logger.info("定时任务调度器已启动")


def trigger_daily_task():
    """触发每日推送任务（同步函数，由调度器在后台线程执行）"""
    try:
        from backend.cli import run_push_task
        
        logger.info("定时任务触发: 开始执行每日推送任务")
        # 直接执行同步任务（调度器会在后台线程中执行）
        run_push_task()
        logger.info("定时任务执行完成")
    except Exception as e:
        logger.error(f"定时任务执行失败: {e}", exc_info=True)


def update_schedule(enabled: bool, time: str = '08:30'):
    """更新定时任务配置"""
    global scheduler
    
    # 确保调度器已初始化
    scheduler = get_scheduler()
    
    # 移除现有任务
    if scheduler.get_job('daily_paper_push'):
        scheduler.remove_job('daily_paper_push')
        logger.info("已移除现有定时任务")
    
    # 如果启用，添加新任务
    if enabled:
        try:
            hour, minute = map(int, time.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError(f"无效的时间格式: {time}")
            
            # 确保调度器正在运行
            if not scheduler.running:
                scheduler.start()
            
            scheduler.add_job(
                trigger_daily_task,
                trigger=CronTrigger(hour=hour, minute=minute),
                id='daily_paper_push',
                name='每日论文推送任务',
                replace_existing=True
            )
            logger.info(f"定时任务已更新: 每天 {time} 执行")
        except ValueError as e:
            logger.error(f"时间格式错误: {e}")
            raise
    else:
        # 如果禁用，确保调度器停止（但不要完全关闭，因为可能还有其他任务）
        logger.info("定时任务已禁用")
    
    # 保存配置到.env
    save_config({
        'schedule': {
            'enabled': enabled,
            'time': time
        }
    })


def get_schedule_status() -> Dict[str, Any]:
    """获取定时任务状态"""
    global scheduler
    
    # 从配置读取基础信息
    config = load_config_from_env()
    schedule_config = config.get('schedule', {})
    base_config = {
        'enabled': schedule_config.get('enabled', False),
        'time': schedule_config.get('time', '08:30'),
        'status': 'stopped',
        'next_run': None
    }
    
    if scheduler is None:
        return base_config
    
    job = scheduler.get_job('daily_paper_push')
    if job and scheduler.running:
        # 从job获取实际执行时间
        if job.next_run_time:
            next_run = job.next_run_time
            # 获取trigger中的时间设置
            if hasattr(job.trigger, 'hour') and hasattr(job.trigger, 'minute'):
                time_str = f"{job.trigger.hour:02d}:{job.trigger.minute:02d}"
            else:
                time_str = base_config['time']
            
            return {
                'enabled': True,
                'time': time_str,
                'status': 'running',
                'next_run': next_run.isoformat()
            }
        else:
            return {
                'enabled': True,
                'time': base_config['time'],
                'status': 'running',
                'next_run': None
            }
    else:
        return base_config


def stop_scheduler():
    """停止调度器"""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("定时任务调度器已停止")

