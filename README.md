# 智能论文推送系统

一个可上线的智能论文推送系统，支持从多个数据源抓取、智能评分、AI生成报告，并通过多种渠道推送。

## 功能特性

- **多数据源抓取**：bioRxiv、PubMed、RSS、Europe PMC、EurekAlert、GitHub、Semantic Scholar
- **智能评分系统**：可解释的评分算法，支持关键词匹配、顶刊加分、引用数、新鲜度等维度
- **AI报告生成**：使用DeepSeek API生成每日情报内参
- **多渠道推送**：支持PushPlus、邮件、企业微信
- **可靠存储**：SQLite数据库，支持审计和回溯
- **双入口**：CLI定时任务 + FastAPI管理接口

## 安装

1. 克隆或下载项目
2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的API密钥等配置
```

## 使用方法

### CLI方式（定时任务）

#### 执行推送任务
```bash
python -m app.cli run
```

#### 测试数据源
```bash
python -m app.cli test-sources
```

#### 自定义参数
```bash
python -m app.cli run --window-days 14 --top-k 10
```

### API方式（管理界面）

启动API服务：
```bash
python -m app.api
```

或使用uvicorn：
```bash
uvicorn app.api:app --host 0.0.0.0 --port 8000
```

API接口：
- `POST /api/run` - 触发推送任务
- `GET /api/runs` - 获取运行历史
- `GET /api/runs/{run_id}/scores` - 获取评分详情
- `POST /api/test-sources` - 测试数据源

### Windows任务计划

1. 创建批处理文件 `run_push.bat`：
```batch
@echo off
cd /d C:\path\to\project
python -m app.cli run
```

2. 在Windows任务计划程序中创建定时任务，每天执行该批处理文件

## 数据迁移

如果你之前使用 `sent_list.txt` 和 `sent_meta.jsonl`，可以运行迁移脚本：

```bash
python migrate_legacy_data.py
```

## 配置说明

主要配置项（在 `.env` 文件中）：

- `DEEPSEEK_API_KEY`: DeepSeek API密钥（必需）
- `PUBMED_EMAIL`: PubMed邮箱（必需）
- `PUSHPLUS_TOKENS`: PushPlus token，多个用逗号分隔
- `DEFAULT_WINDOW_DAYS`: 默认抓取窗口（天），默认7天
- `EUROPEPMC_WINDOW_DAYS`: Europe PMC窗口（天），默认1天
- `TOP_K`: 选择Top K篇，默认5篇

## 目录结构

```
app/
├── __init__.py
├── config.py          # 配置管理
├── logging.py         # 日志配置
├── models.py          # 数据模型
├── filtering.py       # 过滤逻辑
├── scoring.py         # 评分系统
├── ranking.py         # 排名与选择
├── cli.py             # CLI入口
├── api.py             # FastAPI服务
├── sources/           # 数据源模块
│   ├── base.py
│   ├── biorxiv.py
│   ├── pubmed.py
│   └── ...
├── llm/               # LLM报告生成
│   └── generator.py
├── push/              # 推送模块
│   ├── pushplus.py
│   ├── email.py
│   └── wecom.py
└── storage/           # 存储模块
    ├── db.py
    └── repo.py
```

## 兼容性

保留了对原有 `doubao_standalone.py` 的兼容。你可以继续使用原有脚本，它会调用新的模块化代码。

## 许可证

MIT







