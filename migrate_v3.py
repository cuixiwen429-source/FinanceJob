#!/usr/bin/env python3
"""FinanceJob v3 — 对现有 3853 条数据进行赛道分类 + 公司分层 + 重评分

用法:
    python migrate_v3.py            # 全量运行（会修改数据库！）
    python migrate_v3.py --dry      # 试运行，只统计不写入
    python migrate_v3.py --limit 50 # 只处理前50条

步骤:
    1. 数据库迁移：添加 track/company_tier 等新字段
    2. 赛道分类：对每条岗位分类到 10 条赛道
    3. 公司分层：对每家公司标注 S/A/B/C/U
    4. 对 U 级公司调用 LLM 判断
    5. 重评分：用 v3 五维评分系统重新打分
    6. 统计输出
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from shared.db import FinanceJobDB
from shared.track_classifier import classify_track
from shared.company_tier import match_company_tier
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="FinanceJob v3 数据迁移")
    parser.add_argument("--dry", action="store_true", help="试运行，不写入")
    parser.add_argument("--limit", type=int, default=0, help="限制处理条数，0=全部")
    parser.add_argument("--skip-llm", action="store_true", help="跳过 LLM tier 判断")
    args = parser.parse_args()

    db = FinanceJobDB()

    # Step 1: 迁移数据库
    print("=" * 60)
    print("FinanceJob v3 数据迁移")
    print("=" * 60)

    if not args.dry:
        print("\n[1/4] 数据库迁移...")
        db.migrate_v3_columns()
    else:
        print("\n[1/4] [DRY] 数据库迁移（跳过）")

    # Step 2: 获取所有岗位
    limit_clause = f" LIMIT {args.limit}" if args.limit else ""
    rows = db.conn.execute(
        f"SELECT id, title, company, company_type, industry FROM jobs WHERE 1=1{limit_clause}"
    ).fetchall()
    total = len(rows)
    print(f"\n[2/4] 处理 {total} 个岗位的赛道分类 + 公司分层...")

    track_counts = {}
    tier_counts = {"S": 0, "A": 0, "B": 0, "C": 0, "U": 0}
    unknown_companies = []

    for i, row in enumerate(rows):
        job = dict(row)
        title = job.get("title", "")
        company = job.get("company", "")
        company_type = job.get("company_type", "")
        industry = job.get("industry", "")

        # 赛道分类
        track_result = classify_track(title, industry, company_type)
        track_id = track_result["primary_track"]
        track_label = track_result["primary_name"]
        tracks = track_result["tracks"]
        track_counts[track_label] = track_counts.get(track_label, 0) + 1

        # 公司分层
        tier_result = match_company_tier(company, company_type)
        tier = tier_result.tier
        tier_label = tier_result.tier_label
        tier_note = tier_result.note
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

        if tier == "U":
            unknown_companies.append((company, company_type))

        if i < 5 or i % 500 == 0:
            print(f"  [{i+1}/{total}] {company[:20]} -> {track_label} ({tier})")

        if not args.dry:
            import json
            db.conn.execute("""
                UPDATE jobs SET
                    track = ?, tracks = ?, track_label = ?,
                    company_tier = ?, company_tier_label = ?, company_tier_note = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                track_id,
                json.dumps(tracks, ensure_ascii=False),
                track_label,
                tier, tier_label, tier_note,
                datetime.now().isoformat(),
                job["id"],
            ))

    if not args.dry:
        db.conn.commit()

    # Step 3: LLM 判断未标注公司
    unique_unknown = list(set(unknown_companies))
    if unique_unknown and not args.skip_llm:
        print(f"\n[3/4] {len(unique_unknown)} 个未匹配公司，调用 LLM 判断...")
        try:
            from shared.llm import get_llm
            llm = get_llm()

            for company, company_type in unique_unknown:
                if args.dry:
                    print(f"  [DRY] {company}")
                    continue
                try:
                    tier_result = match_company_tier(
                        company, company_type, use_llm=True, llm_client=llm
                    )
                    print(f"  {company} -> {tier_result.tier} ({tier_result.note})")
                    db.conn.execute("""
                        UPDATE jobs SET
                            company_tier = ?, company_tier_label = ?, company_tier_note = ?,
                            updated_at = ?
                        WHERE company = ?
                    """, (
                        tier_result.tier, tier_result.tier_label, tier_result.note,
                        datetime.now().isoformat(), company,
                    ))
                except Exception as e:
                    print(f"  {company} -> ERROR: {e}")
            db.conn.commit()
        except Exception as e:
            print(f"  LLM 调用失败: {e}")
    else:
        print(f"\n[3/4] 跳过 LLM 判断（{len(unique_unknown)} 个未匹配公司）")

    # Step 4: 统计
    print("\n" + "=" * 60)
    print("[4/4] 迁移完成统计")
    print("=" * 60)

    print("\n📊 赛道分布:")
    max_count = max(track_counts.values()) if track_counts else 1
    for name, count in sorted(track_counts.items(), key=lambda x: -x[1]):
        bar = "█" * (count * 30 // max_count)
        print(f"  {name:16s} {count:4d} {bar}")

    print("\n🏢 公司层级分布:")
    tier_names = {"S": "顶级", "A": "一线", "B": "二线", "C": "其他", "U": "未知"}
    for t in ["S", "A", "B", "C", "U"]:
        count = tier_counts.get(t, 0)
        pct = count/total*100 if total > 0 else 0
        print(f"  {t}-{tier_names[t]:4s} {count:4d} ({pct:.1f}%)")

    if not args.dry:
        updated_tier = db.conn.execute(
            "SELECT company_tier, COUNT(*) as c FROM jobs WHERE company_tier != '' AND company_tier != 'U' GROUP BY company_tier"
        ).fetchall()
        tier_after = {r["company_tier"]: r["c"] for r in updated_tier}
        print(f"\n  标注后: S={tier_after.get('S',0)} A={tier_after.get('A',0)} "
              f"B={tier_after.get('B',0)} C={tier_after.get('C',0)} "
              f"U={db.conn.execute('SELECT COUNT(*) FROM jobs WHERE company_tier=\"U\" OR company_tier=\"\"').fetchone()[0]}")

    print(f"\n⚠️ 下一步: 运行评分引擎")
    print(f"   python -m scoring_engine.pipeline --limit 200")
    print(f"   或运行 score_all.py")

    db.close()


if __name__ == "__main__":
    main()
