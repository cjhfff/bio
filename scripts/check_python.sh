#!/bin/bash

# =================================================================
# 检测服务器上的 Python 版本
# =================================================================

echo "=========================================="
echo "Python 版本检测"
echo "=========================================="
echo ""

# 检测所有可能的 Python 命令
PYTHON_COMMANDS=("python3.13" "python3.12" "python3.11" "python3.10" "python3.9" "python3.8" "python3" "python")

echo "检测可用的 Python 版本:"
echo ""

FOUND_PYTHON=""

for cmd in "${PYTHON_COMMANDS[@]}"; do
    if command -v $cmd &> /dev/null; then
        VERSION=$($cmd --version 2>&1)
        WHICH=$(which $cmd)
        echo "  ✅ $cmd"
        echo "     版本: $VERSION"
        echo "     路径: $WHICH"
        echo ""
        
        if [ -z "$FOUND_PYTHON" ]; then
            FOUND_PYTHON=$cmd
        fi
    fi
done

if [ -z "$FOUND_PYTHON" ]; then
    echo "❌ 未找到任何 Python 解释器！"
    exit 1
fi

echo "=========================================="
echo "推荐使用的 Python 命令: $FOUND_PYTHON"
echo "=========================================="
echo ""
echo "使用方法："
echo "  1. 在脚本中设置: PYTHON_EXEC=\"$FOUND_PYTHON\""
echo "  2. 或使用环境变量: export PYTHON_EXEC=\"$FOUND_PYTHON\""
echo ""
