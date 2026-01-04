# 🏥 医疗情报自动收集与推送机器人

一个基于 GitHub Actions 的自动化机器人，用于收集儿童红斑狼疮相关的最新医学文献，通过 AI 生成中文摘要并推送到 Telegram。

## ✨ 功能特性

- 📰 **RSS 订阅**: 自动从 PubMed、ClinicalTrials 等源获取最新文献
- 🤖 **AI 总结**: 使用 Google Gemini AI 将英文文献整理成中文日报
- 📱 **Telegram 推送**: 自动发送每日情报到指定 Telegram 群组/频道
- 🔄 **智能去重**: 自动记录已推送文章，避免重复推送
- ⏰ **定时运行**: 每天自动执行，无需人工干预

## 🚀 快速开始

### 1. Fork 本仓库

点击右上角 "Fork" 按钮，将仓库复制到你的 GitHub 账号下。

### 2. 配置 GitHub Secrets

在你的仓库中，进入 **Settings → Secrets and variables → Actions**，添加以下 Secrets：

| Secret 名称 | 说明 | 获取方式 |
|------------|------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram 机器人 Token | 通过 [@BotFather](https://t.me/BotFather) 创建机器人获取 |
| `TELEGRAM_CHAT_ID` | 目标群组/频道 ID | 将机器人加入群组，通过 API 获取 chat_id |
| `GEMINI_API_KEY` | Google Gemini API 密钥 | 在 [Google AI Studio](https://aistudio.google.com/app/apikey) 创建 |

### 3. 自定义 RSS 源

编辑 `main.py` 中的 `RSS_SOURCES` 列表，替换为你需要的 RSS 链接：

```python
RSS_SOURCES = [
    {
        "name": "PubMed - Pediatric SLE",
        "url": "https://pubmed.ncbi.nlm.nih.gov/rss/search/YOUR_SEARCH_TERM/...",
    },
    # 添加更多源...
]
```

**如何获取 PubMed RSS 链接：**
1. 访问 [PubMed](https://pubmed.ncbi.nlm.nih.gov/)
2. 输入搜索词（如 `pediatric systemic lupus erythematosus`）
3. 点击搜索结果页的 "Create RSS" 按钮
4. 复制生成的 RSS 链接

### 4. 手动测试

进入仓库的 **Actions** 页面，选择 "医疗情报日报" workflow，点击 "Run workflow" 手动触发测试。

## 📁 项目结构

```
met-bot/
├── main.py                      # 核心逻辑代码
├── requirements.txt             # Python 依赖
├── history.json                 # 已推送文章记录（自动生成）
├── README.md                    # 说明文档
└── .github/
    └── workflows/
        └── daily.yml            # GitHub Actions 配置
```

## ⚙️ 工作流程

```
┌─────────────────┐
│  定时触发/手动  │
│  (每天 UTC 0:00) │
└────────┬────────┘
         ▼
┌─────────────────┐
│  获取 RSS 文章   │
└────────┬────────┘
         ▼
┌─────────────────┐
│  对比历史记录    │
│  过滤已推送文章  │
└────────┬────────┘
         ▼
┌─────────────────┐
│  调用 Gemini AI  │
│  生成中文日报    │
└────────┬────────┘
         ▼
┌─────────────────┐
│  发送到 Telegram │
└────────┬────────┘
         ▼
┌─────────────────┐
│  更新历史记录    │
│  提交到仓库      │
└─────────────────┘
```

## 📝 输出示例

```
📅 2026年01月04日 儿童红斑狼疮研究日报

【重磅】
📌 新型生物制剂在儿童系统性红斑狼疮中的应用
💡 一种新药能有效控制狼疮活动，副作用比传统药物更少
🔗 https://pubmed.ncbi.nlm.nih.gov/xxxxx

【临床】
📌 儿童狼疮性肾炎的长期预后研究
💡 早期规范治疗的孩子，10年后肾功能保持良好的比例超过80%
🔗 https://pubmed.ncbi.nlm.nih.gov/xxxxx

【基础】
📌 系统性红斑狼疮中 B 细胞亚群的作用机制
💡 发现一种特殊的免疫细胞与狼疮发病密切相关，可能成为新的治疗靶点
🔗 https://pubmed.ncbi.nlm.nih.gov/xxxxx
```

## 🔧 常见问题

### Q: Telegram 收不到消息？

1. 确认机器人已加入目标群组/频道
2. 确认 `TELEGRAM_CHAT_ID` 正确（群组ID通常是负数）
3. 检查 Actions 日志是否有报错

### Q: 如何获取 Telegram Chat ID？

1. 将机器人加入群组
2. 在群组中发送任意消息
3. 访问 `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. 在返回的 JSON 中找到 `chat.id`

### Q: 如何修改运行时间？

编辑 `.github/workflows/daily.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 0 * * *'  # UTC 时间，北京时间 +8 小时
```

### Q: 历史记录文件太大怎么办？

脚本会自动保留最近 1000 条记录，旧记录会被自动清理。

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！


