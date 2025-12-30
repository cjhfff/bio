# 项目整理计划

## 保留的文件（核心文件）

### 核心代码
- ✅ app/ — 模块化系统目录
- ✅ doubao_standalone.py — 独立脚本（可直接运行）
- ✅ requirements.txt — Python依赖
- ✅ README.md — 项目说明

### 数据文件
- ✅ paper_push.db — SQLite数据库
- ✅ paper_push.log — 运行日志
- ✅ sent_list.txt — 去重数据库
- ✅ sent_meta.jsonl — 元数据记录
- ✅ 生化领域突破汇总_20251228.txt — 最新报告（保留最新1份）

### 部署文件
- ✅ deploy_to_server.md — 服务器部署指南
- ✅ setup_server.sh — 自动部署脚本
- ✅ migrate_legacy_data.py — 数据迁移脚本

### Windows 定时任务
- ✅ run_daily.bat — Windows定时运行脚本

---

## 删除的文件（多余文件）

### 测试文件
- ❌ test.py — 旧版本
- ❌ test_protein.py — 旧版本
- ❌ test_pushplus.py — 测试脚本
- ❌ test_data_sources.py — 测试脚本
- ❌ test_data_sources_detailed.py — 测试脚本
- ❌ test_full_run.py — 测试脚本
- ❌ test_run.py — 测试脚本
- ❌ run_test.bat — 测试批处理

### 调试文件
- ❌ check_biorxiv_detail.py — 调试脚本
- ❌ check_db.py — 调试脚本
- ❌ debug_sources.py — 调试脚本
- ❌ diagnose_sources.py — 调试脚本

### 原始版本
- ❌ doubao.py — 原始Coze版本（已重构）

### 临时/重复文件
- ❌ plan.md — 临时计划
- ❌ plan.txt — 临时计划
- ❌ noop.txt — 临时文件
- ❌ quick_deploy.txt — 重复（信息已在deploy_to_server.md中）
- ❌ setup_scheduled_task.ps1 — 重复功能
- ❌ pack_for_server.py — 打包脚本（已完成）
- ❌ REFACTORING_SUMMARY.md — 重复（信息已在README中）

### 打包文件
- ❌ deploy_package/ — 已打包的目录
- ❌ paper_push_server.zip — 打包文件

### 旧报告文件
- ❌ 植物先天免疫研究资讯_20251219.txt
- ❌ 植物先天免疫研究资讯_20251224.txt
- ❌ 生化领域突破汇总_20251219.txt
- ❌ 生化领域突破汇总_20251226.txt
- ❌ 生化领域突破汇总_20251227.txt

### 缓存目录
- ❌ __pycache__/ — Python缓存
- ❌ app/__pycache__/ — Python缓存
- ❌ app/*/pycache__/ — 所有子目录缓存

---

## 整理后的目录结构

```
bio/
├── app/                          # 模块化系统
│   ├── __init__.py
│   ├── __main__.py
│   ├── api.py
│   ├── cli.py
│   ├── config.py
│   ├── filtering.py
│   ├── logging.py
│   ├── models.py
│   ├── ranking.py
│   ├── scoring.py
│   ├── llm/                      # LLM模块
│   ├── push/                     # 推送模块
│   ├── sources/                  # 数据源模块
│   └── storage/                  # 存储模块
├── doubao_standalone.py          # 独立脚本
├── requirements.txt              # 依赖文件
├── README.md                     # 项目说明
├── deploy_to_server.md           # 部署指南
├── setup_server.sh               # 部署脚本
├── migrate_legacy_data.py        # 数据迁移
├── run_daily.bat                 # Windows定时任务
├── paper_push.db                 # 数据库
├── paper_push.log                # 日志
├── sent_list.txt                 # 去重数据库
├── sent_meta.jsonl               # 元数据
└── 生化领域突破汇总_20251228.txt  # 最新报告
```

---

## 统计

- 保留文件：约 15 个主要文件 + app/ 目录
- 删除文件：约 30+ 个文件/目录
- 节省空间：预计减少 70% 的文件数量





