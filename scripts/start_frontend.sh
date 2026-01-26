#!/bin/bash

# =================================================================
# 启动前端服务
# =================================================================

FRONTEND_DIR="frontend"
LOG_DIR="logs"

echo ">>> 正在启动前端服务..."

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 错误: 未找到 Node.js！"
    echo "请先安装 Node.js:"
    echo "  Ubuntu/Debian: apt install nodejs npm"
    echo "  或访问: https://nodejs.org/"
    exit 1
fi

# 检查前端目录
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ 错误: 前端目录不存在: $FRONTEND_DIR"
    exit 1
fi

# 进入前端目录
cd $FRONTEND_DIR || exit 1

# 检查 node_modules
if [ ! -d "node_modules" ]; then
    echo ">>> 首次运行，正在安装依赖..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败"
        exit 1
    fi
fi

# 创建日志目录
mkdir -p ../$LOG_DIR

echo ">>> 启动开发服务器（端口 3000）..."
echo ">>> 日志文件: ../$LOG_DIR/frontend.log"
echo ""

# 启动前端服务（后台运行）
nohup npm run dev > ../$LOG_DIR/frontend.log 2>&1 &

FRONTEND_PID=$!
echo "进程ID: $FRONTEND_PID"

# 等待几秒
sleep 3

# 检查是否启动成功
if lsof -t -i:3000 > /dev/null 2>&1; then
    echo "✅ 前端服务启动成功！"
    echo ""
    echo "访问地址: http://服务器IP:3000"
    echo "查看日志: tail -f $LOG_DIR/frontend.log"
    echo ""
    echo "停止服务: kill $FRONTEND_PID 或使用 scripts/stop_frontend.sh"
else
    echo "❌ 前端服务启动可能失败，请查看日志: $LOG_DIR/frontend.log"
    echo "检查命令: tail -20 $LOG_DIR/frontend.log"
fi
