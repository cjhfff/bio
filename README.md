# 智能论文推送系统

一个可上线的智能论文推送系统，支持从多个数据源抓取、智能评分、AI生成报告，并通过多种渠道推送。

## ✨ 功能特性

- **多数据源抓取**：bioRxiv、PubMed、RSS、Europe PMC、EurekAlert、GitHub、Semantic Scholar
- **智能评分系统**：可解释的评分算法，支持关键词匹配、顶刊加分、引用数、新鲜度等维度
- **AI报告生成**：使用DeepSeek API生成每日情报内参
- **多渠道推送**：支持PushPlus、邮件、企业微信
- **Web管理界面**：Vue 3 + Element Plus 前端，实时监控和管理
- **可靠存储**：SQLite数据库，支持审计和回溯
- **性能优化**：连接池、缓存、重试机制、速率限制

## 📁 项目结构

```
bio/
├── backend/              # 后端代码
│   ├── api/              # FastAPI路由
│   ├── core/             # 核心业务逻辑
│   ├── models/           # 数据模型
│   ├── services/         # 业务服务层
│   ├── sources/          # 数据源模块
│   ├── llm/              # LLM报告生成
│   ├── push/             # 推送模块
│   ├── storage/          # 存储模块
│   ├── utils/            # 工具函数
│   └── cli.py            # CLI入口
│
├── frontend/             # 前端代码 (Vue 3 + Vite)
│   ├── src/
│   │   ├── components/   # 组件
│   │   ├── views/        # 页面视图
│   │   ├── api/          # API客户端
│   │   ├── store/        # 状态管理
│   │   └── router/       # 路由配置
│   └── package.json
│
├── data/                 # 数据目录
│   ├── database/         # SQLite数据库
│   ├── logs/             # 日志文件
│   ├── reports/          # 生成的报告
│   └── cache/            # 缓存文件
│
├── docker/               # Docker配置
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── scripts/              # 脚本
├── tests/                # 测试
├── requirements.txt      # 依赖
├── requirements-dev.txt  # 开发依赖
└── pyproject.toml        # 项目配置
```

## 🚀 快速开始

### 使用 Docker (推荐)

1. 克隆项目并配置环境变量：
```bash
git clone <repository>
cd bio
cp .env.example .env
# 编辑 .env 文件，填入你的API密钥等配置
```

2. 启动服务：
```bash
cd docker
docker-compose up -d
```

3. 访问管理界面：
- 前端界面: http://localhost:3000
- 后端API: http://localhost:8000

### 手动安装

1. 安装后端依赖：
```bash
pip install -r requirements.txt
```

2. 安装前端依赖：
```bash
cd frontend
npm install
```

3. 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件
```

4. 启动后端API：
```bash
python -m uvicorn backend.api.main:app --reload
```

5. 启动前端开发服务器：
```bash
cd frontend
npm run dev
```

## 💻 使用方法

### CLI方式（定时任务）

#### 执行推送任务
```bash
python -m backend run
```

#### 测试数据源
```bash
python -m backend test-sources
```

#### 自定义参数
```bash
python -m backend run --window-days 14 --top-k 10
```

### Web管理界面

访问 http://localhost:3000 使用Web管理界面：

- **仪表盘**：查看统计数据和最近运行记录
- **论文管理**：浏览和管理论文数据
- **配置中心**：管理关键词、评分规则、数据源
- **日志查看**：实时查看系统日志

### API接口

后端提供RESTful API（访问 http://localhost:8000/docs 查看完整文档）：

- `POST /api/run` - 触发推送任务
- `GET /api/runs` - 获取运行历史
- `GET /api/runs/{run_id}/scores` - 获取评分详情
- `POST /api/test-sources` - 测试数据源

## 🔧 配置说明

主要配置项（在 `.env` 文件中）：

- `DEEPSEEK_API_KEY`: DeepSeek API密钥（必需）
- `PUBMED_EMAIL`: PubMed邮箱（必需）
- `PUSHPLUS_TOKENS`: PushPlus token，多个用逗号分隔
- `DEFAULT_WINDOW_DAYS`: 默认抓取窗口（天），默认1天
- `TOP_K`: 选择Top K篇，默认12篇

## 📊 性能优化

项目包含多项性能优化：

- **连接池**：HTTP请求使用连接池，减少连接开销
- **缓存机制**：文件缓存和内存缓存，避免重复API调用
- **重试机制**：指数退避重试，提高可靠性
- **速率限制**：防止API限流
- **数据库优化**：索引优化，提升查询性能

## 🧪 开发

### 运行测试
```bash
pytest tests/
```

### 代码格式化
```bash
black backend/
isort backend/
```

### 类型检查
```bash
mypy backend/
```

## 📝 许可证

MIT

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！







