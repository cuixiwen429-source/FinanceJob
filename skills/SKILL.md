# FinanceJob — 金融求职全自动投递

## 使用方式

在 Claude Code 中输入以下命令：

- `/finance-job scan` — 全网爬取岗位（第三方平台 + 120家企业官网）
- `/finance-job score` — 科学评分 + 综合排序（四维评分 + 口碑采集）
- `/finance-job tailor` — 简历定制（仅高分岗位，AI 改写 + 生成 PDF）
- `/finance-job send` — 邮件投递（按综合评分降序，自动/草稿模式）
- `/finance-job status` — 查看看板进度
- `/finance-job full` — 一键全流程 (scan → score → tailor → send)

## 全流程命令

```bash
cd /Users/a1-6/FinanceJob && \
  python -m scraper.cron && \
  python -m scoring_engine.pipeline && \
  python -m resume_engine.pipeline && \
  python -m email_sender.sender
```

## 环境依赖

```bash
pip install playwright beautifulsoup4 lxml requests pyyaml pydantic httpx openai rich python-dotenv fonttools weasyprint
playwright install chromium
```

## 配置

1. 复制 `.env.example` 为 `.env`
2. 填入 DEEPSEEK_API_KEY（AI 评分/简历改写）
3. 填入 EMAIL_ADDRESS + EMAIL_AUTH_CODE（邮件投递）
4. 编辑 `config.yaml` 调整目标城市、金融方向、评分阈值
