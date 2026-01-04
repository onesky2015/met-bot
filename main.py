# filename: main.py
"""
医疗情报自动收集与推送机器人
功能: 从RSS源获取医学文献，使用AI总结，推送到Telegram
"""

import os
import json
import logging
import time
from datetime import datetime
from typing import Optional

import feedparser
import requests
import google.generativeai as genai

# ============================================================
# 配置区域
# ============================================================

# 从环境变量读取敏感配置
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# RSS 源列表
RSS_SOURCES = [
    {
        "name": "PubMed - Pediatric SLE",
        # 搜索关键词：Systemic Lupus Erythematosus AND Child
        "url": "https://pubmed.ncbi.nlm.nih.gov/rss/search/14_xQ7JEOWXDuopaPahtu8vYOV9ttMUxoq8IeKOLBpA7Zak9UG/?limit=15&utm_campaign=pubmed-2&fc=20260103215413",
    },
    {
        "name": "ClinicalTrials - Pediatric Lupus",
        # 搜索关键词：SLE (Condition) + Child (Term)
        # 移除了容易报错的时间过滤器，依靠 robots 自身的 history 去重
        "url": "https://clinicaltrials.gov/api/rss?cond=Systemic+Lupus+Erythematosus&term=Child",
    },
]

# 历史记录文件路径
HISTORY_FILE = "history.json"

# 最大历史记录数量（防止文件无限增大）
MAX_HISTORY_SIZE = 1000

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ============================================================
# 历史记录管理
# ============================================================

def load_history() -> set:
    """加载历史记录文件"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(f"已加载 {len(data)} 条历史记录")
                return set(data)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"读取历史记录失败: {e}，将使用空记录")
            return set()
    else:
        logger.info("历史记录文件不存在，创建新记录")
        return set()

def save_history(history: set) -> None:
    """保存历史记录到文件"""
    history_list = list(history)
    if len(history_list) > MAX_HISTORY_SIZE:
        history_list = history_list[-MAX_HISTORY_SIZE:]
    
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history_list, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存 {len(history_list)} 条历史记录")
    except IOError as e:
        logger.error(f"保存历史记录失败: {e}")

# ============================================================
# RSS 解析 (带 Session 和 Headers 伪装)
# ============================================================

def fetch_rss_articles(sources: list) -> list:
    """从RSS源获取文章列表，包含反爬虫策略"""
    articles = []
    session = requests.Session()

    for source in sources:
        source_name = source.get("name", "Unknown")
        url = source.get("url", "")

        if not url: continue
        logger.info(f"正在获取: {source_name}")

        # 针对不同来源定制 Headers
        if "pubmed" in url.lower():
            headers = {
                'User-Agent': 'MedicalIntelligenceBot/1.0 (Research Purpose)',
                'Referer': 'https://pubmed.ncbi.nlm.nih.gov/',
                'Accept': '*/*'
            }
        else:
            # ClinicalTrials 等其他网站模拟浏览器
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }

        try:
            # 延时避免封禁
            time.sleep(2)
            response = session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            current_count = 0
            for entry in feed.entries:
                article_id = entry.get("id") or entry.get("link") or entry.get("title", "")
                if not article_id: continue

                articles.append({
                    "id": article_id,
                    "title": entry.get("title", "无标题"),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", entry.get("description", "无摘要")),
                    "source": source_name,
                    "published": entry.get("published", ""),
                })
                current_count += 1
            
            logger.info(f"从 '{source_name}' 获取了 {current_count} 篇文章")

        except Exception as e:
            logger.error(f"获取 '{source_name}' 失败: {e}")

    session.close()
    return articles

def filter_new_articles(articles: list, history: set) -> list:
    """过滤新文章"""
    new_articles = [a for a in articles if a.get("id") and a.get("id") not in history]
    logger.info(f"发现 {len(new_articles)} 篇新文章")
    return new_articles

# ============================================================
# AI 总结 (自动寻找最佳模型)
# ============================================================

def generate_ai_summary(articles: list) -> Optional[str]:
    """使用 Gemini AI 生成总结，自动适配可用模型"""
    if not GEMINI_API_KEY or not articles: return None

    # 构建 Prompt
    articles_text = ""
    for i, article in enumerate(articles, 1):
        articles_text += f"\n--- 文章 {i} ---\n标题: {article['title']}\n摘要: {article['summary'][:500]}...\n链接: {article['link']}\n"

    prompt = f"""你是一个风湿免疫科专家，请将以下关于"儿童红斑狼疮"的最新文献整理成中文日报。
日期: {datetime.now().strftime('%Y-%m-%d')}
要求：
1. 分为【重磅】、【临床】、【基础】三类。
2. 每个条目包含：中文标题、一句话通俗解读、原文链接。
3. 保持专业且易读。

待处理文献：
{articles_text}
"""

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # ------------------------------------------------------
        # 智能模型选择逻辑
        # ------------------------------------------------------
        logger.info("正在自动选择最佳 Gemini 模型...")
        available_models = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
        except Exception as e:
            logger.warning(f"无法列出模型，尝试使用默认值: {e}")

        # 默认回退模型
        model_name = "models/gemini-pro" 
        
        # 优先选择策略：Flash > Pro > 其他
        if available_models:
            # 你的环境里有 gemini-2.5-flash，优先找它
            flash_models = [m for m in available_models if 'flash' in m]
            pro_models = [m for m in available_models if 'pro' in m]
            
            if flash_models:
                model_name = flash_models[0] # 选最新的Flash
            elif pro_models:
                model_name = pro_models[0]
        
        logger.info(f"已选择模型: {model_name}")
        model = genai.GenerativeModel(model_name)
        
        response = model.generate_content(prompt)
        if response and response.text:
            logger.info("AI总结生成成功")
            return response.text
            
    except Exception as e:
        logger.error(f"AI总结失败: {e}")
        return None

    return None

# ============================================================
# Telegram 推送 (防报错增强版)
# ============================================================

def send_telegram_message(text: str) -> bool:
    """发送消息到 Telegram，失败时自动降级为纯文本"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # 切分长消息
    max_length = 4000
    messages = []
    while len(text) > 0:
        if len(text) > max_length:
            # 寻找最近的换行符切分
            split_idx = text.rfind('\n', 0, max_length)
            if split_idx == -1: split_idx = max_length
            messages.append(text[:split_idx])
            text = text[split_idx:]
        else:
            messages.append(text)
            text = ""

    all_success = True
    for i, msg in enumerate(messages, 1):
        # 方案 A: 尝试 Markdown 发送 (好看)
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                logger.info(f"消息 {i}/{len(messages)} (Markdown) 发送成功")
                continue # 成功，跳过下方降级逻辑
            else:
                logger.warning(f"消息 {i} Markdown 发送失败 ({resp.text})，尝试纯文本重发...")
        except Exception as e:
            logger.warning(f"消息 {i} 网络异常: {e}")

        # 方案 B: 降级为纯文本发送 (保底)
        payload["parse_mode"] = None # 取消格式化
        try:
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                logger.info(f"消息 {i}/{len(messages)} (纯文本) 发送成功")
            else:
                logger.error(f"消息 {i} 彻底失败: {resp.text}")
                all_success = False
        except Exception as e:
            logger.error(f"消息 {i} 纯文本重发异常: {e}")
            all_success = False

    return all_success

# ============================================================
# 主流程
# ============================================================

def main():
    logger.info("=" * 50)
    logger.info("医疗情报收集机器人启动 (v2.0 Final)")
    logger.info("=" * 50)

    # 1. 加载历史
    history = load_history()

    # 2. 获取 RSS
    all_articles = fetch_rss_articles(RSS_SOURCES)
    
    # 3. 过滤新文章
    new_articles = filter_new_articles(all_articles, history)

    if not new_articles:
        logger.info("没有新文章，任务结束")
        return

    # 4. AI 总结
    summary = generate_ai_summary(new_articles)

    # 5. 推送消息
    if summary:
        send_telegram_message(summary)
    else:
        # AI 失败时的备选方案
        fallback = f"新文献通知 (AI生成失败):\n" + "\n".join([f"• {a['title']}\n{a['link']}" for a in new_articles[:5]])
        send_telegram_message(fallback)

    # 6. 保存历史 (标记为已读)
    for a in new_articles:
        history.add(a["id"])
    save_history(history)

    logger.info("任务完成")

if __name__ == "__main__":
    main()