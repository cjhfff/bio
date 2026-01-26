#!/bin/bash

# =================================================================
# 检查前后端服务状态
# =================================================================

echo "=========================================="
echo "前后端服务状态检查"
echo "=========================================="
echo ""

# 检查后端
echo "[后端服务]"
BACKEND_PID=$(lsof -t -i:8000 2>/dev/null)
if [ -z "$BACKEND_PID" ]; then
    echo "  ❌ 后端未运行（端口 8000 未被占用）"
else
    echo "  ✅ 后端正在运行"
    echo "     进程ID: $BACKEND_PID"
    ps -p $BACKEND_PID -o pid,user,cmd,etime 2>/dev/null | tail -1 | sed 's/^/     /'
    
    # 检查健康接口
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        HEALTH_RESPONSE=$(curl -s http://127.0.0.1:8000/health)
        echo "     健康检查: ✅ 正常 ($HEALTH_RESPONSE)"
    else
        echo "     健康检查: ❌ 异常"
    fi
fi
echo ""

# 检查前端
echo "[前端服务]"
FRONTEND_PID=$(lsof -t -i:3000 2>/dev/null)
if [ -z "$FRONTEND_PID" ]; then
    echo "  ❌ 前端未运行（端口 3000 未被占用）"
    echo ""
    echo "  启动前端方法："
    echo "    1. 开发模式: cd frontend && npm run dev"
    echo "    2. 使用脚本: bash scripts/start_frontend.sh"
else
    echo "  ✅ 前端正在运行"
    echo "     进程ID: $FRONTEND_PID"
    ps -p $FRONTEND_PID -o pid,user,cmd,etime 2>/dev/null | tail -1 | sed 's/^/     /'
fi
echo ""

# 检查 Node.js
echo "[Node.js 环境]"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "  ✅ Node.js: $NODE_VERSION"
else
    echo "  ❌ Node.js 未安装"
    echo "     需要安装 Node.js 才能运行前端开发服务器"
fi

if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo "  ✅ npm: $NPM_VERSION"
else
    echo "  ❌ npm 未安装"
fi
echo ""

# 检查 Python
echo "[Python 环境]"
if command -v python3.9 &> /dev/null; then
    PYTHON_VERSION=$(python3.9 --version 2>&1)
    echo "  ✅ Python3.9: $PYTHON_VERSION"
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo "  ✅ Python3: $PYTHON_VERSION"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version 2>&1)
    echo "  ✅ Python: $PYTHON_VERSION"
else
    echo "  ❌ Python 未安装"
fi
echo ""

echo "=========================================="
echo "访问地址"
echo "=========================================="
echo "后端 API: http://服务器IP:8000"
echo "后端文档: http://服务器IP:8000/docs"
if [ ! -z "$FRONTEND_PID" ]; then
    echo "前端界面: http://服务器IP:3000"
else
    echo "前端界面: 未启动"
fi
echo "=========================================="
