#!/bin/bash
# 服务器代码更新自动化脚本
# 用于安全地更新运行在服务器上的代码

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [ "$EUID" -ne 0 ] && [ -z "$SKIP_ROOT_CHECK" ]; then 
        log_warn "建议使用root用户运行此脚本，或设置 SKIP_ROOT_CHECK=1"
    fi
}

# 配置变量
PROJECT_DIR=${PROJECT_DIR:-"/root/bio_monitor"}
BACKUP_DIR=${BACKUP_DIR:-"/root/backups"}
BRANCH=${BRANCH:-"main"}
USE_DOCKER=${USE_DOCKER:-"false"}

echo "========================================"
echo "   代码更新自动化脚本"
echo "========================================"
echo "项目目录: $PROJECT_DIR"
echo "备份目录: $BACKUP_DIR"
echo "分支: $BRANCH"
echo "使用Docker: $USE_DOCKER"
echo "========================================"
echo ""

# 询问确认
read -p "是否继续更新? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_error "用户取消更新"
    exit 1
fi

# 步骤1: 检查项目目录
log_info "步骤1: 检查项目目录..."
if [ ! -d "$PROJECT_DIR" ]; then
    log_error "项目目录不存在: $PROJECT_DIR"
    exit 1
fi
cd "$PROJECT_DIR"

# 步骤2: 创建备份
log_info "步骤2: 创建备份..."
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$BACKUP_DATE"
mkdir -p "$BACKUP_PATH"

# 备份数据库
if [ -f "data/database/paper_push.db" ]; then
    log_info "备份数据库..."
    cp data/database/paper_push.db "$BACKUP_PATH/paper_push.db.backup"
elif [ -f "data/paper_push.db" ]; then
    log_info "备份数据库..."
    cp data/paper_push.db "$BACKUP_PATH/paper_push.db.backup"
else
    log_warn "未找到数据库文件"
fi

# 备份配置文件
if [ -f ".env" ]; then
    log_info "备份配置文件..."
    cp .env "$BACKUP_PATH/.env.backup"
else
    log_warn "未找到.env配置文件"
fi

# 备份当前git提交信息
git rev-parse HEAD > "$BACKUP_PATH/git_commit.txt"
log_info "当前版本: $(cat $BACKUP_PATH/git_commit.txt)"

log_info "备份完成: $BACKUP_PATH"

# 步骤3: 停止服务
log_info "步骤3: 停止运行中的服务..."

if [ "$USE_DOCKER" = "true" ]; then
    log_info "停止Docker容器..."
    if [ -f "docker/docker-compose.yml" ]; then
        cd docker
        docker-compose down
        cd ..
    else
        log_warn "未找到docker-compose.yml"
    fi
else
    log_info "停止Python进程..."
    # 查找并停止Python进程（谨慎操作）
    PYTHON_PIDS=$(pgrep -f "python.*backend" || true)
    if [ -n "$PYTHON_PIDS" ]; then
        log_info "发现运行中的进程: $PYTHON_PIDS"
        echo "$PYTHON_PIDS" | xargs kill 2>/dev/null || true
        sleep 2
    else
        log_info "未发现运行中的Python进程"
    fi
fi

# 步骤4: 保存本地修改
log_info "步骤4: 检查本地修改..."
if ! git diff-index --quiet HEAD --; then
    log_warn "发现本地修改，暂存修改..."
    git stash save "Auto stash before update at $BACKUP_DATE"
fi

# 步骤5: 拉取最新代码
log_info "步骤5: 拉取最新代码..."
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"

NEW_COMMIT=$(git rev-parse HEAD)
log_info "新版本: $NEW_COMMIT"

# 步骤6: 恢复本地修改（如果有）
if git stash list | grep -q "Auto stash before update"; then
    log_info "恢复本地修改..."
    git stash pop || log_warn "合并本地修改时发生冲突，请手动处理"
fi

# 步骤7: 更新依赖
log_info "步骤7: 更新依赖..."

# 检查requirements.txt是否有变化
if git diff "$OLD_COMMIT" "$NEW_COMMIT" --name-only | grep -q "requirements.txt"; then
    log_info "requirements.txt有更新，安装新依赖..."
    pip3 install -r requirements.txt --upgrade
else
    log_info "requirements.txt无变化，跳过依赖更新"
fi

# 更新前端依赖（如果有）
if [ -f "frontend/package.json" ]; then
    if git diff "$OLD_COMMIT" "$NEW_COMMIT" --name-only | grep -q "frontend/package.json"; then
        log_info "前端依赖有更新..."
        cd frontend
        npm install
        npm run build
        cd ..
    else
        log_info "前端依赖无变化"
    fi
fi

# 步骤8: 数据库迁移（如有需要）
log_info "步骤8: 检查数据库迁移..."
if [ -f "scripts/migrate_database.py" ]; then
    log_info "执行数据库迁移..."
    python3 scripts/migrate_database.py || log_warn "数据库迁移失败，请手动检查"
else
    log_info "无需数据库迁移"
fi

# 步骤9: 验证配置
log_info "步骤9: 验证配置文件..."
if [ -f ".env.example" ] && [ -f ".env" ]; then
    # 检查.env.example中是否有.env中没有的配置项
    while IFS= read -r line; do
        if [[ $line == *"="* ]] && ! grep -q "^${line%%=*}=" .env; then
            log_warn "配置项 ${line%%=*} 在.env中不存在，可能需要添加"
        fi
    done < .env.example
else
    log_warn "未找到.env或.env.example文件"
fi

# 步骤10: 测试运行
log_info "步骤10: 测试运行..."
if python3 -m backend test-sources --quick 2>/dev/null; then
    log_info "测试运行成功"
else
    log_warn "测试运行失败，但继续启动服务"
fi

# 步骤11: 重启服务
log_info "步骤11: 重启服务..."

if [ "$USE_DOCKER" = "true" ]; then
    log_info "启动Docker容器..."
    cd docker
    docker-compose up -d
    cd ..
else
    log_info "启动Python服务..."
    # 启动API服务（如果有）
    if [ -f "backend/api/main.py" ]; then
        nohup python3 -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
        log_info "API服务已启动，PID: $!"
    fi
    
    # 注意：定时任务需要手动配置，这里不自动启用
    log_warn "请手动检查并启用定时任务: crontab -e"
fi

# 步骤12: 验证更新
log_info "步骤12: 验证更新..."
sleep 5

if [ "$USE_DOCKER" = "true" ]; then
    if docker-compose ps | grep -q "Up"; then
        log_info "Docker容器运行正常"
    else
        log_error "Docker容器未正常运行"
    fi
else
    if pgrep -f "python.*backend" > /dev/null; then
        log_info "Python服务运行正常"
    else
        log_warn "未检测到Python服务进程"
    fi
fi

# 步骤13: 显示回滚信息
echo ""
echo "========================================"
log_info "更新完成！"
echo "========================================"
echo "备份位置: $BACKUP_PATH"
echo "旧版本: $(cat $BACKUP_PATH/git_commit.txt)"
echo "新版本: $NEW_COMMIT"
echo ""
echo "如需回滚，请执行:"
echo "  cd $PROJECT_DIR"
echo "  git reset --hard $(cat $BACKUP_PATH/git_commit.txt)"
echo "  cp $BACKUP_PATH/paper_push.db.backup data/database/paper_push.db"
echo "  # 然后重启服务"
echo ""
echo "查看日志:"
echo "  tail -f logs/api.log"
echo "  tail -f logs/cron.log"
echo "========================================"
