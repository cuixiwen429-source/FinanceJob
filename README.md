# FinanceJob — 金融求职全自动投递系统

**崔曦文 · 华东师范大学金融硕士 · 2028届**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue)]()

## 架构

```
FinanceJob/
├── main.py               ← 一键入口
├── scraper/              岗位数据源 (腾讯文档 / 企业官网 / 第三方平台)
├── scoring_engine/       ★ 四维科学评分 (岗位/行业/薪资/发展 + 口碑)
├── resume_engine/        AI简历定制 (LangGraph 4-stage)
├── email_sender/         双通道邮件投递 (SMTP + .eml)
├── shared/               共享 (SQLite · LLM · 配置)
└── dashboard/            Next.js Web 看板
```

## 快速开始

```bash
cd C:/Users/ChainsXes/Desktop/FinanceJob

# 1. 安装依赖
pip install -r requirements.txt
playwright install chromium

# 2. 配置
cp .env.example .env
# 编辑 .env: 填入 DEEPSEEK_API_KEY, EMAIL_ADDRESS, EMAIL_AUTH_CODE
# 编辑 config.yaml: 调整目标城市/方向/简历路径

# 3. 导入腾讯文档实习 JD（已内置 4000+ 条）
python main.py import-tencent-docs

# 4. 规则快速评分（无需 LLM / 口碑采集）
python main.py score --score-no-llm --score-skip-reputation --score-limit 100

# 5. 查看高分岗位
python main.py status
```

## 命令

| 命令 | 功能 |
|------|------|
| `python main.py full` | 一键全流程 (scan→score→tailor→send) |
| `python main.py scan` | 全网爬取岗位 |
| `python main.py import-tencent-docs` | 从腾讯文档导入实习 JD |
| `python main.py score` | 四维科学评分 + 口碑采集 |
| `python main.py score --score-no-llm --score-skip-reputation --score-limit 100` | 规则快速评分前100条 |
| `python main.py tailor` | AI简历定制 |
| `python main.py send` | 邮件投递 |
| `python main.py status` | 查看进度 |
| `python launcher.py` | 启动 Web 看板 |

## 评分模式说明

- **默认模式**: 调用 DeepSeek 做岗位匹配与发展前景评估，并采集看准/知乎/牛客口碑。
- **快速模式** (`--score-no-llm`): 使用关键词规则评分，无需 API Key，速度极快，适合批量初筛。
- **口碑跳过** (`--score-skip-reputation`): 不访问外部招聘社区，避免反爬失败阻塞流程。

## 数据源

- `data/tencent_docs_jobs_raw.json`: 腾讯文档「金融-日常实习表」本地缓存（4135 条原始 JD）。
- 新增岗位可通过 `scraper/platforms/tencent_docs.py` 从腾讯文档 URL 实时拉取。

## 在线部署

### 一键部署到 Render（推荐）

项目已配置好 Dockerfile 与 `render.yaml`，点击下方按钮即可免费部署：

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/cuixiwen429-source/FinanceJob)

部署完成后：
- Render 会自动构建 Next.js 前端 + Python API 服务
- 首次启动会从 `data/tencent_docs_jobs_raw.json` 自动导入 4000+ 条 JD
- 通过 Render 给出的 `https://financejob-dashboard-xxx.onrender.com` 即可访问看板
- 免费实例会在 15 分钟无访问后休眠，首次打开可能需要 30 秒冷启动

### 本地启动 Web 看板

```bash
cd dashboard
npm install
npm run build      # 构建静态文件到 dashboard/dist
cd ..
python scripts/seed_and_serve.py
```

访问 http://localhost:5175。

## 注意事项

- 系统优先读取 `data/resume_base.md` 作为简历基础；不存在时使用内置默认简历。
- 邮件发送前请确认 `.env` 中邮箱授权码正确；未配置时可用 `python main.py send` 生成 `.eml` 草稿。
- Web 看板依赖 `dashboard/node_modules`，首次使用前需在 `dashboard/` 下运行 `npm install`。
- 仓库为公开仓库，个人简历信息（姓名、学校等）已随代码提交，如需保密请改为 Private Repo。
