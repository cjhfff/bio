# 关键词配置与评分逻辑优化设计

## 需求背景

### 问题一：评分系统局限性

当前评分系统在处理**固氮（Nitrogen Fixation）**领域的结构生物学研究时，存在以下问题：

1. **关键词硬编码**：核心词库直接写在 `scoring.py` 中，缺乏统一配置管理
2. **单维度评分**：仅对单独匹配的关键词加分，未体现跨领域交叉研究的价值（如"固氮 + 结构解析"）
3. **P0级过滤不足**：高价值的预印本文章（如固氮酶的冷冻电镜结构）难以突破 50 分门槛，导致重要突破延迟推送
4. **可解释性欠缺**：缺少明确的"协同增益"标识，用户无法直观理解系统为何推荐某篇文章

### 问题二：PubMed 数据源缺陷

当前 PubMed 数据源实现存在严重的数据质量问题：

1. **摘要空白漏洞**：`abstract` 字段被硬编码为空字符串（第 65、79 行），导致评分系统和过滤系统无法基于摘要内容进行精准判定
2. **排除过滤失效**：由于缺少摘要，`should_exclude_paper` 无法检测摘要中的医学临床词汇（如 `clinical trial`、`patient`），导致大量非目标领域文章进入推送队列
3. **豁免机制缺失**：未整合结构生物学豁免逻辑，即使摘要包含 `Cryo-EM` 等高价值词汇，仍可能被错误排除
4. **可观测性不足**：缺少数据漏斗统计，无法追踪 PubMed 数据源的过滤效率和质量问题

### 核心目标

**评分系统优化**：
- 通过引入**分层关键词配置**和**协同增益机制（Synergy Bonus）**，使固氮 P0 级文章（如固氮酶结构解析）能够自动置顶（≥50 分）
- 提高跨领域交叉研究的识别精度（Precision）
- 增强评分结果的可观测性和可解释性

**PubMed 数据源优化**：
- 修复摘要提取逻辑，还原论文完整语义信息
- 强化排除过滤精度，降低医学临床类杂质文章
- 整合结构生物学豁免机制，与 BioRxiv 逻辑对齐
- 增加数据漏斗诊断日志，提升系统可观测性

---

## 设计方案

### 一、配置层改造（app/config.py）

#### 1.1 新增分层关键词配置

在 `Config` 类中新增以下配置项，替代 `scoring.py` 中的硬编码词库：

| 配置项 | 用途 | 权重档位 | 示例关键词 |
|--------|------|----------|------------|
| `STRUCT_KEYWORDS` | 结构生物学核心词 | 15分/词 | `cryo-em`, `crystal structure`, `atomic resolution`, `nlr structure`, `resistosome` |
| `NITRO_KEYWORDS` | 生物固氮核心词 | 8分/词 | `nitrogen fixation`, `nitrogenase`, `nif`, `nodulation`, `symbiosome` |
| `SIGNAL_KEYWORDS` | 信号转导核心词 | 8分/词 | `signal transduction`, `receptor kinase`, `ligand`, `phosphorylation` |
| `BREAKTHROUGH_KEYWORDS` | 结构突破组合词 | 15分（组合匹配） | `nlr`, `resistosome`, `inflammasome`, `cryo-em` |

#### 1.2 配置项说明

**STRUCT_KEYWORDS（结构生物学核心词）**
- 范围：涵盖冷冻电镜、晶体结构、原子分辨率、构象变化等高价值技术和概念
- 权重：15分/词（最高档）
- 理由：结构生物学突破是该领域的最高证据等级

**NITRO_KEYWORDS & SIGNAL_KEYWORDS（固氮/信号核心词）**
- 范围：涵盖生物固氮、根瘤共生、信号转导等研究方向的专业术语
- 权重：8分/词（中等档）
- 理由：领域相关性词汇，但单独出现不足以构成突破性工作

**BREAKTHROUGH_KEYWORDS（结构突破组合词）**
- 范围：特定的高影响力词汇组合（如 NLR 免疫受体 + 冷冻电镜）
- 权重：15分（固定加分）
- 理由：这些词汇组合代表当前最前沿的研究方向

#### 1.3 与现有配置的关系

保留现有的 `RESEARCH_TOPICS`（用于数据源检索）和 `STRUCTURE_KEYWORDS`（用于过滤豁免），新增配置项专门服务于评分系统，避免混淆。

---

### 二、评分逻辑优化（app/scoring.py）

#### 2.1 核心改动：协同增益机制

新增**协同增益评分（Synergy Bonus）**规则：

| 判定条件 | 加分值 | 说明 |
|---------|--------|------|
| 同时命中结构词 + 固氮词 | +15分 | 如"nitrogenase cryo-EM structure" |
| 同时命中结构词 + 信号词 | +15分 | 如"receptor kinase crystal structure" |

#### 2.2 评分流程

**步骤1：关键词匹配**
- 遍历 `STRUCT_KEYWORDS`，每命中一个词 +15分
- 遍历 `NITRO_KEYWORDS` 和 `SIGNAL_KEYWORDS`，每命中一个词 +8分
- 记录所有匹配词汇，用于生成评分原因（ScoreReason）

**步骤2：协同增益判定**
- 检测是否同时存在：
  - `matched_struct` 非空 AND (`matched_nitro` 非空 OR `matched_signal` 非空)
- 满足条件则额外 +15分
- 生成特殊标识的评分原因：
  ```
  ScoreReason(
      category="synergy_bonus",
      points=15.0,
      description="[RELEVANT_CROSS_FIELD] 结构解析+固氮/信号机制交叉 (+15分)"
  )
  ```
- **关键标记说明**：`[RELEVANT_CROSS_FIELD]` 标识用于 AI 报告生成阶段，指示 LLM 对该文章"加大解析力度"

**步骤3：来源与突破加权**
- 保留现有的顶刊来源加分（+20分）
- 保留 Europe PMC 特异性加分（+5分）
- 保留结构突破组合词加分（+15分）
- 保留预印本结构研究加分（+10分）

**步骤4：引用与新鲜度**
- 保持现有逻辑不变
- 引用数：每条引用 +2分
- 新鲜度：30 天内按 `(30 - days_diff) * 0.5` 计算（最高 +15分）

#### 2.3 评分计算示例

**案例：固氮酶结构解析预印本**

| 评分项 | 匹配内容 | 得分 |
|--------|----------|------|
| 结构核心词 | `cryo-em`, `atomic resolution` | 15 + 15 = 30 |
| 固氮核心词 | `nitrogenase` | 8 |
| 协同增益 | 结构词 + 固氮词 | +15 |
| 预印本结构 | BioRxiv + structure | +10 |
| 新鲜度 | 发布 3 天前 | (30-3)*0.5 = 13.5 |
| **总分** | | **76.5** |

**结果**：文章直接进入 P0 级别（≥50分），在 AI 报告中优先解读。

---

### 三、数据模型影响

#### 3.1 无需变更数据库结构

当前 `ScoreReason` 模型已支持自定义 `category` 和 `description`，协同增益可直接使用：

```
ScoreReason(
    category="synergy_bonus",
    points=15.0,
    description="[重磅] 结构解析+固氮/信号机制交叉 (+15分)"
)
```

#### 3.2 评分原因类别扩展

新增评分类别：

| category | 含义 | 示例描述 |
|----------|------|----------|
| `struct_match` | 结构关键词匹配 | "命中结构核心词: cryo-em, atomic resolution (+30)" |
| `field_match` | 领域关键词匹配 | "命中固氮/信号词: nitrogenase, nif (+16)" |
| `synergy_bonus` | 协同增益 | "[重磅] 结构解析+固氮/信号机制交叉 (+15分)" |

---

### 四、可观测性增强

#### 4.1 评分原因展示

在 AI 生成的报告中，用户将看到明确的评分拆解：

**示例输出**：
```
📄 Cryo-EM structure of nitrogenase complex reveals catalytic mechanism
📊 评分: 76.5 (P0 级别 - 突破性工作)

评分详情:
  ✅ 命中结构核心词: cryo-em, atomic resolution (+30分)
  ✅ 命中固氮/信号词: nitrogenase, nif (+16分)
  🔥 [RELEVANT_CROSS_FIELD] 结构解析+固氮/信号机制交叉 (+15分)
  ✅ 预印本结构研究 (+10分)
  ✅ 新鲜度: 3天前 (+13.5分)
```

#### 4.2 与 AI 生成系统的集成

**标记驱动的 LLM 提示增强**：

在调用 AI 生成报告时，系统可根据 `[RELEVANT_CROSS_FIELD]` 标记动态调整 Prompt：

| 评分类型 | 标记 | LLM Prompt 策略 |
|---------|------|----------------|
| P0 + 协同增益 | `[RELEVANT_CROSS_FIELD]` | "这是一篇跨学科重点文章，请详细解析其结构生物学方法与领域问题的结合点，篇幅不少于 200 字" |
| P0 无协同 | 无特殊标记 | "这是一篇高分文章，请概述其核心贡献，篇幅约 150 字" |
| P1/P2 | 无特殊标记 | "简要总结该文章的研究方向和主要发现，篇幅约 80 字" |

**实现方式**：

在 `app/llm/generator.py` 中检测 `reasons` 列表：
```
def generate_paper_summary(scored_paper: ScoredPaper) -> str:
    has_cross_field = any(
        '[RELEVANT_CROSS_FIELD]' in reason.description 
        for reason in scored_paper.reasons
    )
    
    if has_cross_field:
        prompt_suffix = "（重点关注：这是跨学科交叉研究，请深度解析其方法学创新和领域意义）"
        min_length = 200
    else:
        prompt_suffix = ""
        min_length = 150 if scored_paper.score >= 50 else 80
    
    # ... 构建 Prompt 并调用 LLM
```

**预期效果**：
- 协同增益文章的 AI 解读深度提升 30-50%
- 用户能更清晰地理解"为何系统认为这篇文章重要"

#### 4.3 诊断日志输出

**日志分级策略**：

| 日志级别 | 记录内容 | 用途 |
|---------|---------|------|
| INFO | 评分汇总、P0/P1/P2 分布 | 日常监控 |
| DEBUG | 每篇文章的匹配关键词列表、协同增益触发详情 | 权重调优 |
| WARNING | 豁免机制触发记录（含文章标题） | 误报审计 |

**示例日志**：
```
DEBUG - [评分详情] title="Cryo-EM structure of nitrogenase..."
  matched_struct=['cryo-em', 'atomic resolution']
  matched_nitro=['nitrogenase']
  synergy_triggered=True
  final_score=76.5

WARNING - [结构豁免] 论文包含排除词但保留: title="Human NLR protein structure reveals..."
  exclude_words=['human']
  exemption_keywords=['cryo-em', 'nlr structure']
```

**日志幂等性保障**：
- 确保同一篇论文在多次评分时产生相同日志（便于回溯分析）
- 在分布式环境中，通过 DOI 或 PMID 作为日志追踪 ID

---

## 预期效果

### 1. 固氮 P0 级文章更容易置顶

**优化前**：
- 一篇解析固氮酶结构的 BioRxiv 预印本，可能只得 35 分（结构词 15 + 固氮词 8 + 预印本 10 + 新鲜度 2）
- 排名落后，需人工筛选才能发现

**优化后**：
- 相同文章可得 63 分（结构词 15 + 固氮词 8 + 协同增益 15 + 预印本 10 + 新鲜度 15）
- 自动进入 P0 级别，系统优先推送

### 2. 筛选精度（Precision）提升

**单领域文章（非交叉）**：
- 只讲固氮但不涉及结构：约 20-30 分（P2 级别）
- 只讲结构但不涉及植物/微生物：约 25-35 分（P1 级别）
- 不会干扰核心阅读需求

**跨领域交叉文章**：
- 结构 + 固氮：50-80 分（P0 级别）
- 结构 + 信号：50-75 分（P0 级别）
- 精准匹配博士的核心研究方向

### 3. 可解释性增强

- 用户可通过 `[重磅]` 标识快速识别系统推荐理由
- 避免"黑箱"评分带来的信任问题
- 便于后续调整权重策略

---

## 实施要点

### 1. 配置项管理原则

- **分离关注点**：检索用关键词（`RESEARCH_TOPICS`）与评分用关键词（`STRUCT_KEYWORDS` 等）独立维护
- **避免重复**：新增配置项与现有 `JOURNAL_IMPACT_MAP` 平级放置，不重复定义
- **易扩展**：未来可按需添加 `MICROBIO_KEYWORDS`（微生物核心词）等新领域

### 2. 评分逻辑可维护性

- **幂等性**：确保同一篇论文多次评分结果一致
- **原子性**：每个评分项独立计算，互不影响
- **可追溯**：通过 `ScoreReason` 记录每一项得分的来源

### 3. 兼容性保障

- **向后兼容**：现有配置项（如 `JOURNAL_IMPACT_MAP`）保持不变
- **增量修改**：仅在 `Config` 类中新增属性，不删除旧代码
- **渐进式部署**：可先部署配置层，再上线评分逻辑

---

## 风险与限制

### 1. 过拟合风险

**风险**：过度优化特定词汇组合，可能漏掉新兴研究方向

**缓解措施**：
- 保留原有的宽泛关键词（`RESEARCH_TOPICS`）用于数据源检索
- 定期审查 P1/P2 级别文章，发现遗漏的高价值论文并更新词库

### 2. 权重调整成本

**风险**：15分的协同增益权重可能过高或过低，需实际运行后调整

**缓解措施**：
- 配置项集中在 `Config` 类，修改成本低
- 通过日志和报告观察评分分布，基于数据调整

**权重校准方法**（实施 7 天后执行）：
1. 统计 P0 级别文章的评分分布（箱线图）
2. 检查协同增益触发的文章中，用户实际阅读的比例（通过推送后反馈）
3. 若 P0 文章过多（>10 篇/天），可降低协同增益至 10 分
4. 若协同增益文章的用户满意度 >90%，可维持 15 分或提升至 20 分

### 3. 计算复杂度

**风险**：增加关键词匹配和协同判定逻辑，可能略微影响性能

**评估**：
- 每篇文章的评分时间增加约 1-2ms（文本匹配开销）
- 在日推送量 < 500 篇的场景下，总体影响可忽略不计

**性能优化建议**（可选）：
- 若未来关键词列表扩展至 100+ 条，可使用 Trie 树或 Aho-Corasick 算法加速多模式匹配
- 对于 PubMed 摘要提取，若遇到 API 限流，可实施本地缓存（将 XML 结果存入 SQLite）

---

## 第三部分：PubMed 数据源深度优化

### 一、摘要提取逻辑修复

#### 1.1 问题根源

当前实现在第 65 和 79 行硬编码 `abstract=''`，原因是未正确解析 PubMed XML 响应中的 `AbstractText` 节点。

#### 1.2 解决方案

**提取路径**：
```
PubmedArticle → MedlineCitation → Article → Abstract → AbstractText
```

**处理策略**：
- PubMed 摘要可能分段存储（如 Background、Methods、Results、Conclusion），需遍历 `AbstractText` 列表
- 每个片段通过 `str()` 转换为纯文本
- 最终用空格拼接为完整摘要

**示例逻辑**：
```
abstract_parts = []
abstract_data = article_data.get('Abstract', {}).get('AbstractText', [])
for part in abstract_data:
    abstract_parts.append(str(part))
abstract = " ".join(abstract_parts)
```

#### 1.3 特殊情况处理

**带标签的摘要片段**：

PubMed XML 中的 `AbstractText` 节点可能带有 `Label` 属性，例如：
```xml
<AbstractText Label="METHODS">We performed cryo-EM analysis...</AbstractText>
<AbstractText Label="RESULTS">The structure reveals...</AbstractText>
```

**优化措施**：
- Biopython 的 `Entrez.read()` 会自动处理这些标签，`str(part)` 已能提取纯文本
- 在拼接前对每个片段执行 `strip()` 清理操作，防止双空格或不必要的换行符
- 最终逻辑：
  ```
  abstract_parts = [str(part).strip() for part in abstract_data if str(part).strip()]
  abstract = " ".join(abstract_parts)
  ```

**边界情况**：
- 若 `AbstractText` 为空列表，则 `abstract = ""`（保持向后兼容）
- 若某些片段为空字符串，通过列表推导式过滤（`if str(part).strip()`）

#### 1.4 链路影响

修复后，摘要将传递到以下环节：
- **评分系统**：`score_paper` 中的关键词匹配基于 `(title + abstract).lower()`
- **过滤系统**：`should_exclude_paper` 能检测摘要中的排除词（如 `clinical trial`、`human patient`）
- **AI 生成**：LLM 可基于完整摘要生成更准确的研究解读

---

### 二、排除过滤增强

#### 2.1 当前过滤流程缺陷

现有代码在第 65 行对空摘要执行过滤：
```
paper = Paper(title=title, abstract='', ...)
if should_exclude_paper(paper, exclude_keywords):
    continue
```

由于 `abstract=''`，`should_exclude_paper` 只能检查标题中的排除词，导致以下问题：
- 标题中包含 `nitrogen fixation` 但摘要讨论人类临床试验的文章，无法被过滤
- 标题中使用缩写（如 NF）的医学文章，绕过了排除词检测

#### 2.2 优化策略

**提取摘要后再过滤**：
```
paper = Paper(
    title=title,
    abstract=abstract,  # 完整摘要
    date=final_date,
    source='PubMed',
    doi=doi,
    link=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
)

# 此时过滤器能检测标题 + 摘要中的所有排除词
if should_exclude_paper(paper, exclude_keywords):
    stat["excluded"] += 1
    continue
```

#### 2.3 精度提升预估

| 场景 | 优化前 | 优化后 |
|------|--------|--------|
| 标题含目标词但摘要涉及医学临床 | 保留（误报） | 排除 |
| 标题含目标词且摘要涉及植物/微生物 | 保留（正确） | 保留 |
| 标题含排除词 | 排除（正确） | 排除 |

预计可降低 **30-40%** 的非目标领域文章（基于 PubMed MeSH 交叉污染现象）。

---

### 三、结构生物学豁免机制整合

#### 3.1 问题背景

BioRxiv 数据源已实现豁免逻辑（参见 `app/sources/biorxiv.py`）：
- 如果论文包含 `STRUCTURE_KEYWORDS`（如 `cryo-em`、`crystal structure`），即使触发排除词（如 `human`），仍予以保留
- 理由：人类蛋白结构研究（如 NLR 免疫受体）对植物研究有重要参考价值

PubMed 当前未实现此机制，导致高价值结构文章被错误过滤。

#### 3.2 解决方案

**修改 `filtering.py` 中的 `should_exclude_paper`**：

| 当前逻辑 | 优化后逻辑 |
|---------|-----------|
| 检测到排除词 → 直接返回 True | 检测到排除词 → 检查是否包含豁免词 → 包含则返回 False，否则返回 True |

**伪逻辑**：
```
if any(exclude_keyword in text):
    # 检查豁免条件
    if any(struct_keyword in text for struct_keyword in Config.STRUCTURE_KEYWORDS):
        return False  # 豁免，不排除
    return True  # 正常排除
return False  # 无排除词
```

**日志记录**：

当触发豁免机制时，应记录 DEBUG 级别日志，便于后续审计：
```
if any(struct_keyword in text for struct_keyword in Config.STRUCTURE_KEYWORDS):
    logger.debug(f"[结构豁免] 论文包含排除词但保留: title='{paper.title[:50]}...'")
    return False
```

#### 3.3 适用场景

| 文章类型 | 排除词 | 豁免词 | 最终结果 |
|---------|--------|--------|----------|
| 人类 NLR 蛋白冷冻电镜结构 | `human` | `cryo-em`, `nlr structure` | 保留 |
| 小鼠癌症临床试验 | `mouse`, `cancer` | 无 | 排除 |
| 拟南芥受体激酶晶体结构 | 无 | `crystal structure` | 保留 |

#### 3.4 豁免机制的潜在风险与缓解

**风险：关键词漂移（Keyword Drift）**

虽然 `cryo-em` 是高价值词，但可能出现在非目标场景中，例如：
```
"We used cryo-em as a reference to discuss our clinical results in cancer patients."
```

此类文章虽包含 `cryo-em`，但主题为临床研究，触发豁免会产生误报。

**当前策略（第一阶段）**：
- 保持简单的全文匹配逻辑
- 依赖协同增益机制降低误报影响（该类文章缺少领域关键词，评分不会进入 P0）
- 通过数据漏斗日志监控豁免触发频率

**未来优化方向（第二阶段）**：

如果在实际运行中发现豁免机制导致杂质增多（通过用户反馈或漏斗统计识别），可引入**近邻判定（Proximity Detection）**机制：

| 策略 | 判定逻辑 | 实现方式 |
|------|---------|----------|
| 位置优先 | 豁免词必须出现在摘要前 30% | 计算词汇在文本中的相对位置（字符索引 / 总长度） |
| 上下文验证 | 豁免词周围 50 字符内包含领域词 | 提取 `cryo-em` 前后 50 字符，检测是否含 `protein`、`structure`、`complex` 等 |
| 密度阈值 | 豁免词出现次数 ≥ 2 | 统计关键词频率，单次出现可能是引用，多次出现才是核心方法 |

**示例伪代码（近邻判定）**：
```
def is_structural_research(text: str, struct_keywords: List[str]) -> bool:
    """判断是否为真正的结构生物学研究"""
    for kw in struct_keywords:
        if kw in text:
            # 方案一：位置判定（简单）
            kw_pos = text.find(kw)
            if kw_pos / len(text) < 0.3:  # 出现在前30%
                return True
            
            # 方案二：上下文验证（精确）
            context = text[max(0, kw_pos-50):min(len(text), kw_pos+50)]
            if any(domain_kw in context for domain_kw in ['protein', 'enzyme', 'complex']):
                return True
    return False
```

**实施建议**：
- 第一阶段采用简单全文匹配，观察 7-14 天
- 若豁免误报率 > 20%（通过数据漏斗中 `excluded` 降低幅度与用户反馈交叉验证），启用近邻判定
- 优先采用"位置判定"方案（复杂度低，效果显著）

---

### 四、数据漏斗诊断日志

#### 4.1 设计目标

在 `fetch` 方法中引入统计计数器，记录每个过滤阶段的论文数量：

| 统计项 | 含义 | 计数时机 |
|--------|------|----------|
| `total` | 原始抓取总数 | 遍历 `PubmedArticle` 开始 |
| `excluded` | 被排除词过滤 | `should_exclude_paper` 返回 True |
| `date_filtered` | 日期不符合窗口 | `is_recent_date` 返回 False |
| `duplicate` | 去重命中 | `item_id in sent_ids` |
| `final` | 最终保留数 | 添加到 `papers` 列表 |

#### 4.2 实现方式

**初始化计数器**：
```
stat = {"total": 0, "excluded": 0, "date_filtered": 0, "duplicate": 0, "final": 0}
```

**在关键节点递增**：
```
for article in records.get('PubmedArticle', []):
    stat["total"] += 1
    try:
        # ... 提取逻辑 ...
        
        if should_exclude_paper(paper, exclude_keywords):
            stat["excluded"] += 1
            continue
        
        if not is_recent_date(paper.date, days=self.window_days):
            stat["date_filtered"] += 1
            continue
        
        if item_id in sent_ids:
            stat["duplicate"] += 1
            continue
        
        papers.append(paper)
        stat["final"] += 1
```

**输出日志**：
```
logger.info(f"PubMed 数据漏斗: {stat}")
```

#### 4.3 日志示例

```
INFO - PubMed 数据漏斗: {'total': 87, 'excluded': 23, 'date_filtered': 5, 'duplicate': 12, 'final': 47}
```

**解读**：
- 原始抓取 87 篇
- 排除过滤淘汰 23 篇（26.4%）
- 日期窗口淘汰 5 篇（5.7%）
- 去重淘汰 12 篇（13.8%）
- 最终保留 47 篇（54.0%）

---

### 五、日期提取健壮性增强

#### 5.1 当前问题

`_extract_date` 方法依赖多个日期字段的回退逻辑：
1. 优先尝试 `DateCompleted`
2. 回退到 `ArticleDate`
3. 最终返回 `default_date`（当天）

存在风险：
- 某些预印本的 `ArticleDate` 为空列表，导致 `IndexError`
- 日期格式不统一（如 `2025-1-5` vs `2025-01-05`），导致字符串比较异常

#### 5.2 优化策略

**统一日期格式化**：
```
if year:
    # 使用 zfill 确保月份和日期为两位数
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
```

**增加异常捕获范围**：
```
try:
    pub_date_list = article['MedlineCitation']['Article']['ArticleDate']
    if pub_date_list:  # 检查是否为空列表
        pub_date_obj = pub_date_list[0]
        # ...
except (KeyError, IndexError, TypeError, AttributeError):  # 扩展异常类型
    pass
```

#### 5.3 日期验证

在提取后验证日期有效性：
```
try:
    datetime.datetime.strptime(final_date, '%Y-%m-%d')
except ValueError:
    final_date = default_date  # 格式错误则回退
```

---

### 六、PMID 链接生成

#### 6.1 当前缺失

现有代码 `link=''`（第 83 行），导致：
- 用户无法直接跳转到原文
- 去重机制无法利用 PubMed URL 作为唯一标识

#### 6.2 解决方案

提取 PMID 并生成标准链接：
```
pmid = article['MedlineCitation']['PMID']
link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
```

**示例**：`https://pubmed.ncbi.nlm.nih.gov/12345678/`

---

### 七、优化后的完整数据流

**数据流图**（使用 Mermaid 表达）：

```
flowchart TD
    A[PubMed API 搜索] --> B[获取 ID 列表]
    B --> C[批量抓取 XML]
    C --> D[遍历 PubmedArticle]
    D --> E[提取标题 + 摘要 + 日期 + DOI + PMID]
    E --> F{排除词过滤}
    F -->|命中排除词| G{检查豁免词}
    G -->|包含结构词| H[保留]
    G -->|无豁免词| I[丢弃 - excluded++]
    F -->|无排除词| H
    H --> J{日期窗口验证}
    J -->|超出窗口| K[丢弃 - date_filtered++]
    J -->|在窗口内| L{去重检查}
    L -->|已推送| M[丢弃 - duplicate++]
    L -->|未推送| N[添加到结果集 - final++]
    N --> O[返回 SourceResult]
    I --> D
    K --> D
    M --> D
```

---

### 八、PubMed 优化的预期效果

#### 8.1 数据质量提升

| 指标 | 优化前 | 优化后 | 提升幅度 |
|------|--------|--------|----------|
| 摘要完整率 | 0% | 95%+ | ∞ |
| 排除过滤精度 | 60% | 85%+ | +41.7% |
| 结构文章保留率 | 70% | 95%+ | +35.7% |

#### 8.2 评分系统协同

有了完整摘要后，协同增益机制将在 PubMed 数据源生效：
- 一篇标题为 "Structural insights into nitrogenase" 但摘要中详细描述冷冻电镜方法的文章
- 优化前：只能通过标题匹配 `nitrogenase`（+8分），总分约 20-30 分（P2 级别）
- 优化后：摘要中匹配 `cryo-em`（+15分） + `nitrogenase`（+8分） + 协同增益（+15分），总分约 50+ 分（P0 级别）

#### 8.3 可观测性增强

通过数据漏斗日志，可快速定位问题：
- 如果 `excluded` 占比过高（>40%），说明检索关键词过于宽泛，需优化 MeSH 查询
- 如果 `duplicate` 占比过高（>30%），说明窗口期设置不当或数据源更新频率过低
- 如果 `final` 数量过少（<10），可能需要扩大检索范围或增加数据源

---

## 后续扩展方向

1. **多领域协同**：支持三领域交叉（如"固氮 + 信号 + 结构"），再额外 +10 分
2. **动态权重**：根据历史推送反馈（用户点击率、标记为重要等）自动调整关键词权重
3. **负向关键词**：新增"负向协同"机制，降低非目标领域文章的评分（如"癌症 + 结构"虽有结构词但不相关）
4. **配置可视化**：提供 Web 界面，允许用户在线调整关键词和权重，无需修改代码
5. **Europe PMC 对齐**：将 PubMed 的优化逻辑（摘要提取、豁免机制）同步应用到 Europe PMC 数据源
6. **语义去重**：基于摘要向量相似度检测同一研究的多次发表（预印本 → 正式刊）

---

## 实施检查清单

### 第一阶段：配置与评分优化

- [ ] 在 `app/config.py` 中添加 `STRUCT_KEYWORDS`、`NITRO_KEYWORDS`、`SIGNAL_KEYWORDS`、`BREAKTHROUGH_KEYWORDS`
- [ ] 更新 `app/scoring.py`：
  - [ ] 修改关键词匹配逻辑，使用 `Config` 中的新配置项
  - [ ] 新增协同增益判定逻辑
  - [ ] 更新 `ScoreReason` 的 `category` 和 `description`
- [ ] 验证测试（评分系统）：
  - [ ] 使用固氮酶结构文章测试，确认能达到 P0 级别（≥50 分）
  - [ ] 使用纯固氮文章（无结构词）测试，确认保持在 P2 级别（<30 分）
  - [ ] 检查评分原因展示是否包含 `[重磅]` 标识

### 第二阶段：PubMed 数据源优化

- [ ] 更新 `app/sources/pubmed.py`：
  - [ ] 修复摘要提取逻辑（解析 `AbstractText` 节点）
  - [ ] 调整过滤顺序（先提取完整数据，再执行过滤）
  - [ ] 添加 PMID 链接生成逻辑
  - [ ] 增加数据漏斗统计计数器（`stat` 字典）
  - [ ] 增强日期提取的异常处理和格式化
- [ ] 更新 `app/filtering.py`：
  - [ ] 在 `should_exclude_paper` 中实现结构生物学豁免机制
  - [ ] 添加豁免触发的 DEBUG 级别日志
- [ ] 验证测试（PubMed 数据源）：
  - [ ] 抓取包含固氮关键词的文章，检查摘要是否完整
  - [ ] 使用含 `clinical trial` 摘要的文章，确认被正确排除
  - [ ] 使用含 `human` + `cryo-em` 的文章，确认触发豁免
  - [ ] 检查日志中是否输出数据漏斗统计信息

### 第三阶段：集成测试与监控

- [ ] 端到端测试：
  - [ ] 运行完整推送流程，确认 PubMed 文章能正常进入评分系统
  - [ ] 验证协同增益机制在 PubMed 数据上的触发效果
  - [ ] 检查 AI 生成报告中是否包含完整摘要信息
- [ ] 日志观察（7 天运行期）：
  - [ ] 统计 P0/P1/P2 分布，评估权重合理性
  - [ ] 分析 PubMed 数据漏斗，评估排除过滤精度
  - [ ] 对比优化前后的推送质量（用户反馈、误报率）
- [ ] 文档更新：
  - [ ] 在项目 Wiki 的"智能评分系统"章节中补充协同增益机制说明
  - [ ] 在"数据采集"章节中更新 PubMed 优化内容（摘要提取、豁免机制）
  - [ ] 添加故障排除条目："PubMed 摘要为空" 的诊断步骤
