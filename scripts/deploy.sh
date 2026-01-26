#!/bin/bash

# =================================================================
# Bio Paper System 自动化部署与重启脚本
# =================================================================

# 1. 配置变量
APP_PORT=8000
APP_NAME="bio-backend"
LOG_DIR="logs"

# 自动检测 Python 版本（优先级：python3.9 > python3 > python）
# 也可以通过环境变量手动指定: export PYTHON_EXEC="python3.9"
if [ -z "$PYTHON_EXEC" ]; then
    if command -v python3.9 &> /dev/null; then
        PYTHON_EXEC="python3.9"
    elif command -v python3 &> /dev/null; then
        PYTHON_EXEC="python3"
    elif command -v python &> /dev/null; then
        PYTHON_EXEC="python"
    else
        echo "❌ 错误: 未找到 Python 解释器！"
        echo "请先运行: bash scripts/check_python.sh 查看可用的 Python 版本"
        exit 1
    fi
fi

echo "使用 Python: $PYTHON_EXEC ($($PYTHON_EXEC --version 2>&1))"

echo ">>> [1/5] 开始清理旧进程..."
# 查找占用指定端口的进程并杀死
PID=$(lsof -t -i:$APP_PORT)
if [ -z "$PID" ]; then
    echo "没有进程占用端口 $APP_PORT"
else
    echo "发现占用端口 $APP_PORT 的进程: $PID，正在关闭..."
    kill -9 $PID
    sleep 2
fi

# 杀死所有残留的 uvicorn 进程
pkill -f uvicorn
echo "进程清理完成。"

echo ">>> [2/5] 更新系统依赖..."
# 确保安装了登录系统必须的加密库
$PYTHON_EXEC -m pip install --upgrade pip
$PYTHON_EXEC -m pip install python-jose[cryptography] passlib[bcrypt] python-multipart email-validator pydantic[email]
# 安装 requirements.txt 中的其他依赖
if [ -f "requirements.txt" ]; then
    $PYTHON_EXEC -m pip install -r requirements.txt
fi

echo ">>> [3/5] 验证代码结构与数据库..."
# 创建必要的目录
mkdir -p data/database $LOG_DIR
# 尝试加载一次应用以验证没有 ModuleNotFoundError
$PYTHON_EXEC -c "import os; os.environ['DB_PATH']='data/database/paper_push.db'; from backend.api.main import app; print('代码逻辑验证通过')"

if [ $? -ne 0 ]; then
    echo "❌ 代码验证失败，请检查报错信息！"
    exit 1
fi

echo ">>> [4/5] 启动后端服务 (后台运行)..."
nohup $PYTHON_EXEC -m uvicorn backend.api.main:app --host 0.0.0.0 --port $APP_PORT > $LOG_DIR/api.log 2>&1 &

echo ">>> [5/5] 验证启动状态..."
sleep 5
if curl -s http://127.0.0.1:$APP_PORT/health | grep -q "healthy"; then
    echo "✅ 后端启动成功！"
    echo "日志文件: $LOG_DIR/api.log"
    echo "访问地址: http://服务器IP:$APP_PORT"
else
    echo "❌ 启动失败，请查看 $LOG_DIR/api.log"
fi

