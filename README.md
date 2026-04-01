# 一念 (Yinian) CLI

<div align="center">

**最省钱的 AI 助手 CLI — 自动选模型、智能路由、管道友好**

[English](#english) · [安装](#安装) · [快速开始](#快速开始) · [功能特色](#功能特色) · [支持模型](#支持模型) · [配置](#配置) · [开发](#开发)

</div>

---

## ✨ 特性

- 🧠 **智能路由** — 根据问题类型自动选择最合适的模型（代码 → DeepSeek/GLM，闲聊 → 豆包，英文 → 通义）
- 💰 **成本最优** — `--fast` 模式下自动选最便宜的可用模型，省钱又高效
- ⚡ **本地模型** — 支持 Llama.cpp 本地部署，零成本离线使用 Qwen3.5-9B
- 📊 **用量透明** — 每次调用清晰显示 Token 消耗和费用
- 💾 **智能缓存** — 相同问题自动命中缓存，省时省钱
- 🔗 **管道友好** — 天然支持 Linux/Unix 管道，`cat error.log | yinian "分析报错"`
- 🎨 **优雅输出** — Markdown 渲染、代码高亮、语法高亮

---

## 安装

### pip 安装

```bash
pip install -e .
```

### 升级

```bash
pip install -e . --upgrade
```

### 前置要求

- Python 3.10+
- [Llama.cpp](https://github.com/ggerganov/llama.cpp)（可选，用于本地模型）

---

## 快速开始

### 基础问答

```bash
# 直接提问
yinian "如何用 Python 写快排？"

# 指定模型
yinian "翻译成英文：我爱中国" --model kimi

# 管道输入
cat error.log | yinian "分析这个报错"
```

### 智能自动模式 (`--fast`)

无需指定模型，AI 自动根据问题类型选择最合适的：

```bash
yinian "用Python写一个网页爬虫" --fast
# 输出: ⚡ 智能模式 → code → deepseek (¥0.0030/1K, 置信度 95%)

yinian "你好，今天心情不错" --fast
# 输出: ⚡ 智能模式 → chinese → doubao (¥0.0060/1K, 置信度 80%)
```

### 多模型对比

```bash
yinian "解释一下什么是量子纠缠" --compare deepseek kimi qwen
```

### REPL 交互模式

```bash
yinian

# 在 REPL 内:
🤖 一念 REPL — 交互式对话
模型: deepseek  │  会话: default

你: 你好
AI: 你好！有什么可以帮你的吗？

/help        查看所有命令
/model kimi  切换模型
/cheap       开启智能省心模式（每条消息自动路由最便宜）
/sessions    查看所有会话
/exit        退出
```

---

## 功能特色

### 智能路由规则

| 问题类型 | 路由模型 | 说明 |
|---------|---------|------|
| `code` | zhipu / deepseek | 代码编写、调试、解释 |
| `math` | deepseek / zhipu | 数学计算、公式推导 |
| `chinese` | doubao / kimi | 中文内容创作、闲聊 |
| `english` | qwen / zhipu | 英文写作、翻译 |
| `quick` | deepseek / qwen | 快速问答、事实查询 |

> 路由优先级可配置，无 API Key 时自动 fallback 到本地模型

### 模型费用参考

| 模型 | 输入 ¥/1K | 输出 ¥/1K | 备注 |
|------|----------|----------|------|
| GLM-4-Flash | ¥0.0001 | ¥0.0001 | 免费额度大 |
| Qwen3.5-Flash | ¥0.0002 | ¥0.002 | 性价比高 |
| DeepSeek V3 | ¥0.001 | ¥0.002 | 均衡 |
| Doubao-Pro | ¥0.003 | ¥0.003 | 稳定 |
| Kimi moonshot-v1 | ¥0.012 | ¥0.012 | 长上下文 |

### 会话管理

```bash
yinian session list    # 查看所有会话
yinian session save     # 保存当前会话
yinian session load     # 加载会话
yinian session clean    # 清理旧会话
```

### 用量统计

```bash
yinian stats
```

---

## 支持模型

### 云端模型

| 模型 | 模型 ID | 状态 |
|------|---------|------|
| DeepSeek V3 | `deepseek-chat` | ✅ |
| DeepSeek R1 | `deepseek-reasoner` | ✅ |
| Kimi (Moonshot) | `moonshot-v1-8k` | ✅ |
| 通义千问 | `qwen3.5-flash` | ✅ |
| 智谱 GLM | `glm-4-flash` | ✅ |
| 百度文心 | `ernie-4.0-8k` | ✅ |
| 字节豆包 | `doubao-pro-32k` | ✅ |
| 腾讯混元 | `hunyuan-pro` | ✅ |
| MiniMax M2.7 | `MiniMax-M2.7` | ✅ |

### 本地模型

```bash
# 配置本地 Llama.cpp 模型
yinian config set models.llama.base_url http://localhost:8080/v1
yinian config set models.llama.model Qwen3.5-9B-Q4_K_M
yinian config set models.llama.api_key local
```

---

## 配置

### 首次配置

```bash
# 设置 API Key
yinian config set deepseek.api_key sk-xxxxx
yinian config set kimi.api_key sk-xxxxx
yinian config set zhipu.api_key xxxxxx

# 查看配置
yinian config list

# 查看路由规则
yinian config get router.rules
```

### 配置文件

配置文件位于 `~/.yinian/config.json`：

```json
{
  "router": {
    "strategy": "auto",
    "rules": {
      "code": "deepseek",
      "chinese": "doubao",
      "english": "qwen"
    }
  },
  "defaults": {
    "fast_model": "deepseek",
    "best_model": "deepseek-r1"
  }
}
```

---

## CLI 参数

```
yinian [OPTIONS] [QUESTION]
```

| 参数 | 说明 |
|------|------|
| `--model, -m` | 指定模型 |
| `--compare, -c` | 多模型对比 |
| `--fast` | 智能自动模式（选最便宜） |
| `--best` | 精准模式（用最强模型） |
| `--dry-run` | 仅显示路由结果，不实际调用 |
| `--file, -f` | 从文件读取内容 |
| `--system, -s` | 设置系统提示词 |

---

## 开发

### 安装开发环境

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest tests/ -v
```

### 项目结构

```
yinian/
├── cli/            # 命令行入口
│   ├── ask.py      # 问答命令
│   ├── config.py   # 配置命令
│   ├── session.py  # 会话管理
│   └── stats.py    # 用量统计
├── core/           # 核心模块
│   ├── router.py   # 智能路由引擎
│   ├── cache.py    # 响应缓存
│   ├── session.py  # 会话管理
│   └── config.py   # 配置管理
└── models/         # 模型适配器
    ├── deepseek.py
    ├── kimi.py
    ├── qwen.py
    └── ...
```

---

## License

MIT License

---

# English

## Yinian CLI

**The most cost-effective AI assistant CLI — auto-select models, smart routing, pipe-friendly**

### Install

```bash
pip install -e .
```

### Quick Start

```bash
# Ask a question
yinian "How to write quicksort in Python?"

# Auto-select cheapest model (smart routing)
yinian "Write a Python web scraper" --fast

# Pipe input
cat error.log | yinian "Analyze this error"

# Interactive REPL
yinian
```

### Smart Routing

Automatically selects the best model based on question type:

| Type | Model | Use Case |
|------|-------|----------|
| `code` | zhipu / deepseek | Code writing, debugging |
| `math` | deepseek / zhipu | Math, formulas |
| `chinese` | doubao / kimi | Chinese content, chat |
| `english` | qwen / zhipu | English writing, translation |
| `quick` | deepseek / qwen | Quick Q&A |

### Configuration

```bash
# Set API key
yinian config set deepseek.api_key sk-xxxxx

# Local Llama.cpp model
yinian config set models.llama.base_url http://localhost:8080/v1
yinian config set models.llama.api_key local
```

### License

MIT
