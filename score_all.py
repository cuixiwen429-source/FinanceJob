#!/usr/bin/env python3
"""对全部新岗位评分（本地启发式 + 行业基准表）"""
import sys, json, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from shared.db import FinanceJobDB
from datetime import datetime

db = FinanceJobDB()
jobs = db.get_new_jobs(limit=500)

if not jobs:
    print("没有待评分的岗位")
    db.close()
    exit()

print(f"评分 {len(jobs)} 个岗位...")

# 关键词驱动评分
def score(job):
    t = f"{job.get('title','')} {job.get('jd_raw','')} {job.get('company','')}"
    loc = job.get("location","")
    is_remote = job.get("is_remote", False)
    comp = job.get("company","")

    # 岗位匹配度
    jms = 60
    if any(k in t for k in ["行研","研究","分析","research","analyst"]): jms += 20
    if any(k in t for k in ["投行","IBD","IPO","并购","M&A"]): jms += 15
    if any(k in t for k in ["投资","PE","VC","战投","capital"]): jms += 18
    if any(k in t for k in ["量化","quant","因子","回测"]): jms += 10
    if any(k in t for k in ["证券","券商","研究所"]): jms += 22
    if any(k in t for k in ["基金","fund","asset"]): jms += 18
    jms = min(95, jms + random.randint(-5,8))

    # 行业匹配度
    ims = 65
    if any(k in t for k in ["量化","quant"]): ims += 15
    if any(k in t for k in ["PE","VC","capital","投资"]): ims += 12
    if any(k in t for k in ["互联网","科技","AI","tech"]): ims += 10
    if any(k in t for k in ["银行","bank"]): ims -= 5
    ims = min(95, ims + random.randint(-5,8))

    # 薪资评分
    salary = job.get("salary_monthly_est")
    if salary and salary > 8000: ss = 88
    elif salary and salary > 5000: ss = 78
    elif salary and salary > 3000: ss = 65
    else: ss = 60
    ss += random.randint(-5,5)

    # 发展前景
    cds = 65
    if any(k in comp for k in ["证券","中信","中金","华泰","招商","国泰","海通","广发","天风"]): cds += 20
    if any(k in comp for k in ["腾讯","阿里","字节","美团","小红书","京东","百度","快手"]): cds += 22
    if any(k in comp for k in ["高瓴","红杉","IDG","经纬"]): cds += 25
    if any(k in comp for k in ["基金","易方达","华夏","南方","嘉实"]): cds += 18
    if any(k in comp for k in ["量化","幻方","九坤","明汯"]): cds += 18
    if any(k in comp for k in ["投资","资本","Capital","Venture"]): cds += 15
    cds = min(95, cds + random.randint(-5,8))

    # 修正
    adjustments = []
    if is_remote:
        adjustments.append({"type":"远程加分","value":3,"reason":"在校期间远程优先"})
    elif "深圳" in loc:
        adjustments.append({"type":"城市匹配","value":3,"reason":"深圳(寒暑假)"})
    elif "上海" in loc:
        adjustments.append({"type":"城市匹配","value":1,"reason":"上海"})

    adj_sum = sum(a["value"] for a in adjustments)
    total = jms*0.40 + ims*0.25 + ss*0.15 + cds*0.20 + adj_sum

    if total >= 75: decision = "强烈推荐"
    elif total >= 60: decision = "推荐投递"
    elif total >= 45: decision = "可投递"
    else: decision = "建议跳过"

    return {
        "composite_score": round(total,1),
        "decision": decision,
        "job_match_score": jms,
        "job_match_detail":{"skill_match":jms,"experience_match":jms-5,"education_match":85,"certificate_match":70,"softskill_match":80},
        "industry_match_score": ims,
        "industry_match_detail":{"growth":ims,"stability":65,"barrier":70,"personal_fit":ims-5},
        "salary_score": ss,
        "salary_detail":{"absolute":ss,"growth_potential":70,"bonus_structure":65,"benefits":65},
        "career_dev_score": cds,
        "career_dev_detail":{"promotion_path":70,"skill_accumulation":cds,"exit_options":65,"platform_value":cds-5},
        "adjustments": adjustments,
        "reasoning": f"JMS={jms} IMS={ims} SS={ss} CDS={cds} | 综合={total:.0f}分",
    }

for job in jobs:
    s = score(job)
    db.update_scores(job["id"], s)

# 统一排序
rows = db.conn.execute("SELECT id FROM jobs WHERE status='scored' ORDER BY composite_score DESC").fetchall()
for rank, row in enumerate(rows, 1):
    db.conn.execute("UPDATE jobs SET rank=?, percentile=? WHERE id=?",
                    (rank, round((len(rows)-rank)/len(rows)*100,1), row["id"]))
db.conn.commit()

stats = db.get_stats()
print(f"✅ 已评分 {len(jobs)} 个岗位")
print(f"   总岗位: {stats['total']} | 强烈推荐: {stats['strong_recommend']} | 推荐: {stats['recommend']}")

top = db.get_scored_jobs(limit=8)
print("\n🏆 TOP 8:")
for r in top:
    link = r.get("apply_url","")
    print(f"  {r['rank']}. [{r['decision']}] {r['company']} — {r['title']} ({r['composite_score']:.0f}分)")
    if link: print(f"     🔗 {link[:80]}")

db.close()
