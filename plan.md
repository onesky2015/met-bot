# Role
你是一个资深的 Python 后端工程师和 DevOps 专家。

# Task
请帮我构建一个基于 GitHub Actions 的“医疗情报自动收集与推送机器人”。
不需要我写代码，请直接为我生成项目中需要的所有文件。

# Tech Stack
- 语言: Python 3.9+
- 依赖库: `feedparser` (RSS解析), `requests` (API调用), `google-generativeai` (AI总结)
- 部署: GitHub Actions (定时运行)

# Project Structure
请生成以下文件结构：
1. `main.py`: 核心逻辑代码。
2. `requirements.txt`: 依赖库列表。
3. `.github/workflows/daily.yml`: GitHub Actions 配置文件。
4. `README.md`: 简单的使用说明。

# Detailed Requirements

## 1. main.py (核心逻辑)
请实现以下功能：
- **配置读取**: 从 `os.environ` 读取 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GEMINI_API_KEY`。
- **RSS 源**: 定义一个 `RSS_SOURCES` 列表。请放入两个占位符链接：
    - 一个 PubMed 的 RSS 链接 (注释写: 需替换为用户生成的PubMed链接)
    - 一个 ClinicalTrials 的 RSS 链接。
- **历史记录 (去重)**:
    - 脚本启动时读取 `history.json` (如果存在)。
    - 解析 RSS 时，比对文章的 ID 或 Link。如果 ID 已存在于 history，则跳过。
    - 收集完新文章后，将新 ID 加入 history。
    - **关键**: 脚本结束前，必须将更新后的 history 保存回 `history.json` 文件。为了防止文件无限变大，只保留最后 1000 条记录。
- **AI 总结**:
    - 如果有新文章，使用 `google.generativeai` 库调用 `gemini-1.5-flash` 模型。
    - 将新文章的标题、来源、摘要拼接发给 AI。
    - Prompt 要求：你是一个风湿免疫科专家，请将以下关于“儿童红斑狼疮”的最新文献整理成中文日报。分为【重磅】、【临床】、【基础】三类。每条内容包含中文标题、一句话通俗解读、和原文链接。
- **Telegram 推送**:
    - 将 AI 生成的文本通过 `requests` 发送到 Telegram API。
- **容错**: 如果 AI 请求失败或 RSS 解析失败，打印错误但不中断整个程序。

## 2. .github/workflows/daily.yml (自动化)
- 触发条件: `cron: '0 0 * * *'` (每天 UTC 00:00) 和 `workflow_dispatch` (手动触发)。
- 权限设置: 必须包含 `contents: write` 权限，因为我们需要提交 `history.json` 的变更。
- 步骤:
    - Checkout 代码。
    - 安装 Python 环境。
    - 安装依赖 (`pip install -r requirements.txt`)。
    - 运行脚本 (`python main.py`)，并注入 GitHub Secrets 到环境变量。
    - **Git Commit**: 如果 `history.json` 有变化，配置 git user 为 "GitHub Action"，并自动 commit 和 push 更改回仓库。

## 3. requirements.txt
- 包含 `feedparser`, `requests`, `google-generativeai`。

# Implementation Plan
请直接生成代码，每段代码标明文件名。确保代码逻辑健壮，能够处理网络异常。