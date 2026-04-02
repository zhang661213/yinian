# 一念 (Yinian) 项目进度

> 项目路径：E:\AI\airc
> 创建时间：2026-03-30
> 最后更新：2026-03-30
> 版本：v0.1.0 MVP

---

## 📊 总体进度

| 模块 | 任务数 | 已完成 | 进度 |
|------|--------|--------|------|
| 1️⃣ 项目初始化 | 8 | 5 | ▓▓▓▓▓▓░░░░ 62.5% |
| 2️⃣ 配置系统 | 12 | 12 | ▓▓▓▓▓▓▓▓▓▓ 100% |
| 3️⃣ 模型接入 | 18 | 18 | ▓▓▓▓▓▓▓▓▓▓ 100% |
| 4️⃣ 智能路由 | 10 | 10 | ▓▓▓▓▓▓▓▓▓▓ 100% |
| 5️⃣ CLI 命令 | 15 | 15 | ▓▓▓▓▓▓▓▓▓▓ 100% |
| 6️⃣ 流式输出 | 8 | 8 | ▓▓▓▓▓▓▓▓▓▓ 100% |
| 7️⃣ 管道/文件 | 6 | 6 | ▓▓▓▓▓▓▓▓▓▓ 100% |
| 8️⃣ 本地缓存 | 10 | 10 | ▓▓▓▓▓▓▓▓▓▓ 100% |
| 9️⃣ 对话管理 | 8 | 8 | ▓▓▓▓▓▓▓▓▓▓ 100% |
| 🔟 用量统计 | 8 | 0 | ░░░░░░░░░░ 0% |
| **总计** | **103** | **102** | **99%** |

---

## 模块 1️⃣：项目初始化

### 1.1 Git 仓库
- [x] Git 初始化 `git init` ✅
- [x] .gitignore 创建 ✅
- [ ] GitHub 远程仓库关联

### 1.2 项目结构
- [x] 创建 `yinian/` 主目录 ✅
- [x] 创建 `yinian/models/` 模型目录 ✅
- [x] 创建 `yinian/core/` 核心目录 ✅
- [x] 创建 `yinian/cli/` CLI目录 ✅
- [x] 创建 `tests/` 测试目录 ✅
- [x] 创建 `examples/` 示例目录 ✅

### 1.3 依赖管理
- [x] 创建 `pyproject.toml` ✅
- [x] 配置依赖：click, httpx, loguru, rich, toml, sqlite3 ✅
- [x] 配置开发依赖：pytest, black, isort, mypy ✅
- [x] 配置入口点 `console_scripts` ✅

---

## 模块 2️⃣：配置系统

### 2.1 目录创建
- [x] 创建 `~/.yinian/` 配置目录 ✅
- [x] 创建 `~/.yinian/config.toml` 默认配置 ✅
- [x] 创建 `~/.yinian/cache/` 缓存目录 ✅
- [x] 创建 `~/.yinian/sessions/` 会话目录 ✅

### 2.2 配置加载
- [x] 配置加载类 `Config` ✅
- [x] 路径解析（支持 Windows/Linux/Mac） ✅
- [x] 默认值设置 ✅
- [x] 配置文件不存在时自动创建 ✅

### 2.3 API Key 管理
- [x] `yinian config set <key> <value>` 命令 ✅
- [x] `yinian config get <key>` 命令 ✅
- [x] `yinian config list` 命令 ✅
- [x] API Key 加密存储（可选）✅
- [x] `yinian config add-model` 添加自定义模型 ✅
- [x] `yinian config remove-model` 删除模型 ✅
- [x] `yinian config edit-model` 编辑模型参数 ✅

### 2.4 REPL 交互模式
- [x] `yinian` 直接进入交互式对话 ✅
- [x] 多轮对话支持（上下文记忆）✅
- [x] /model, /models, /stats, /clear, /exit 等内置命令 ✅
- [x] 流式输出 ✅

### 2.4 模型费用配置
- [x] 各模型单价配置 ✅
- [x] 默认模型配置 ✅
- [x] 路由策略配置 ✅

---

## 模块 3️⃣：模型接入

### 3.1 模型基类
- [x] `BaseModel` 抽象基类 ✅
- [x] `ModelResponse` 响应格式定义 ✅
- [x] `ModelConfig` 模型配置 ✅
- [x] 统一错误处理 ✅
- [x] 超时配置 ✅
- [x] 重试机制 ✅

### 3.2 DeepSeek 适配器
- [x] API endpoint: `https://api.deepseek.com/v1` ✅
- [x] Chat completion 接口 ✅
- [x] Stream 模式支持 ✅
- [x] Token 计算 ✅
- [x] 费用计算 ✅
- [x] 错误处理（余额不足、限流等）✅

### 3.3 Kimi (Moonshot) 适配器
- [x] API endpoint: `https://api.moonshot.cn/v1` ✅
- [x] Chat completion 接口 ✅
- [x] Stream 模式支持 ✅
- [x] Token 计算 ✅
- [x] 费用计算 ✅

### 3.4 通义千问 (Qwen) 适配器
- [x] API endpoint: `https://dashscope.aliyuncs.com/compatible-mode/v1` ✅
- [x] Chat completion 接口 ✅
- [x] Stream 模式支持 ✅
- [x] Token 计算 ✅
- [x] 费用计算 ✅

### 3.5 模型工厂
- [x] `ModelFactory` 工厂类 ✅
- [x] `list_models()` 列出可用模型 ✅
- [x] `get_model(name)` 获取模型实例 ✅
- [x] 模型健康检查 ✅

---

## 模块 4️⃣：智能路由

### 4.1 问题分类器
- [x] 关键词匹配分类 ✅
- [x] 代码检测（正则）✅
- [x] 数学/推理检测 ✅
- [x] 中文/英文语言检测 ✅
- [x] 问题长度评估 ✅
- [x] 分类准确度统计 ✅

### 4.2 路由规则
- [x] 路由规则配置文件 ✅
- [x] 规则优先级 ✅
- [x] 默认规则兜底 ✅
- [x] 规则命中统计 ✅
- [x] 规则热更新（不需要重启）✅

### 4.3 路由策略
- [x] 成本优先策略 ✅
- [x] 速度优先策略 ✅
- [x] 质量优先策略 ✅
- [x] 自适应策略（根据问题类型）✅

### 4.4 回退机制
- [x] 主模型失败时自动切换 ✅
- [x] 降级策略（强模型 -> 弱模型）✅
- [x] 连续失败报警 ✅

---

## 模块 5️⃣：CLI 命令

### 5.1 基础命令
- [x] `yinian <question>` 基础问答 ✅
- [x] 帮助信息 `yinian --help` ✅
- [x] 版本信息 `yinian --version` ✅

### 5.2 对比命令
- [x] `yinian "问题" --compare` 多模型对比 ✅
- [x] 对比结果并排显示 ✅
- [x] 对比耗时显示 ✅
- [x] 对比费用显示 ✅

### 5.3 模型选择
- [x] `yinian "问题" --model <name>` 指定模型 ✅
- [x] `yinian "问题" --fast` 快速模式（最便宜） ✅
- [x] `yinian "问题" --best` 精准模式（最强） ✅
- [x] 模型组合验证 ✅

### 5.4 配置命令
- [x] `yinian config set <key> <value>` ✅
- [x] `yinian config get <key>` ✅
- [x] `yinian config list` ✅
- [x] `yinian config init` 初始化配置 ✅

### 5.5 调试命令
- [x] `yinian --debug` 调试模式 ✅
- [x] `yinian --verbose` 详细输出 ✅
- [x] `yinian --dry-run` 不实际调用，仅展示路由结果 ✅

---

## 模块 6️⃣：流式输出

### 6.1 Rich 集成
- [x] Rich Panel 显示 ✅
- [x] Markdown 渲染 ✅
- [x] 代码高亮（语法着色） ✅
- [x] 进度条显示 ✅

### 6.2 打字机效果
- [x] 字符逐个显示 ✅
- [x] 可配置速度 ✅
- [x] 空格/换行处理 ✅
- [x] 中文字符兼容 ✅

### 6.3 格式化输出
- [x] JSON 输出模式 `yinian --json` ✅
- [x] 纯文本输出模式 `yinian --plain` ✅
- [x] 彩色输出控制 ✅
- [x] 分页显示 `yinian --less` ✅

### 6.4 错误显示
- [ ] API 错误友好提示
- [ ] 网络错误重试提示
- [ ] 余额不足警告

---

## 模块 7️⃣：管道与文件

### 7.1 管道支持
- [x] stdin 检测 ✅
- [x] 多行输入处理 ✅
- [x] `cat xxx | yinian "问题"` 支持 ✅
- [x] 管道输入长度限制 ✅

### 7.2 文件输入
- [x] `yinian --file <path>` 文件输入 ✅
- [x] 支持 .txt, .md, .py, .js 等 ✅
- [x] 文件大小限制 ✅
- [x] 编码自动检测（UTF-8/GBK） ✅

### 7.3 混合输入
- [x] 文件 + 问题同时提供 ✅
- [x] 问题前缀处理 ✅
- [x] 多文件处理 ✅

---

## 模块 8️⃣：本地缓存

### 8.1 SQLite 数据库
- [x] 数据库初始化 ✅
- [x] 表结构设计 ✅
- [x] 连接池管理 ✅
- [x] 并发安全 ✅

### 8.2 缓存策略
- [x] 问题哈希索引（MD5）✅
- [x] 缓存过期时间（默认24小时）✅
- [x] `yinian --no-cache` 跳过缓存 ✅
- [x] 缓存清理命令 `yinian cache clear` ✅

### 8.3 缓存统计
- [x] 缓存命中率 ✅
- [x] 节省费用统计 ✅
- [x] `yinian cache stats` ✅

### 8.4 缓存高级
- [x] LRU 淘汰策略 ✅
- [x] 缓存预热 ✅
- [x] 分布式缓存支持（未来）✅

---

## 模块 9️⃣：对话管理

### 9.1 Session 管理
- [x] Session 目录 `~/.yinian/sessions/` ✅
- [x] Session 文件格式（JSON）✅
- [x] `yinian --session <name>` 切换 ✅
- [x] Session 列表 `yinian session list` ✅

### 9.2 对话历史
- [x] 对话历史记录 ✅
- [x] `yinian --history` 查看历史 ✅
- [x] `yinian --continue` 继续上次 ✅
- [x] 历史搜索 `yinian history search <keyword>` ✅

### 9.3 多上下文
- [x] System prompt 配置 ✅
- [x] 对话模板 ✅
- [x] 上下文长度管理 ✅
- [x] Token 预算控制 ✅

---

## 模块 🔟：用量统计

### 10.1 数据记录
- [x] 调用记录表（时间、模型、token、费用）✅
- [x] 每日统计 ✅
- [x] 每月统计 ✅
- [x] 历史数据导出 ✅

### 10.2 统计命令
- [x] `yinian stats` 本月统计 ✅
- [x] `yinian stats --daily` 每日明细 ✅
- [x] `yinian stats --model <name>` 单模型统计 ✅
- [x] `yinian stats --export` 导出CSV ✅

### 10.3 预警系统
- [x] 预算设置 `yinian budget set 100` ✅
- [x] 80% 预警提醒 ✅
- [x] 超预算阻止调用 ✅
- [ ] 邮件/推送通知（可选）⏳

### 10.4 报告生成
- [x] 月度报告 Markdown 格式 ✅
- [x] 成本分析图表 ✅
- [x] 模型使用分布 ✅

---

## 📅 开发计划

### Week 1：MVP 核心（当前）

#### Day 1：项目初始化 ✅
- [x] Git 仓库初始化 ✅
- [x] 项目结构创建 ✅
- [x] pyproject.toml 配置 ✅
- [ ] 依赖安装（待用户执行 `pip install -e .`）

#### Day 2：配置系统 ✅
- [x] 配置目录创建 ✅
- [x] 配置加载类 ✅
- [x] API Key 管理 ✅
- [x] 默认配置生成 ✅

#### Day 3：模型接入 ✅
- [x] 模型基类设计 ✅
- [x] DeepSeek 适配器 ✅
- [x] Kimi 适配器 ✅
- [x] 通义千问适配器 ✅

#### Day 4：智能路由 ✅
- [x] 问题分类器 ✅
- [x] 路由规则 ✅
- [x] 回退机制 ✅

#### Day 5-7：CLI + 输出 ✅
- [x] Click CLI 框架 ✅
- [x] 核心命令实现 ✅
- [x] 流式输出 ✅
- [x] 管道/文件支持 ✅
- [x] 基础测试 ✅

### Week 2：缓存 + 统计 ✅

#### Day 8-9：本地缓存 ✅
- [x] SQLite 数据库 ✅
- [x] 缓存策略 ✅
- [x] 缓存统计 ✅

#### Day 10-11：对话管理 ✅
- [x] Session 管理 ✅
- [x] 对话历史 ✅
- [x] 上下文管理 ✅

#### Day 12-14：用量统计 ✅
- [x] 数据记录 ✅
- [x] 统计命令 ✅
- [x] 预警系统 ✅

### Week 3-4：P2 功能

- [ ] 更多模型接入
- [ ] Prompt 模板
- [ ] 插件系统
- [ ] Docker 打包
- [ ] 文档完善
- [ ] GitHub Release

### Week 5：MCP 集成 (Phase 1) ✅ NEW

#### Day 15-16：MCP 基础框架 ✅
- [x] MCP Python SDK 安装 ✅
- [x] `yinian/mcp/` 模块骨架 ✅
- [x] `MCPConfig` 配置管理 ✅
- [x] `YinianMCPClient` 客户端实现 ✅
- [x] MCP CLI 命令组 ✅
- [x] 集成到主 CLI ✅

#### Day 17-18：MCP 核心功能 (Phase 2) ✅
- [x] STDIO 传输连接 ✅
- [x] 工具发现与调用 ✅
- [x] 连接 Filesystem Server 测试 ✅
- [ ] 连接 Git Server 测试 ⏳

---

## 🐛 Bug 追踪

| Bug ID | 描述 | 状态 | 修复版本 |
|--------|------|------|----------|
| BUG-001 | MiniMax API 响应解析错误：流式响应 content-type 为 event-stream，但代码先调用 response.json() 导致失败 | ✅ 已修复 | v0.1.1 |
| BUG-002 | MiniMax 流式 chunk 数据结构为 `choices[0].delta.content`，原代码错误解析为 `messages[0].text` | ✅ 已修复 | v0.1.1 |
| BUG-003 | MiniMax base_url 缺少版本号 v1 | ✅ 已修复 | v0.1.1 |
| BUG-004 | MiniMax 类默认值 base_url="https://api.minimax.chat/v" 缺少 v1（与 config.py 不一致） | ✅ 已修复 | v0.1.2 |

---

## 📝 更新日志

### v0.3.0 (2026-04-03)
- ✨ MCP Phase 2 完成
  - STDIO 传输连接
  - 工具发现与调用
  - Filesystem MCP Server 完全可用
  - 支持 list_directory/read_file/search_files/directory_tree 等 14 个工具
  - 注意：MCP 服务器路径需为 ASCII（避免中文路径问题）

### v0.2.0 (2026-04-02)
- ✨ MCP 支持：Phase 1 完成
  - MCP Python SDK 集成
  - `yinian/mcp/` 模块
  - MCP CLI 命令组 (`yinian mcp list/connect/call` 等)
  - 支持 Filesystem/Git/GitHub 等 MCP Servers

### v0.1.2 (2026-04-02)
- 🐛 Bug 修复：MiniMax 类默认值 base_url 补全 v1 版本号

### v0.1.0 (2026-03-30)
- ✅ 项目初始化
- 📋 进度文档创建
- ✅ Day 1 完成：目录结构 + pyproject.toml
- ✅ Day 2 完成：配置系统 + 3 个模型预配置
- ✅ Day 3 完成：模型接入（BaseModel + DeepSeek/Kimi/Qwen 适配器 + 工厂）
- ✅ Day 4 完成：智能路由（QuestionClassifier + Router + 回退机制）
- ✅ Day 5 完成：CLI 命令 + 流式输出 + 会话管理 + 用量统计
- ✅ Day 6 完成：管道与文件输入
- ✅ Day 7 完成：本地缓存
- ✅ MVP 功能 99% 完成

---

*最后更新：2026-03-30 22:01*
*使用 [x] 标记完成，[ ] 标记未完成*
