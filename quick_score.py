#!/usr/bin/env python3
"""快速评分 — 使用本地基准表 + 启发式算法，不依赖 LLM API Key"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared.db import FinanceJobDB
from datetime import datetime

db = FinanceJobDB()

# 对每个 new 岗位分配现实评分
jobs = db.get_new_jobs(limit=50)

HARDCODED_SCORES = {
    "行研实习生-新能源组": {"jms":88,"ims":85,"ss":78,"cds":82,"reputation":6,"reasoning":"中信证券头部券商，新能源组行业成长性强，技能匹配度高"},
    "投行部实习生": {"jms":80,"ims":73,"ss":82,"cds":85,"reputation":5,"reasoning":"中金投行平台价值极高，但岗位竞争激烈"},
    "战略投资分析实习生": {"jms":82,"ims":84,"ss":85,"cds":84,"reputation":7,"reasoning":"腾讯战投平台价值极高，行业前景好，深圳本地"},
    "远程行研实习生-消费组": {"jms":78,"ims":75,"ss":62,"cds":70,"reputation":3,"reasoning":"远程实习灵活，华泰消费组口碑好，但薪资偏低"},
    "投资实习生-科技方向": {"jms":70,"ims":80,"ss":72,"cds":78,"reputation":5,"reasoning":"高瓴顶级PE，硬科技方向成长性高，经验匹配偏低"},
    "量化研究实习生": {"jms":60,"ims":71,"ss":92,"cds":75,"reputation":4,"reasoning":"幻方头部量化，薪资极高，但用户量化经验偏少"},
    "行业研究员实习生": {"jms":85,"ims":82,"ss":75,"cds":78,"reputation":5,"reasoning":"易方达头部公募，广州地点一般，研究方向对口"},
    "投资实习生-Seed Stage": {"jms":72,"ims":78,"ss":70,"cds":82,"reputation":6,"reasoning":"红杉顶级VC，早期投资经验价值极高"},
    "金融工程实习生": {"jms":65,"ims":68,"ss":60,"cds":62,"reputation":2,"reasoning":"东方财富数据服务商，平台价值一般"},
    "总行金融市场部实习生": {"jms":55,"ims":68,"ss":72,"cds":65,"reputation":3,"reasoning":"招商银行金融市场部，稳定但行研匹配度不高"},
}

for job in jobs:
    title = job.get("title","")
    company = job.get("company","")
    key = title
    scores = HARDCODED_SCORES.get(key, {"jms":60,"ims":65,"ss":60,"cds":60,"reputation":0,"reasoning":"默认评分"})

    # 修正因子
    adjustments = []
    location = job.get("location","")
    is_remote = job.get("is_remote", False)

    if is_remote:
        adjustments.append({"type":"远程加分","value":3,"reason":"在校期间远程优先"})
    elif "深圳" in location:
        adjustments.append({"type":"城市匹配","value":3,"reason":"深圳本地(寒暑假)"})
    elif "上海" in location:
        adjustments.append({"type":"城市匹配","value":1,"reason":"上海(在校)"})

    if company in ("腾讯","平安集团","中信证券"):
        adjustments.append({"type":"内推可用","value":3,"reason":"人脉网络有该公司员工"})

    if scores["reputation"] >= 6:
        adjustments.append({"type":"口碑优秀","value":2,"reason":"全网口碑正面"})

    total = (scores["jms"]*0.40 + scores["ims"]*0.25 + scores["ss"]*0.15 + scores["cds"]*0.20
             + sum(a["value"] for a in adjustments))

    if total >= 75: decision = "强烈推荐"
    elif total >= 60: decision = "推荐投递"
    elif total >= 45: decision = "可投递"
    else: decision = "建议跳过"

    db.update_scores(job["id"], {
        "composite_score": round(total,1),
        "decision": decision,
        "job_match_score": scores["jms"],
        "job_match_detail":{"skill_match":scores["jms"],"experience_match":scores["jms"]-5,"education_match":90,"certificate_match":75,"softskill_match":80},
        "industry_match_score": scores["ims"],
        "industry_match_detail":{"growth":scores["ims"],"stability":70,"barrier":75,"personal_fit":scores["ims"]-5},
        "salary_score": scores["ss"],
        "salary_detail":{"absolute":scores["ss"],"growth_potential":75,"bonus_structure":70,"benefits":70},
        "career_dev_score": scores["cds"],
        "career_dev_detail":{"promotion_path":75,"skill_accumulation":scores["cds"],"exit_options":70,"platform_value":scores["cds"]},
        "adjustments": adjustments,
        "reasoning": scores["reasoning"],
    })

# 统一排序
rows = db.conn.execute("SELECT id, composite_score FROM jobs WHERE status='scored' ORDER BY composite_score DESC").fetchall()
for rank, row in enumerate(rows, 1):
    db.conn.execute("UPDATE jobs SET rank=?, percentile=? WHERE id=?",
                    (rank, round((len(rows)-rank)/len(rows)*100,1), row["id"]))
db.conn.commit()

print(f"✅ 已评分 {len(jobs)} 个岗位")
for r in db.get_scored_jobs(limit=5):
    print(f"  {r['rank']}. [{r['decision']}] {r['company']} — {r['title']} ({r['composite_score']:.0f}分)")
db.close()
