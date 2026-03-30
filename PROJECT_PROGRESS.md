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
| 4️⃣ 智能路由 | 10 | 0 | ░░░░░░░░░░ 0% |
| 5️⃣ CLI 命令 | 15 | 0 | ░░░░░░░░░░ 0% |
| 6️⃣ 流式输出 | 8 | 0 | ░░░░░░░░░░ 0% |
| 7️⃣ 管道/文件 | 6 | 0 | ░░░░░░░░░░ 0% |
| 8️⃣ 本地缓存 | 10 | 0 | ░░░░░░░░░░ 0% |
| 9️⃣ 对话管理 | 8 | 0 | ░░░░░░░░░░ 0% |
| 🔟 用量统计 | 8 | 0 | ░░░░░░░░░░ 0% |
| **总计** | **103** | **37** | **36%** |

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
- [ ] 关键词匹配分类
- [ ] 代码检测（正则）
- [ ] 数学/推理检测
- [ ] 中文/英文语言检测
- [ ] 问题长度评估
- [ ] 分类准确度统计

### 4.2 路由规则
- [ ] 路由规则配置文件
- [ ] 规则优先级
- [ ] 默认规则兜底
- [ ] 规则命中统计
- [ ] 规则热更新（不需要重启）

### 4.3 路由策略
- [ ] 成本优先策略
- [ ] 速度优先策略
- [ ] 质量优先策略
- [ ] 自适应策略（根据问题类型）

### 4.4 回退机制
- [ ] 主模型失败时自动切换
- [ ] 降级策略（强模型 -> 弱模型）
- [ ] 连续失败报警

---

## 模块 5️⃣：CLI 命令

### 5.1 基础命令
- [ ] `yinian <question>` 基础问答
- [ ] 帮助信息 `yinian --help`
- [ ] 版本信息 `yinian --version`

### 5.2 对比命令
- [ ] `yinian "问题" --compare` 多模型对比
- [ ] 对比结果并排显示
- [ ] 对比耗时显示
- [ ] 对比费用显示

### 5.3 模型选择
- [ ] `yinian "问题" --model <name>` 指定模型
- [ ] `yinian "问题" --fast` 快速模式（最便宜）
- [ ] `yinian "问题" --best` 精准模式（最强）
- [ ] 模型组合验证

### 5.4 配置命令
- [ ] `yinian config set <key> <value>`
- [ ] `yinian config get <key>`
- [ ] `yinian config list`
- [ ] `yinian config init` 初始化配置

### 5.5 调试命令
- [ ] `yinian --debug` 调试模式
- [ ] `yinian --verbose` 详细输出
- [ ] `yinian --dry-run` 不实际调用，仅展示路由结果

---

## 模块 6️⃣：流式输出

### 6.1 Rich 集成
- [ ] Rich Panel 显示
- [ ] Markdown 渲染
- [ ] 代码高亮（语法着色）
- [ ] 进度条显示

### 6.2 打字机效果
- [ ] 字符逐个显示
- [ ] 可配置速度
- [ ] 空格/换行处理
- [ ] 中文字符兼容

### 6.3 格式化输出
- [ ] JSON 输出模式 `yinian --json`
- [ ] 纯文本输出模式 `yinian --plain`
- [ ] 彩色输出控制
- [ ] 分页显示 `yinian --less`

### 6.4 错误显示
- [ ] API 错误友好提示
- [ ] 网络错误重试提示
- [ ] 余额不足警告

---

## 模块 7️⃣：管道与文件

### 7.1 管道支持
- [ ] stdin 检测
- [ ] 多行输入处理
- [ ] `cat xxx | yinian "问题"` 支持
- [ ] 管道输入长度限制

### 7.2 文件输入
- [ ] `yinian --file <path>` 文件输入
- [ ] 支持 .txt, .md, .py, .js 等
- [ ] 文件大小限制
- [ ] 编码自动检测（UTF-8/GBK）

### 7.3 混合输入
- [ ] 文件 + 问题同时提供
- [ ] 问题前缀处理
- [ ] 多文件处理

---

## 模块 8️⃣：本地缓存

### 8.1 SQLite 数据库
- [ ] 数据库初始化
- [ ] 表结构设计
- [ ] 连接池管理
- [ ] 并发安全

### 8.2 缓存策略
- [ ] 问题哈希索引（MD5）
- [ ] 缓存过期时间（默认24小时）
- [ ] `yinian --no-cache` 跳过缓存
- [ ] 缓存清理命令 `yinian cache clear`

### 8.3 缓存统计
- [ ] 缓存命中率
- [ ] 节省费用统计
- [ ] `yinian cache stats`

### 8.4 缓存高级
- [ ] LRU 淘汰策略
- [ ] 缓存预热
- [ ] 分布式缓存支持（未来）

---

## 模块 9️⃣：对话管理

### 9.1 Session 管理
- [ ] Session 目录 `~/.yinian/sessions/`
- [ ] Session 文件格式（JSON）
- [ ] `yinian --session <name>` 切换
- [ ] Session 列表 `yinian session list`

### 9.2 对话历史
- [ ] 对话历史记录
- [ ] `yinian --history` 查看历史
- [ ] `yinian --continue` 继续上次
- [ ] 历史搜索 `yinian history search <keyword>`

### 9.3 多上下文
- [ ] System prompt 配置
- [ ] 对话模板
- [ ] 上下文长度管理
- [ ] Token 预算控制

---

## 模块 🔟：用量统计

### 10.1 数据记录
- [ ] 调用记录表（时间、模型、token、费用）
- [ ] 每日统计
- [ ] 每月统计
- [ ] 历史数据导出

### 10.2 统计命令
- [ ] `yinian stats` 本月统计
- [ ] `yinian stats --daily` 每日明细
- [ ] `yinian stats --model <name>` 单模型统计
- [ ] `yinian stats --export` 导出CSV

### 10.3 预警系统
- [ ] 预算设置 `yinian budget set 100`
- [ ] 80% 预警提醒
- [ ] 超预算阻止调用
- [ ] 邮件/推送通知（可选）

### 10.4 报告生成
- [ ] 月度报告 Markdown 格式
- [ ] 成本分析图表
- [ ] 模型使用分布

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

#### Day 4：智能路由
- [ ] 问题分类器
- [ ] 路由规则
- [ ] 回退机制

#### Day 5-7：CLI + 输出
- [ ] Click CLI 框架
- [ ] 核心命令实现
- [ ] 流式输出
- [ ] 管道/文件支持
- [ ] 基础测试

### Week 2：缓存 + 统计

#### Day 8-9：本地缓存
- [ ] SQLite 数据库
- [ ] 缓存策略
- [ ] 缓存统计

#### Day 10-11：对话管理
- [ ] Session 管理
- [ ] 对话历史
- [ ] 上下文管理

#### Day 12-14：用量统计
- [ ] 数据记录
- [ ] 统计命令
- [ ] 预警系统

### Week 3-4：P2 功能

- [ ] 更多模型接入
- [ ] Prompt 模板
- [ ] 插件系统
- [ ] Docker 打包
- [ ] 文档完善
- [ ] GitHub Release

---

## 🐛 Bug 追踪

| Bug ID | 描述 | 状态 | 修复版本 |
|--------|------|------|----------|
| - | - | - | - |

---

## 📝 更新日志

### v0.1.0 (2026-03-30)
- ✅ 项目初始化
- 📋 进度文档创建
- ✅ Day 1 完成：目录结构 + pyproject.toml
- ✅ Day 2 完成：配置系统 + 3 个模型预配置
- ✅ Day 3 完成：模型接入（BaseModel + DeepSeek/Kimi/Qwen 适配器 + 工厂）

---

*最后更新：2026-03-30 22:01*
*使用 [x] 标记完成，[ ] 标记未完成*
