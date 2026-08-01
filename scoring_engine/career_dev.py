"""维度4: 发展前景评分 CDS (0-100, 权重20%)"""

from shared.llm import get_llm
from scoring_engine.models import CareerDevScore


# 公司品牌分
COMPANY_TIER = {
    # 头部券商
    "中信证券": 35, "中金公司": 35, "华泰证券": 32, "国泰君安": 30,
    "中信建投": 30, "招商证券": 28, "广发证券": 28,
    # 外资投行
    "Goldman Sachs": 40, "Morgan Stanley": 40, "J.P. Morgan": 38,
    # 头部PE/VC
    "高瓴资本": 38, "红杉中国": 38, "腾讯": 35, "字节跳动": 32,
    "阿里巴巴": 30, "蚂蚁集团": 30,
    # 头部基金
    "易方达基金": 30, "华夏基金": 30, "南方基金": 28, "嘉实基金": 28,
    # 头部量化
    "幻方量化": 32, "九坤投资": 30,
    # 银行
    "招商银行": 28, "平安银行": 25, "微众银行": 25,
    # 精品投行
    "华兴资本": 28, "泰合资本": 25, "光源资本": 25,
    # 评级/数据
    "万得 Wind": 22, "东方财富": 25, "同花顺": 22,
}


def _rule_based_skill_score(job: dict) -> float:
    """基于 JD 关键词评估技能积累价值（无 LLM）"""
    jd = job.get("jd_raw", job.get("jd_clean", "")).lower()
    score = 60
    if any(w in jd for w in ["财务建模", "估值", "dcf", "财务模型"]):
        score += 10
    if any(w in jd for w in ["行业研究", "深度报告", "研报", "研究"]):
        score += 10
    if any(w in jd for w in ["python", "数据分析", "量化", "编程"]):
        score += 5
    if any(w in jd for w in ["尽职调查", "立项", "投决", "ic"]):
        score += 10
    return min(95, score)


def _rule_based_exit_score(job: dict) -> float:
    """基于岗位类型评估退出路径（无 LLM）"""
    company_type = job.get("company_type", "")
    title = job.get("title", "").lower()
    if "投行" in title or company_type in ("券商", "外资投行"):
        return 80
    if "行研" in title or "研究" in title:
        return 78
    if company_type in ("PE/VC", "公募基金", "量化私募"):
        return 75
    if "战投" in title or company_type == "互联网战投":
        return 72
    return 65


def score_career_dev(job: dict, use_llm: bool = True) -> CareerDevScore:
    """计算发展前景评分"""
    company = job.get("company", "")
    title = job.get("title", "")
    jd = job.get("jd_raw", job.get("jd_clean", ""))
    company_type = job.get("company_type", "")

    # 1. 晋升路径 (基于公司类型)
    if company_type in ("券商", "外资投行"):
        promotion = 75  # 分析师→高级分析师→首席 路径清晰
    elif company_type in ("公募基金", "PE/VC"):
        promotion = 70
    elif company_type in ("互联网战投", "量化私募"):
        promotion = 65
    elif company_type in ("银行", "保险"):
        promotion = 60
    else:
        promotion = 60

    # 2. 技能积累
    if use_llm:
        llm = get_llm()
        skill_prompt = f"""分析以下岗位的描述，评估该岗位能积累的可迁移技能价值（0-100分）。

岗位: {title}
JD: {jd[:1000]}

评分标准:
- 财务建模/估值能力 +25
- 行业研究/分析能力 +25
- 数据分析/Python +15
- 项目管理/沟通协调 +10
- 其他专业能力 +25（根据JD具体判断）

输出 JSON: {{"skill_score": 75, "key_skills": ["财务建模", "行业研究"]}}
"""
        try:
            result = llm.chat_json([{"role": "user", "content": skill_prompt}],
                                    system="你是金融职业发展评估专家。只输出 JSON。")
            skill_score = result.get("skill_score", 65)
        except Exception:
            skill_score = 65
    else:
        skill_score = _rule_based_skill_score(job)

    # 3. 退出选项
    if use_llm:
        exit_prompt = f"""基于以下岗位信息，推理该岗位未来可能的退出路径数量（转买方/转卖方/去企业/创业/其他）。

岗位: {title} @ {company} ({company_type})
JD: {jd[:1000]}

输出 JSON:
{{"exit_count": 4, "exit_paths": ["买方研究员", "上市公司战投", "PE投资经理", "基金经理"], "exit_score": 80}}
"""
        try:
            result = llm.chat_json([{"role": "user", "content": exit_prompt}],
                                    system="你是金融职业规划专家。只输出 JSON。")
            exit_score = result.get("exit_score", 60)
        except Exception:
            exit_score = 60
    else:
        exit_score = _rule_based_exit_score(job)

    # 4. 平台价值
    platform = COMPANY_TIER.get(company, 20)

    return CareerDevScore(
        promotion_path=promotion,
        skill_accumulation=skill_score,
        exit_options=exit_score,
        platform_value=platform + 50,  # 基准50 + 品牌分
    )
