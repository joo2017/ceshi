---
name: kpop-data-scraper
description: 使用 AI 自动抓取 kpopofficial.com 的 K-Pop 回归日程，过滤已过期的活动，并生成 JSON 数据集和 Markdown 报告。
---

# K-Pop 数据抓取 Skill

本 Skill 全自动完成 K-Pop 回归日程的获取流程。脚本保存在 Skill 目录中，可以在任何项目目录下直接调用。

## 核心功能

1.  **自动发现**: 自动查找 kpopofficial.com 上的月度日程页面。
2.  **AI 智能过滤**: 使用 `gemini-3-flash-preview` 智能识别日期，过滤掉已过期的活动。
3.  **数据生成**: 在当前运行目录下生成 JSON 和 Markdown 报告。

## 如何使用 (Agent 指令)

当用户请求抓取 K-Pop 数据时，请直接执行位于本 Skill 目录下的 `kpop_skill_runner.py` 脚本。

**运行命令示例**：

```bash
python "kpop_skill_runner.py"
```

*(请确保在用户希望保存数据的工作目录中运行此命令，且 Python 环境已配置)*

## 依赖要求

- Python 3.x
- `requests`, `beautifulsoup4`, `python-dotenv`, `google-generativeai`, `openai`
- 环境变量 `GEMINI_API_KEY` (或 `OPENAI_API_KEY`)
