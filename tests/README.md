# 批处理功能测试文档

## 优化内容

### 1. API连接稳定性优化

#### 超时设置优化
- **原设置**: 300秒（5分钟）
- **新设置**: 600秒（10分钟），可通过环境变量 `API_TIMEOUT` 配置
- **位置**: `app/config.py`

#### 重试策略优化
- **原策略**: 固定延迟（5秒、10秒）
- **新策略**: 指数退避策略
  - 第1次重试: 10秒
  - 第2次重试: 20秒
  - 第3次重试: 40秒
  - 最大延迟: 60秒（可通过 `API_RETRY_MAX_DELAY` 配置）
- **位置**: `app/llm/generator.py`

#### 客户端实例优化
- **改进**: 每次重试都创建新的客户端实例，避免连接复用问题
- **位置**: `app/llm/generator.py` 中的 `generate_batch_report` 和 `generate_final_summary`

#### 密钥切换优化
- **改进**: 切换密钥前等待时间从2秒增加到5秒
- **位置**: `app/llm/generator.py`

### 2. 配置项

新增配置项（`app/config.py`）：
```python
API_TIMEOUT = 600  # API超时时间（秒）
API_MAX_RETRIES = 3  # 每个密钥最多重试次数
API_RETRY_BASE_DELAY = 10  # 重试基础延迟（秒）
API_RETRY_MAX_DELAY = 60  # 重试最大延迟（秒）
```

## 测试用例

### 1. 批处理功能测试 (`test_batch_processing.py`)

#### 测试类: `TestBatchProcessing`
- `test_prepare_papers_for_llm_batch_mode`: 测试批量模式下的论文准备
- `test_prepare_papers_for_llm_single_paper`: 测试单篇论文准备
- `test_prepare_papers_for_llm_empty_list`: 测试空论文列表
- `test_generate_batch_report_success`: 测试批次报告生成成功
- `test_generate_batch_report_api_failure`: 测试API失败时的降级报告
- `test_generate_batch_report_empty_papers`: 测试空论文列表的批次报告
- `test_generate_batch_report_more_than_two_papers`: 测试超过2篇论文的处理
- `test_generate_final_summary_success`: 测试最终总结报告生成成功
- `test_generate_final_summary_api_failure`: 测试最终总结失败时的处理
- `test_generate_final_summary_empty_reports`: 测试空报告列表的处理

#### 测试类: `TestBatchProcessingIntegration`
- `test_batch_processing_workflow`: 测试完整的批处理工作流程

### 2. API连接稳定性测试 (`test_api_connection.py`)

#### 测试类: `TestAPIConnection`
- `test_api_timeout_config`: 测试API超时配置
- `test_api_retry_config`: 测试API重试配置
- `test_retry_delay_calculation`: 测试重试延迟计算（指数退避）
- `test_api_retry_on_connection_error`: 测试连接错误时的重试机制
- `test_api_key_switching`: 测试API密钥切换机制
- `test_fresh_client_instance`: 测试每次重试都创建新的客户端实例

### 3. CLI批处理逻辑测试 (`test_cli_batch_logic.py`)

#### 测试类: `TestCLIBatchLogic`
- `test_batch_processing_logic`: 测试批处理逻辑
- `test_batch_size_calculation`: 测试批次大小计算
- `test_error_handling_in_batch_processing`: 测试批处理中的错误处理

## 运行测试

### 运行所有测试
```bash
python tests/run_tests.py
```

### 运行特定测试模块
```bash
python -m unittest tests.test_batch_processing
python -m unittest tests.test_api_connection
python -m unittest tests.test_cli_batch_logic
```

### 运行特定测试类
```bash
python -m unittest tests.test_batch_processing.TestBatchProcessing
```

### 运行特定测试方法
```bash
python -m unittest tests.test_batch_processing.TestBatchProcessing.test_prepare_papers_for_llm_batch_mode
```

## 测试覆盖率目标

- **单元测试**: 覆盖核心函数（`prepare_papers_for_llm`, `generate_batch_report`, `generate_final_summary`）
- **集成测试**: 覆盖完整的批处理工作流程
- **错误处理测试**: 覆盖API失败、网络错误等异常情况

## 注意事项

1. **Mock使用**: 测试中使用Mock避免实际调用API
2. **测试数据**: 使用模拟的Paper和ScoredPaper对象
3. **环境变量**: 某些测试可能需要设置环境变量
4. **数据库**: CLI测试可能需要模拟数据库操作

## 持续改进

- [ ] 添加性能测试（测试大批量论文的处理时间）
- [ ] 添加压力测试（测试API限流情况）
- [ ] 添加端到端测试（完整流程测试）
- [ ] 添加监控和日志测试


