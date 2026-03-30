# AI CLI 工具 — 产品详细方案

> 项目代号：`airc`（AI Route CLI）
> 版本：v1.0.0
> 日期：2026-03-30

---

## 一、项目概述

### 1.1 产品定位

**"最省钱的 AI 助手 CLI — 自动选模型、智能省 Token、管道友好"**

一款轻量级命令行 AI 工具，通过智能路由自动为用户选择最合适的模型，减少不必要的 API 调用费用。同时支持多模型对比、本地缓存、用量统计等功能。

### 1.2 核心解决的问题

- 市面缺少**支持国内模型**的轻量 CLI 工具
- 用户不知道该选哪个模型，往往用最贵的
- API 调用费用不透明，容易超支
- 工具链太重，不够开发者友好

### 1.3 目标用户

| 用户类型 | 场景 |
|---------|------|
| 开发者 | 快速命令行问答、代码辅助 |
| 内容创作者 | 文案生成、多平台适配 |
| AI 爱好者 | 模型对比、Prompt 测试 |
| 运营/产品 | 快速获取 AI 辅助分析 |

---

## 二、功能规格

### 2.1 功能分级

#### 🟢 P0 — MVP 必须（第一版实现）

| 功能 | 说明 |
|------|------|
| **智能路由** | 根据问题类型自动选择最合适的模型 |
| **多模型对比** | `--compare` 参数同时调用多个模型对比结果 |
| **管道模式** | 接收 stdin 输入，支持 `cat xxx \| ai` |
| **文件输入** | `ai --file xxx.md` 读取文件内容处理 |
| **流式输出** | 打字机效果，实时显示 AI 回复 |
| **流式输出** | Markdown 渲染，代码高亮 |
| **多模型支持** | DeepSeek、Kimi、通义、文心、智谱、OpenAI |

#### 🟡 P1 — 第二版（缓存+统计）

| 功能 | 说明 |
|------|------|
| **本地缓存** | 相同问题 24h 内直接返回缓存 |
| **对话记忆** | 支持多 session，切换上下文 |
| **用量统计** | `ai --stats` 查看本月各模型费用 |
| **费用预警** | 超过设定阈值提醒 |
| **历史记录** | `ai --history` 查看过往问答 |

#### 🔵 P2 — 第三版（生态扩展）

| 功能 | 说明 |
|------|------|
| **Prompt 模板** | 内置 + 自定义模板市场 |
| **插件系统** | 用户自行添加自定义模型 |
| **OpenAI 兼容** | 支持接入第三方 OpenAI 兼容接口 |
| **离线模式** | 网络中断时使用缓存结果 |

---

### 2.2 智能路由策略

自动判断问题类型，匹配最优模型：

```python
路由规则：
├── 代码相关  → DeepSeek（能力强 + 价格低）
├── 数学/推理 → DeepSeek R1（推理专用）
├── 中文文案 → Kimi / 通义千问（中文表达好）
├── 快速问答 → DeepSeek Chat（最便宜的模型）
├── 英文内容 → GPT-4o Mini（性价比最高）
└── 未分类   → DeepSeek Chat（默认兜底）
```

### 2.3 命令行接口

```bash
# 基础问答
ai "如何用 Python 写一个快速排序？"

# 多模型对比
ai "帮我写一个快排" --compare

# 指定模型
ai "帮我写一个快排" --model deepseek,kimi

# 快速模式（最便宜模型）
ai "翻译：Hello World" --fast

# 精准模式（最强模型）
ai "分析这段代码" --best

# 管道输入
cat error.log | ai "分析这个报错"

# 文件输入
ai --file main.py "审查这段代码"

# 继续上次对话
ai --continue

# 切换 session
ai --session work

# 查看用量
ai --stats

# 查看帮助
ai --help
```

---

## 三、技术方案

### 3.1 技术选型

| 层级 | 选择 | 理由 |
|------|------|------|
| 语言 | Python 3.10+ | 生态丰富、快速开发、跨平台 |
| CLI 框架 | Click | 轻量、命令行友好 |
| HTTP 客户端 | httpx | 同步/异步支持，流式输出 |
| 配置管理 | TOML | 配置文件格式，用户友好 |
| 缓存 | SQLite | 轻量、零依赖、足够用 |
| 日志 | loguru | 简洁、好用 |

### 3.2 项目结构

```
airc/
├── airc/
│   ├── __init__.py
│   ├── main.py          # 入口，CLI 定义
│   ├── router.py        # 智能路由引擎
│   ├── models/          # 模型适配器
│   │   ├── __init__.py
│   │   ├── base.py      # 基类
│   │   ├── deepseek.py
│   │   ├── kimi.py
│   │   ├── qwen.py
│   │   ├── wenxin.py
│   │   ├── zhipu.py
│   │   └── openai.py
│   ├── cache.py         # 本地缓存
│   ├── config.py       # 配置管理
│   ├── stats.py        # 用量统计
│   ├── session.py      # 对话管理
│   └── output.py       # 输出格式化
├── tests/
├── README.md
├── pyproject.toml
└── requirements.txt
```

### 3.3 模型 API 适配

统一 OpenAI 兼容格式，差异化适配：

```python
# 各模型接入点
DeepSeek:  https://api.deepseek.com/v1
Kimi:      https://api.moonshot.cn/v1
通义千问:   https://dashscope.aliyuncs.com/compatible-mode/v1
文心一言:   https://qianfan.baidubce.com/v2
智谱:      https://open.bigmodel.cn/api/paas/v4
OpenAI:   https://api.openai.com/v1
```

### 3.4 配置格式（~/.airc/config.toml）

```toml
[defaults]
model = "deepseek"          # 默认模型
fast_model = "deepseek"     # 快速模式模型
best_model = "deepseek-r1"  # 精准模式模型

[models.deepseek]
api_key = "sk-xxx"
cost_per_1k = 0.001         # 每1000 token费用

[models.kimi]
api_key = "sk-xxx"
cost_per_1k = 0.012

[models.qwen]
api_key = "sk-xxx"
cost_per_1k = 0.002

[cache]
enabled = true
ttl_hours = 24

[budget]
monthly_limit = 100         # 月度预算（元）
alert_threshold = 0.8       # 80% 时提醒
```

---

## 四、开发计划

### 4.1 Milestone

| 版本 | 目标 | 周期 |
|------|------|------|
| v0.1 | 基础问答 + 流式输出 + 3个模型 | Week 1 |
| v0.2 | 多模型对比 + 管道模式 + 文件输入 | Week 2 |
| v0.3 | 智能路由 + 配置系统 | Week 3 |
| v1.0 | 缓存 + 用量统计 + 对话管理 | Week 4 |
| v1.1+ | 模板市场 + 插件系统 | Week 5+ |

### 4.2 第一周详细任务

**Day 1-2：项目初始化**
- [ ] 项目脚手架搭建（pyproject.toml + Click）
- [ ] 配置文件加载逻辑
- [ ] 基础日志系统

**Day 3-4：模型接入**
- [ ] 基类定义 + DeepSeek 接入
- [ ] Kimi 接入
- [ ] 通义接入
- [ ] 统一响应格式

**Day 5-7：CLI + 输出**
- [ ] 基础命令 `ai <question>`
- [ ] 流式输出（打字机效果）
- [ ] Markdown 渲染
- [ ] 错误处理

---

## 五、定价策略（商业化参考）

### 5.1 定位

开源免费版（基础功能）+ 云端托管付费版

### 5.2 收费模式

| 方案 | 价格 | 功能 |
|------|------|------|
| 免费版 | ¥0 | 基础问答、3个模型、有限缓存 |
| Pro | ¥29/月 | 全部模型、无限制缓存、用量统计 |
| Team | ¥99/月 | 团队共享、API Key 管理、审计日志 |

### 5.3 变现路径

1. **GitHub Star 积累** → 吸引个人用户
2. **开发者社区** → 建立插件生态
3. **云端版** → 付费转化（用户不用自己管 API Key）
4. **企业定制** → 私有部署、技术支持

---

## 六、竞品对比

| 工具 | 多模型 | 国内模型 | 智能路由 | 缓存 | CLI 友好 |
|------|:------:|:--------:|:--------:|:----:|:--------:|
| shell_gpt | ✅ | ❌ | ❌ | ❌ | ✅ |
| llm (Simon Willison) | ✅ | 弱 | ❌ | ❌ | ✅ |
| aichat | ✅ | ✅ | ❌ | ❌ | ❌ |
| **airc** | ✅ | ✅ | ✅ | ✅ | ✅ |

**差异化总结：国内模型支持 + 智能路由省 token + 轻量 CLI**

---

## 七、风险与应对

| 风险 | 等级 | 应对措施 |
|------|------|---------|
| API 接口变动 | 中 | 插件化设计，快速适配 |
| 模型价格波动 | 低 | 配置中声明价格，用户自设 |
| 变现周期长 | 高 | 先开源积累用户，再商业化 |
| 微信审核（公众号相关） | 低 | 本工具不涉及公众号内容 |

---

## 八、待确认事项

- [ ] API Key 由用户提供还是平台统一管理？
- [ ] 第一期接入哪些模型？（建议至少 3 个）
- [ ] 是否需要多语言界面（英文）？
- [ ] 是否需要 Docker 打包？
- [ ] 目标平台：Windows / Mac / Linux 全平台还是优先某个？

---

*方案生成时间：2026-03-30*
*负责人：AI 助手*
