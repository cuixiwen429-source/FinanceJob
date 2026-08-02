"""★ 个人化评分管线 v3

赛道感知 + 公司分层 + 用户画像注入 + 四档决策分桶

核心改进：
1. 先分类赛道，再按赛道独立评分
2. 每个岗位先判断准入门槛（学历/经验/年级）
3. 公司 tier 纳入评分权重
4. 用户画像注入所有 AI 分析
5. 四档决策替代 83.5% 强烈推荐的虚假区分

用法:
    python -m scoring_engine.pipeline          # 评分所有新岗位
    python -m scoring_engine.pipeline --limit 100
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from shared.db import FinanceJobDB
from shared.config import UserConfig
from shared.llm import get_llm
from shared.user_profile import get_profile, UserProfile

from shared.track_classifier import classify_track, get_track_info
from shared.company_tier import match_company_tier, batch_assign_tiers, TierResult

from scoring_engine.models import (
    PersonalizedScore,
    CompositeScore,
    JobMatchScore,
    IndustryMatchScore,
    SalaryScore,
    CareerDevScore,
    Adjustment,
)
from scoring_engine.job_matcher import score_job_match
from scoring_engine.industry_matcher import score_industry_match
from scoring_engine.salary_analyzer import score_salary
from scoring_engine.career_dev import score_career_dev


# ── 赛道权重表 ──

TRACK_WEIGHTS = {
    "ecm_dcm":      {"track_fit": 95, "tier_factor": 1.2, "note": "对口赛道，高度推荐"},
    "ibd":          {"track_fit": 88, "tier_factor": 1.1, "note": "高度相关"},
    "research":     {"track_fit": 82, "tier_factor": 1.0, "note": "理工背景有优势"},
    "fa_boutique":  {"track_fit": 75, "tier_factor": 0.9, "note": "门槛适中，适合积累"},
    "pe_vc":        {"track_fit": 70, "tier_factor": 1.0, "note": "需强金融基础"},
    "asset_mgmt":   {"track_fit": 65, "tier_factor": 1.0, "note": "可尝试"},
    "ficc":         {"track_fit": 55, "tier_factor": 0.9, "note": "非核心赛道"},
    "sales_trading": {"track_fit": 45, "tier_factor": 0.8, "note": "非优势赛道"},
    "middle_back":  {"track_fit": 30, "tier_factor": 0.5, "note": "与前台经验不匹配"},
    "quant":        {"track_fit": 35, "tier_factor": 0.6, "note": "量化背景劣势明显"},
}


def score_threshold_match(job: dict, llm=None) -> float:
    """评估准入门槛匹配度

    检查 JD 中的学历/年级/经验要求是否与用户背景匹配
    """
    jd = f"{job.get('jd_raw','')} {job.get('title','')} {job.get('jd_clean','')}".lower()

    # 硬门槛检测
    score = 75.0  # 默认

    # 博士/3+年经验 → 大概率不满足
    if any(w in jd for w in ["博士", "phd", "3年以上", "5年以上", "资深"]):
        score -= 30

    # 硕士/在读研究生 → 我们满足
    if any(w in jd for w in ["硕士", "master", "研究生"]):
        score += 10

    # 本科及以上 → 满足
    if any(w in jd for w in ["本科", "bachelor"]):
        score += 5

    # 要求金融/经济相关专业 → 弱匹配（水利→金融跨专业）
    if any(w in jd for w in ["金融专业", "经济专业", "财务专业", "会计专业"]):
        score -= 10

    # 要求理工科背景 → 优势
    if any(w in jd for w in ["理工", "工程", "数学", "统计", "计算机"]):
        score += 15

    # 实习经验要求
    if any(w in jd for w in ["有实习经验优先", "相关实习经验", "投行实习"]):
        score += 5  # 我们有实习

    # 年级要求：大二/大三 → 我们是研一
    if any(w in jd for w in ["大一", "大二", "大三"]) and "研" not in jd:
        score -= 5

    return max(0, min(100, score))


def score_tier_match(company_tier: str, track_id: str) -> float:
    """评估公司层级匹配度

    对于 S-Tier 公司：用户竞争力不足 → 得分较低（不是不推荐，是实事求是）
    对于 B-Tier 公司：用户竞争力匹配 → 得分较高
    对于 C-Tier 及以下：如果赛道热门，bar 较低，得分中等
    """
    tier_scores = {
        "S": 55,   # 顶级：竞争激烈，用户背景偏弱
        "A": 72,   # 一线：值得冲刺
        "B": 85,   # 二线：主力目标
        "C": 68,   # 其他：可考虑，但注意区分度
        "U": 65,   # 未知：保守评分
    }
    return tier_scores.get(company_tier, 65)


def score_edge_leverage(job: dict, track_id: str, llm=None) -> float:
    """评估背景优势发挥程度

    岗位是否能发挥用户"理工+金融"的复合优势？
    - 行研赛道的能源/制造业/基建/TMT 组：高
    - ECM/DCM：中等（实习经验可迁移）
    - 量化：低（工程≠CS/数学纯量化）
    """
    jd = (f"{job.get('title','')} {job.get('industry','')} "
          f"{job.get('jd_raw','')} {job.get('jd_clean','')}").lower()

    score = 60.0  # 默认

    # 赛道基础分
    track_edge_base = {
        "research": 15,    # 行研最能发挥理工优势
        "ecm_dcm": 10,     # ECM实习直接相关
        "ibd": 8,
        "pe_vc": 5,
        "asset_mgmt": 3,
        "ficc": 2,
        "fa_boutique": 2,
        "sales_trading": 0,
        "quant": -5,
        "middle_back": -10,
    }
    score += track_edge_base.get(track_id, 0)

    # JD 中的行业关键词匹配（理工优势行业）
    edge_industries = [
        "能源", "新能源", "碳中和", "电力",
        "制造", "工业", "机械", "汽车", "军工",
        "基建", "建筑", "水利", "工程",
        "材料", "化工", "TMT", "硬科技", "半导体", "电子",
    ]
    matched = [w for w in edge_industries if w in jd]
    score += min(20, len(matched) * 4)

    # 资本市场相关加分
    if any(w in jd for w in ["ECM", "DCM", "定增", "基石", "承销", "资本市场", "再融资"]):
        score += 10

    return max(0, min(100, score))


def score_growth_value(job: dict, company_tier: str, track_id: str, llm=None) -> float:
    """评估成长价值

    该岗位对用户"理工→金融"职业转换的长期贡献
    """
    score = 65.0  # 默认

    # 公司 tier 贡献
    tier_growth = {"S": 25, "A": 18, "B": 12, "C": 5, "U": 10}
    score += tier_growth.get(company_tier, 10)

    # 赛道成长性
    track_growth = {
        "ibd": 18, "ecm_dcm": 16, "research": 15,
        "pe_vc": 14, "ficc": 12, "quant": 12,
        "asset_mgmt": 10, "fa_boutique": 8,
        "sales_trading": 6, "middle_back": 3,
    }
    score += track_growth.get(track_id, 8)

    # 有留用机会加分
    jd = f"{job.get('jd_raw','')} {job.get('title','')}".lower()
    if any(w in jd for w in ["留用", "转正", "return offer", "可转正"]):
        score += 8

    return max(0, min(100, score))


def generate_ai_reasoning(job: dict, score: PersonalizedScore,
                           track_label: str, company_tier_label: str,
                           use_llm: bool = True) -> str:
    """用 LLM 生成个性化决策建议"""
    if not use_llm:
        return f"{score.decision_emoji} {score.decision} | {score.reasoning}"

    profile = get_profile()

    prompt = f"""你是一个金融求职顾问。请基于用户画像分析以下岗位，输出 2-3 句话的投递建议。

{profile.to_ai_context()}

---
岗位信息：
- 岗位：{job.get('title','')}
- 公司：{job.get('company','')}
- 赛道：{track_label}
- 公司层级：{company_tier_label}
- 地点：{job.get('location','')}
- 薪资：{job.get('salary_raw','')}
- JD摘要：{job.get('jd_raw','')[:800]}

评分情况：
- 赛道契合度：{score.track_fit:.0f}/100
- 准入门槛：{score.threshold_match:.0f}/100
- 机构层级匹配：{score.tier_match:.0f}/100
- 优势发挥：{score.edge_leverage:.0f}/100
- 成长价值：{score.growth_value:.0f}/100
- 最终决策：{score.decision}

请用以下格式返回（纯文本，50-80字，不要序号）：
"建议投递。理由。注意事项。"
"""
    try:
        llm = get_llm()
        result = llm.chat(
            [{"role": "user", "content": prompt}],
            system="你是金融求职顾问。回复简洁，50-80字，不要序号和标题。",
            temperature=0.3,
            max_tokens=150,
        )
        return result.strip()
    except Exception:
        return f"{score.decision_emoji} {score.decision} — {track_label}赛道，{company_tier_label}机构"


# ═══════════════════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════════════════

class ScoringPipelineV3:
    """赛道感知 + 个人化评分"""

    def __init__(self, db: FinanceJobDB, config: UserConfig = None):
        self.db = db
        self.config = config or UserConfig.load()
        self.profile = get_profile()

    def score_all(self, limit: int = 200, use_llm: bool = True,
                  dry_run: bool = False) -> list[dict]:
        """对所有未评分的岗位进行 v3 评分"""

        # Step 0: 迁移数据库（添加新字段）
        self.db.migrate_v3_columns()

        # Step 1: 获取未评分岗位
        jobs = self.db.get_new_jobs(limit=limit)
        # 也处理已有旧评分但无 track 的岗位
        if len(jobs) < limit:
            rows = self.db.conn.execute(
                "SELECT * FROM jobs WHERE (track = '' OR company_tier = '') LIMIT ?",
                (limit - len(jobs),)
            ).fetchall()
            jobs.extend([dict(r) for r in rows])

        if not jobs:
            print("[v3] 暂无岗位需要评分")
            return []

        print(f"[v3] 开始对 {len(jobs)} 个岗位进行个人化评分...")

        # Step 2: 批量分类赛道
        for job in jobs:
            track_result = classify_track(
                job.get("title", ""),
                job.get("industry", ""),
                job.get("company_type", ""),
            )
            job["track"] = track_result["primary_track"]
            job["tracks"] = track_result["tracks"]
            job["track_label"] = track_result["primary_name"]

        # Step 3: 批量标注公司 tier
        for job in jobs:
            tier_result = match_company_tier(
                job.get("company", ""),
                job.get("company_type", ""),
                use_llm=False,  # 先规则匹配，未知的后面 LLM
            )
            job["company_tier"] = tier_result.tier
            job["company_tier_label"] = tier_result.tier_label
            job["company_tier_note"] = tier_result.note

        # Step 3b: LLM 判断未标注的公司（批量一次请求）
        unknown_jobs = [j for j in jobs if j["company_tier"] in ("U", "")]
        if unknown_jobs and use_llm:
            print(f"[v3] {len(unknown_jobs)} 个公司未匹配，调用 LLM 判断...")
            try:
                llm = get_llm()
                # 批量请求（减少 API 调用）
                for j in unknown_jobs:
                    tier_result = match_company_tier(
                        j.get("company", ""),
                        j.get("company_type", ""),
                        use_llm=True,
                        llm_client=llm,
                    )
                    j["company_tier"] = tier_result.tier
                    j["company_tier_label"] = tier_result.tier_label
                    j["company_tier_note"] = tier_result.note
            except Exception as e:
                print(f"[v3] LLM tier 判断失败: {e}")

        # Step 4: 逐岗评分
        results = []
        for i, job in enumerate(jobs):
            try:
                track_id = job.get("track", "research")
                company_tier = job.get("company_tier", "U")
                track_label = job.get("track_label", "未知")
                company_tier_label = job.get("company_tier_label", "未知")

                print(f"  [{i+1}/{len(jobs)}] {job.get('company','?')} — {job.get('title','?')}")
                print(f"    赛道={track_label} | 层级={company_tier_label}")

                # 五维评分
                track_weight = TRACK_WEIGHTS.get(track_id, TRACK_WEIGHTS["research"])
                track_fit = track_weight["track_fit"]
                threshold_match = score_threshold_match(job)
                tier_match = score_tier_match(company_tier, track_id)
                edge_leverage = score_edge_leverage(job, track_id)
                growth_value = score_growth_value(job, company_tier, track_id)

                personalized = PersonalizedScore(
                    track_fit=track_fit,
                    threshold_match=threshold_match,
                    tier_match=tier_match,
                    edge_leverage=edge_leverage,
                    growth_value=growth_value,
                )

                # AI reasoning
                ai_reasoning = generate_ai_reasoning(
                    job, personalized, track_label, company_tier_label, use_llm
                )

                decision = personalized.decision
                total = personalized.total

                print(f"    适配={track_fit:.0f} 门槛={threshold_match:.0f} "
                      f"层级={tier_match:.0f} 优势={edge_leverage:.0f} 成长={growth_value:.0f}")
                print(f"    → {personalized.decision_emoji} {decision} ({total:.0f})")

                # 运行旧评分维度（兼容+参考）
                resume = self.profile.to_ai_context()
                jms = score_job_match(job, resume, use_llm=False)
                ims = score_industry_match(job)
                ss = score_salary(job)
                cds = score_career_dev(job, use_llm=False)

                if not dry_run:
                    score_data = {
                        "composite_score": total,
                        "rank": 0, "percentile": 0,
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
                            "growth": ims.growth, "stability": ims.stability,
                            "barrier": ims.barrier, "personal_fit": ims.personal_fit,
                        },
                        "salary_score": ss.total,
                        "salary_detail": {
                            "absolute": ss.absolute, "growth_potential": ss.growth_potential,
                            "bonus_structure": ss.bonus_structure, "benefits": ss.benefits,
                        },
                        "career_dev_score": cds.total,
                        "career_dev_detail": {
                            "promotion_path": cds.promotion_path,
                            "skill_accumulation": cds.skill_accumulation,
                            "exit_options": cds.exit_options,
                            "platform_value": cds.platform_value,
                        },
                        "adjustments": [
                            {"type": f"赛道:{track_id}", "value": 0, "reason": track_weight["note"]},
                            {"type": f"tier:{company_tier}", "value": 0, "reason": f"{company_tier_label}机构"},
                        ],
                        "reasoning": personalized.reasoning,
                        "track": track_id,
                        "tracks": job.get("tracks", [track_id]),
                        "track_label": track_label,
                        "company_tier": company_tier,
                        "company_tier_label": company_tier_label,
                        "company_tier_note": job.get("company_tier_note", ""),
                        "ai_reasoning": ai_reasoning,
                    }
                    self.db.update_scores(job["id"], score_data)

                results.append({
                    "job_id": job.get("id"),
                    "company": job.get("company"),
                    "title": job.get("title"),
                    "track": track_label,
                    "tier": company_tier_label,
                    "decision": decision,
                    "total": total,
                })

            except Exception as e:
                print(f"    ⚠ 评分异常: {e}")
                continue

        # Step 5: 统一排序
        if not dry_run and results:
            self._rank_all()

        # 统计
        priority = sum(1 for r in results if r["decision"] == "优先投")
        worth = sum(1 for r in results if r["decision"] == "值得投")
        consider = sum(1 for r in results if r["decision"] == "可考虑")
        skip = sum(1 for r in results if r["decision"] == "不推荐")

        print(f"\n[v3] 完成! {len(results)} 个岗位已评分")
        print(f"  🟢 优先投: {priority} | 🔵 值得投: {worth} | 🟡 可考虑: {consider} | ⚪ 不推荐: {skip}")

        return results

    def _rank_all(self):
        """对所有 scored 岗位按复合评分排序"""
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
    parser = argparse.ArgumentParser(description="FinanceJob v3 个人化评分引擎")
    parser.add_argument("--limit", type=int, default=200, help="最多评分岗位数")
    parser.add_argument("--dry", action="store_true", help="试运行，不写入数据库")
    parser.add_argument("--no-llm", action="store_true", help="不使用 LLM（规则评分）")
    args = parser.parse_args()

    db = FinanceJobDB()
    pipeline = ScoringPipelineV3(db)
    results = pipeline.score_all(
        limit=args.limit,
        use_llm=not args.no_llm,
        dry_run=args.dry,
    )

    if not args.dry:
        stats = db.get_stats()
        print(f"\n数据库状态: 总={stats['total']}, 赛道分布={stats.get('track_distribution',{})}")
        print(f"Tier分布: S={stats.get('tier_S',0)} A={stats.get('tier_A',0)} "
              f"B={stats.get('tier_B',0)} C={stats.get('tier_C',0)} U={stats.get('tier_unknown',0)}")

    db.close()


if __name__ == "__main__":
    main()
