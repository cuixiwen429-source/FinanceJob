"""★ 科学综合评分管线

爬取完成后 → 口碑采集 → 四维评分 → 修正因子 → 综合排序 → 决策推荐

用法:
    python -m scoring_engine.pipeline          # 评分所有新岗位
    python -m scoring_engine.pipeline --dry    # 试运行，不写入 DB
"""

import argparse
from datetime import datetime
from pathlib import Path

from shared.db import FinanceJobDB
from shared.config import UserConfig
from scoring_engine.models import CompositeScore
from scoring_engine.job_matcher import score_job_match
from scoring_engine.industry_matcher import score_industry_match
from scoring_engine.salary_analyzer import score_salary
from scoring_engine.career_dev import score_career_dev
from scoring_engine.adjustments import calculate_adjustments
from scoring_engine.reputation_fetcher import ReputationFetcher


# ── 用户简历文本 ──

def load_resume_text() -> str:
    """从 data/resume_base.md 读取简历，不存在则使用默认简历"""
    resume_path = Path(__file__).resolve().parent.parent / "data" / "resume_base.md"
    if resume_path.exists():
        return resume_path.read_text(encoding="utf-8")
    return """# 崔曦文

## 教育背景
- 华东师范大学 金融硕士 2028届
- 黑龙江大学 水利水电工程 学士

## 实习经历
- 证券研究所 行研实习生: 撰写行业深度报告、构建DCF估值模型、跟踪新能源/汽车产业链

## 技能
- 财务建模、估值分析、Python/Pandas、Wind/同花顺/iFinD
- CFA Level 1 Candidate
"""


RESUME_TEXT = load_resume_text()


class ScoringPipeline:
    """四维科学评分主流程"""

    def __init__(self, db: FinanceJobDB, config: UserConfig = None):
        self.db = db
        self.config = config or UserConfig.load()
        self.reputation = ReputationFetcher(db)

    def score_all_new(self, dry_run: bool = False, limit: int = 200,
                      use_llm: bool = True, skip_reputation: bool = False) -> list[dict]:
        """对所有新岗位评分, 返回评分结果列表

        Args:
            dry_run: 试运行，不写入数据库
            limit: 最多评分岗位数
            use_llm: 是否使用 LLM 增强评分（False 使用规则快速评分，成本低速度快）
            skip_reputation: 是否跳过口碑采集（避免外部网站反爬失败阻塞流程）
        """
        jobs = self.db.get_new_jobs(limit=limit)
        if not jobs:
            print("[评分] 暂无新岗位需要评分")
            return []

        mode_str = "LLM增强" if use_llm else "规则快速"
        print(f"[评分] 开始对 {len(jobs)} 个新岗位进行四维评分（模式: {mode_str}）...")
        if skip_reputation:
            print("[评分] 已跳过口碑采集")
        results = []

        for i, job in enumerate(jobs):
            try:
                print(f"  [{i+1}/{len(jobs)}] {job.get('company','?')} — {job.get('title','?')}")

                # ★ Step 0: 全网口碑采集（可跳过）
                company = job.get("company", "")
                rep_data = None
                if company and not skip_reputation:
                    print(f"    口碑采集: {company}...")
                    try:
                        rep_data = self.reputation.fetch_company(company)
                    except Exception as e:
                        print(f"    口碑采集失败，使用空口碑: {e}")

                # Step 1: 岗位匹配度
                jms = score_job_match(job, RESUME_TEXT, use_llm=use_llm)

                # Step 2: 行业匹配度
                ims = score_industry_match(job)

                # Step 3: 薪资评分
                ss = score_salary(job)

                # Step 4: 发展前景
                cds = score_career_dev(job, use_llm=use_llm)

                # Step 5: 修正因子
                adjustments = calculate_adjustments(job, rep_data)

                # Step 6: 综合评分
                composite = CompositeScore(
                    job_id=job.get("id", ""),
                    job_match=jms,
                    industry_match=ims,
                    salary=ss,
                    career_dev=cds,
                    adjustments=adjustments,
                )

                total = composite.total
                decision = composite.decision

                print(f"    JMS={jms.total:.1f} IMS={ims.total:.1f} SS={ss.total:.1f} CDS={cds.total:.1f}")
                print(f"    综合={total:.1f} → {decision}")

                if not dry_run:
                    # 写入 DB
                    score_data = {
                        "composite_score": total,
                        "rank": 0,  # 稍后统一排序
                        "percentile": 0,
                        "decision": decision,
                        "job_match_score": jms.total,
                        "job_match_detail": {
                            "skill_match": jms.skill_match,
                            "experience_match": jms.experience_match,
                            "education_match": jms.education_match,
                            "certificate_match": jms.certificate_match,
                            "softskill_match": jms.softskill_match,
                        },
                        "industry_match_score": ims.total,
                        "industry_match_detail": {
                            "growth": ims.growth,
                            "stability": ims.stability,
                            "barrier": ims.barrier,
                            "personal_fit": ims.personal_fit,
                        },
                        "salary_score": ss.total,
                        "salary_detail": {
                            "absolute": ss.absolute,
                            "growth_potential": ss.growth_potential,
                            "bonus_structure": ss.bonus_structure,
                            "benefits": ss.benefits,
                        },
                        "career_dev_score": cds.total,
                        "career_dev_detail": {
                            "promotion_path": cds.promotion_path,
                            "skill_accumulation": cds.skill_accumulation,
                            "exit_options": cds.exit_options,
                            "platform_value": cds.platform_value,
                        },
                        "adjustments": [
                            {"type": a.type, "value": a.value, "reason": a.reason}
                            for a in adjustments
                        ],
                        "reputation": rep_data,
                        "reasoning": (
                            f"JMS({jms.total:.0f}): 技能{jms.skill_match:.0f}/经验{jms.experience_match:.0f}/"
                            f"学历{jms.education_match:.0f} | IMS({ims.total:.0f}): 成长{ims.growth:.0f}/"
                            f"适配{ims.personal_fit:.0f} | SS({ss.total:.0f}) | CDS({cds.total:.0f})"
                            f" | 修正: {[f'{a.type}:{a.value:+}' for a in adjustments]}"
                        ),
                    }
                    self.db.update_scores(job["id"], score_data)

                results.append({
                    "job_id": job.get("id"),
                    "company": company,
                    "title": job.get("title"),
                    "total": total,
                    "decision": decision,
                })

            except Exception as e:
                print(f"    ⚠ 评分异常: {e}")
                continue

        # Step 7: 统一排序 + 计算百分位
        if not dry_run and results:
            self._rank_all()

        print(f"\n[评分] 完成! {len(results)} 个岗位已评分")

        # 打印统计
        strong = sum(1 for r in results if r["decision"] == "强烈推荐")
        rec = sum(1 for r in results if r["decision"] == "推荐投递")
        con = sum(1 for r in results if r["decision"] == "可投递")
        skip = sum(1 for r in results if r["decision"] == "建议跳过")
        print(f"  强烈推荐: {strong} | 推荐: {rec} | 可投递: {con} | 跳过: {skip}")

        return results

    def _rank_all(self):
        """对所有 scored 岗位统一排序，计算百分位"""
        import sqlite3
        rows = self.db.conn.execute(
            "SELECT id, composite_score FROM jobs WHERE status='scored' ORDER BY composite_score DESC"
        ).fetchall()
        total = len(rows)
        if total == 0:
            return
        for rank, row in enumerate(rows, 1):
            percentile = round((total - rank) / total * 100, 1)
            self.db.conn.execute(
                "UPDATE jobs SET rank = ?, percentile = ? WHERE id = ?",
                (rank, percentile, row["id"])
            )
        self.db.conn.commit()


def main():
    parser = argparse.ArgumentParser(description="FinanceJob 评分引擎")
    parser.add_argument("--dry", action="store_true", help="试运行，不写入数据库")
    parser.add_argument("--limit", type=int, default=200, help="最多评分岗位数（默认200）")
    parser.add_argument("--no-llm", action="store_true", help="使用规则快速评分，不调用LLM")
    parser.add_argument("--skip-reputation", action="store_true", help="跳过口碑采集")
    args = parser.parse_args()

    db = FinanceJobDB()
    pipeline = ScoringPipeline(db)
    pipeline.score_all_new(
        dry_run=args.dry,
        limit=args.limit,
        use_llm=not args.no_llm,
        skip_reputation=args.skip_reputation,
    )

    stats = db.get_stats()
    print(f"\n数据库状态: {stats}")
    db.close()


if __name__ == "__main__":
    main()
