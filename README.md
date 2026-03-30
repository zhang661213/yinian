# 一念 (Yinian) CLI

> 最省钱的 AI 助手 CLI — 自动选模型、智能省 Token、管道友好

## 安装

```bash
pip install -e .
```

## 快速开始

```bash
# 基础问答
yinian "如何用 Python 写快排？"

# 多模型对比
yinian "帮我写一个快排" --compare

# 指定模型
yinian "翻译：Hello World" --model kimi

# 管道输入
cat error.log | yinian "分析这个报错"
```

## 功能

- 🧠 智能路由 - 自动选择最合适的模型
- 💰 省 Token - 智能缓存，避免重复调用
- 📊 用量统计 - 清楚知道每分钱花在哪
- 🔗 管道友好 - 天然支持 Linux/Unix 管道
- 🎨 优雅输出 - Markdown 渲染，代码高亮

## 支持模型

- DeepSeek
- Kimi (Moonshot)
- 通义千问
- (更多模型接入中...)

## 配置

首次使用需要配置 API Key：

```bash
yinian config set deepseek.key sk-xxxxx
yinian config set kimi.key sk-xxxxx
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/
```

## License

MIT
