"""简历引擎主流程

对已评分的高分岗位，生成定制化简历+求职信+PDF。

用法:
    python -m resume_engine.pipeline
    python -m resume_engine.pipeline --job-id xxx
"""

import argparse
from pathlib import Path

from shared.db import FinanceJobDB
from shared.config import UserConfig
from resume_engine.rewriter import rewrite_resume
from resume_engine.pdf_gen import generate_pdf


# 基础简历路径
BASE_RESUME_PATH = Path(__file__).resolve().parent.parent / "data" / "resume_base.md"

# 默认基础简历（如果文件不存在）
DEFAULT_RESUME_MD = """# 崔曦文

## 教育背景
- **华东师范大学** | 金融硕士 | 2026.09 - 2028.06 (预计)
  - 研究方向: 证券投资、行业研究
- **黑龙江大学** | 水利水电工程 学士 | 2022.09 - 2026.06

## 实习经历
- **证券研究所 | 行研实习生** | 2025.07 - 2025.09
  - 独立完成新能源汽车行业深度研究报告，构建DCF估值模型
  - 跟踪覆盖5家上市公司，撰写周报及点评报告
  - 参与定增项目研究，支持团队投资决策

## 项目经历
- **多因子选股模型** | 量化研究项目
  - 基于Python构建多因子选股模型，回测年化收益跑赢基准
  - 使用Wind/同花顺API获取数据，构建因子库

## 技能
- 财务建模: DCF、可比公司法、先例交易法
- 数据工具: Python/Pandas, Excel/VBA, SQL
- 金融终端: Wind, 同花顺, iFinD
- 语言: 英语 CET-6, 普通话

## 证书
- CFA Level 1 Candidate
- 证券从业资格
"""


def get_base_resume() -> str:
    """获取基础简历文本"""
    if BASE_RESUME_PATH.exists():
        return BASE_RESUME_PATH.read_text(encoding="utf-8")
    return DEFAULT_RESUME_MD


def detect_finance_direction(title: str, jd: str, config: UserConfig) -> str:
    """根据岗位标题和 JD 判断金融方向，回退到用户配置首选"""
    text = f"{title} {jd}".lower()
    direction_map = [
        ("量化", "量化"),
        ("投行", "投行"),
        ("ibd", "投行"),
        ("行研", "行研"),
        ("行业研究", "行研"),
        ("证券研究", "行研"),
        ("投资", "PE/VC"),
        ("pe", "PE/VC"),
        ("vc", "PE/VC"),
        ("战投", "战投"),
        ("战略投资", "战投"),
    ]
    for keyword, direction in direction_map:
        if keyword in text:
            return direction
    directions = config.finance_directions or ["行研"]
    first = directions[0]
    # Strip detail suffixes like "行研/证券研究"
    return first.split("/")[0].strip()


def run_resume_pipeline(job_id: str = None, limit: int = 10):
    """对高分岗位生成定制简历"""
    db = FinanceJobDB()

    if job_id:
        # 单个岗位
        rows = db.conn.execute(
            "SELECT * FROM jobs WHERE id = ?", (job_id,)
        ).fetchall()
        jobs = [dict(r) for r in rows]
    else:
        # 获取所有"强烈推荐"+"推荐投递"且尚未生成简历的岗位
        rows = db.conn.execute(
            """SELECT * FROM jobs
               WHERE decision IN ('强烈推荐', '推荐投递')
               AND (tailored_resume_path = '' OR tailored_resume_path IS NULL)
               ORDER BY composite_score DESC
               LIMIT ?""",
            (limit,)
        ).fetchall()
        jobs = [dict(r) for r in rows]

    if not jobs:
        print("[简历] 暂无需要生成简历的岗位")
        db.close()
        return

    print(f"[简历] 为 {len(jobs)} 个岗位生成定制简历...")
    base_resume = get_base_resume()
    config = UserConfig.load()
    count = 0

    for job in jobs:
        try:
            title = job.get("title", "")
            company = job.get("company", "")
            jd = job.get("jd_raw", job.get("jd_clean", ""))
            jid = job.get("id", "")

            if not jd:
                print(f"  ⚠ {company} - {title}: 无 JD 文本，跳过")
                continue

            print(f"  → {company} — {title}")

            # AI 改写
            finance_direction = detect_finance_direction(title, jd, config)
            result = rewrite_resume(
                job_title=title,
                job_company=company,
                jd_text=jd,
                resume_md=base_resume,
                finance_direction=finance_direction,
            )

            tailored_md = result.get("tailored_md", "")
            cover_letter = result.get("cover_letter", "")
            score = result.get("score", 0)

            print(f"    改写评分: {score}/100")
            if result.get("changes_summary"):
                for change in result["changes_summary"][:3]:
                    print(f"      · {change}")

            # 生成 PDF
            pdf_path = generate_pdf(
                tailored_md,
                output_path="",
                name="崔曦文",
                job_title=title.replace("/", "-"),
                company=company,
            )

            # 更新 DB
            db.conn.execute(
                """UPDATE jobs SET
                    tailored_resume_path = ?, cover_letter = ?,
                    status = 'resume_ready', updated_at = datetime('now')
                   WHERE id = ?""",
                (pdf_path, cover_letter, jid),
            )
            db.conn.commit()
            count += 1

        except Exception as e:
            print(f"  ⚠ {job.get('company','?')} 简历生成失败: {e}")
            continue

    print(f"\n[简历] 完成! 生成 {count} 份定制简历")
    db.close()


def main():
    parser = argparse.ArgumentParser(description="FinanceJob 简历引擎")
    parser.add_argument("--job-id", type=str, help="指定岗位 ID")
    parser.add_argument("--limit", type=int, default=10, help="最大处理数量")
    args = parser.parse_args()

    run_resume_pipeline(job_id=args.job_id, limit=args.limit)


if __name__ == "__main__":
    main()
