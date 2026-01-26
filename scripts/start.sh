#!/bin/bash

# =================================================================
# Bio Paper System 快速启动脚本
# =================================================================

# 配置变量
APP_PORT=8000
LOG_DIR="logs"
PYTHON_EXEC="python3"  # 根据服务器环境调整，如 python3.9

# 创建日志目录
mkdir -p $LOG_DIR

echo ">>> 正在启动后端服务..."
echo "端口: $APP_PORT"
echo "日志: $LOG_DIR/api.log"

# 启动服务（后台运行）
nohup $PYTHON_EXEC -m uvicorn backend.api.main:app --host 0.0.0.0 --port $APP_PORT > $LOG_DIR/api.log 2>&1 &

# 获取进程ID
PID=$!
echo "进程ID: $PID"

# 等待几秒让服务启动
sleep 3

# 检查服务是否启动成功
if curl -s http://127.0.0.1:$APP_PORT/health > /dev/null 2>&1; then
    echo "✅ 服务启动成功！"
    echo ""
    echo "访问地址: http://服务器IP:$APP_PORT"
    echo "API文档: http://服务器IP:$APP_PORT/docs"
    echo "查看日志: tail -f $LOG_DIR/api.log"
    echo ""
    echo "停止服务: kill $PID 或使用 scripts/stop.sh"
else
    echo "❌ 服务启动可能失败，请查看日志: $LOG_DIR/api.log"
    echo "检查命令: tail -20 $LOG_DIR/api.log"
fi
