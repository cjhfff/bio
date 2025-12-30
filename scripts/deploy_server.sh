#!/bin/bash
# 服务器部署脚本
set -e

PROJECT_DIR="${1:-$(pwd)}"
VENV_DIR="$PROJECT_DIR/venv"

echo "=========================================="
echo "开始部署 Paper Push 系统到服务器"
echo "=========================================="
echo "项目目录: $PROJECT_DIR"
echo ""

# 1. 检查 Python 版本
echo "1. 检查 Python 版本..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3，请先安装 Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python 版本: $(python3 --version)"

# 2. 进入项目目录
cd "$PROJECT_DIR"
echo ""
echo "2. 进入项目目录: $(pwd)"

# 3. 创建虚拟环境（如果不存在）
echo ""
echo "3. 检查虚拟环境..."
if [ ! -d "$VENV_DIR" ]; then
    echo "   创建虚拟环境..."
    python3 -m venv "$VENV_DIR"
    echo "✅ 虚拟环境已创建: $VENV_DIR"
else
    echo "✅ 虚拟环境已存在: $VENV_DIR"
fi

# 4. 激活虚拟环境并安装依赖
echo ""
echo "4. 安装依赖..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ 依赖安装完成"

# 5. 创建必要目录
echo ""
echo "5. 创建必要目录..."
mkdir -p data logs reports
echo "✅ 目录创建完成:"
echo "   - data/   (数据库)"
echo "   - logs/   (日志)"
echo "   - reports/ (报告)"

# 6. 检查 .env 文件
echo ""
echo "6. 检查配置文件..."
if [ ! -f ".env" ]; then
    echo "⚠️  警告: .env 文件不存在"
    echo "   请创建 .env 文件并配置以下必需项:"
    echo "   - DEEPSEEK_API_KEY"
    echo "   - PUBMED_EMAIL"
    echo ""
    echo "   可选配置项:"
    echo "   - PUSHPLUS_TOKENS"
    echo "   - EMAIL_* (邮件推送)"
    echo "   - WECOM_WEBHOOK_URL (企业微信)"
    echo ""
    read -p "是否现在创建 .env 文件? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cat > .env << EOF
# DeepSeek API 配置（必需）
DEEPSEEK_API_KEY=sk-xxx

# PubMed 配置（必需）
PUBMED_EMAIL=your-email@example.com

# 推送配置（可选）
# PUSHPLUS_TOKENS=token1,token2
# EMAIL_SMTP_HOST=smtp.example.com
# EMAIL_SMTP_PORT=587
# EMAIL_SMTP_USER=your-email@example.com
# EMAIL_SMTP_PASSWORD=your-password
# EMAIL_TO=recipient@example.com
# WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx

# 数据库路径（可选，默认 data/paper_push.db）
DB_PATH=data/paper_push.db

# 日志配置（可选）
LOG_FILE=paper_push.log
LOG_LEVEL=INFO

# 检索窗口（可选，默认1天）
DEFAULT_WINDOW_DAYS=1
EUROPEPMC_WINDOW_DAYS=1

# 快速筛选阈值（可选，默认50）
QUICK_FILTER_THRESHOLD=50

# API 超时和重试（可选）
API_TIMEOUT=600
API_MAX_RETRIES=3
API_RETRY_BASE_DELAY=10
API_RETRY_MAX_DELAY=60
EOF
        echo "✅ .env 文件已创建，请编辑并填入实际配置"
        echo "   编辑命令: nano .env 或 vim .env"
    fi
else
    echo "✅ .env 文件已存在"
fi

# 7. 初始化数据库
echo ""
echo "7. 初始化数据库..."
python -m app run --help > /dev/null 2>&1 || true
if [ -f "data/paper_push.db" ]; then
    echo "✅ 数据库已初始化: data/paper_push.db"
else
    echo "⚠️  数据库文件未创建，将在首次运行时自动创建"
fi

# 8. 测试导入
echo ""
echo "8. 测试代码导入..."
python -c "import app; print('✅ 代码导入成功')" || {
    echo "❌ 代码导入失败，请检查错误信息"
    exit 1
}

# 9. 设置文件权限
echo ""
echo "9. 设置文件权限..."
chmod 755 data logs reports 2>/dev/null || true
chmod 600 .env 2>/dev/null || true
echo "✅ 文件权限设置完成"

# 10. 显示部署信息
echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "下一步操作:"
echo ""
echo "1. 配置 .env 文件（如果尚未配置）:"
echo "   nano .env"
echo ""
echo "2. 测试数据源:"
echo "   source venv/bin/activate"
echo "   python -m app test-sources"
echo ""
echo "3. 运行一次完整流程:"
echo "   python -m app run"
echo ""
echo "4. 配置定时任务（选择一种方式）:"
echo ""
echo "   方式1: Crontab"
echo "   crontab -e"
echo "   # 添加: 30 8 * * * cd $PROJECT_DIR && $VENV_DIR/bin/python -m app run"
echo ""
echo "   方式2: Systemd (推荐)"
echo "   参考: docs/服务器部署指南.md"
echo ""
echo "5. 查看日志:"
echo "   tail -f logs/paper_push_*.log"
echo ""
echo "=========================================="

