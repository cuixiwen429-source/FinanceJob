"""维度1: 岗位匹配度 JMS (0-100, 权重40%)

5 个子维度：
  技能匹配 (30%): JD关键词 + 简历技能覆盖
  经验匹配 (25%): 行业/职能/项目经验
  学历匹配 (20%): 学历层次+专业+学校
  证书匹配 (15%): 硬性要求+加分项
  软技能匹配 (10%): 沟通/协作/领导力
"""

from shared.llm import get_llm
from scoring_engine.models import JobMatchScore


# ── 学历评分规则 ──

def score_education(jd_text: str) -> dict:
    """从 JD 中提取学历要求并评分"""
    jd_lower = jd_text.lower()

    level_score = 80  # 硕士默认
    if any(w in jd_lower for w in ["博士", "phd", "博士研究生"]):
        level_score = 50  # 不是博士
    if any(w in jd_lower for w in ["硕士", "master", "硕士研究生"]):
        level_score = 85  # 正好匹配
    if any(w in jd_lower for w in ["本科", "bachelor"]):
        level_score = 90  # 硕士高于要求

    # 专业相关度
    major_score = 70
    finance_majors = ["金融", "经济", "会计", "财务", "投资", "管理", "统计", "数学", "计算机"]
    for m in finance_majors:
        if m in jd_lower:
            major_score = 90
            break

    # 学校梯队
    school_score = 75  # 华东师大 985
    if any(w in jd_lower for w in ["985", "211", "双一流"]):
        school_score = 85

    return {
        "education_match": (level_score * 0.5 + major_score * 0.3 + school_score * 0.2)
    }


# ── 证书评分规则 ──

CERTIFICATE_SCORES = {
    "cfa": 15, "特许金融分析师": 15,
    "frm": 12, "金融风险管理师": 12,
    "cpa": 15, "注册会计师": 15,
    "证券从业": 8, "证券从业资格": 8,
    "基金从业": 8, "基金从业资格": 8,
    "保荐代表人": 20, "保代": 20,
    "司法考试": 12, "法律职业资格": 12,
    "acca": 10,
}

def score_certificates(jd_text: str) -> float:
    """评估证书匹配度"""
    jd_lower = jd_text.lower()
    required = []
    bonus = []

    for cert, score in CERTIFICATE_SCORES.items():
        if cert in jd_lower:
            if any(w in jd_lower for w in ["必须", "要求", "required", "优先"]):
                required.append(score)
            else:
                bonus.append(score)

    if not required and not bonus:
        return 70  # 无证书要求

    base = 60
    if required:
        base = 80  # 假设用户有基础从业资格
    base += sum(bonus) * 0.5
    return min(100, base)


def _rule_based_job_match(job: dict, resume_text: str) -> dict:
    """基于关键词的规则快速岗位匹配（无 LLM 调用）"""
    jd = job.get("jd_raw", job.get("jd_clean", "")).lower()
    resume = resume_text.lower()

    # 技能关键词
    skill_keywords = [
        "财务建模", "估值", "dcf", "行业研究", "行研", "研报", "深度报告",
        "python", "pandas", "wind", "同花顺", "ifind", "bloomberg",
        "excel", "ppt", "数据分析", "尽职调查", "ipo", "并购", "定增",
        "量化", "因子", "回测", "机器学习",
    ]
    matched = sum(1 for kw in skill_keywords if kw in jd and kw in resume)
    skill_match = 50 + min(50, matched * 3)

    # 经验匹配（实习、研究、项目等）
    exp_match = 60
    if any(w in jd for w in ["实习经历", "相关实习", "有.*实习", "经验优先"]):
        exp_match = 70 if any(w in resume for w in ["实习", "研究员", "分析"]) else 55

    # 学历匹配
    edu = score_education(jd)

    # 证书匹配
    cert = score_certificates(jd)

    # 软技能
    soft_match = 65
    if any(w in jd for w in ["沟通", "团队协作", "抗压", "细致", "责任心"]):
        soft_match = 70 if any(w in resume for w in ["沟通", "团队", "协作", "负责"]) else 60

    return {
        "skill_match": skill_match,
        "experience_match": exp_match,
        "softskill_match": soft_match,
        "education_match": edu.get("education_match", 75),
        "certificate_match": cert,
    }


def score_job_match(job: dict, resume_text: str, use_llm: bool = True) -> JobMatchScore:
    """计算岗位匹配度"""
    jd = job.get("jd_raw", job.get("jd_clean", ""))

    if not use_llm:
        result = _rule_based_job_match(job, resume_text)
        return JobMatchScore(
            skill_match=result.get("skill_match", 60),
            experience_match=result.get("experience_match", 60),
            education_match=result.get("education_match", 75),
            certificate_match=result.get("certificate_match", 70),
            softskill_match=result.get("softskill_match", 60),
        )

    # 1. 技能匹配 - LLM 评估
    llm = get_llm()
    skill_prompt = f"""你是一个金融求职匹配专家。请评估以下 JD 要求的技能与候选人简历之间的匹配度。

JD 岗位描述:
{jd[:2000]}

候选人简历:
{resume_text[:1500]}

输出 JSON 格式的评分 (0-100):
{{"skill_match": 85, "experience_match": 80, "softskill_match": 75, "reasoning": "简要理由"}}
"""
    try:
        result = llm.chat_json([{"role": "user", "content": skill_prompt}],
                                system="你是金融求职评分专家。只输出 JSON。")
    except Exception:
        result = {"skill_match": 60, "experience_match": 60, "softskill_match": 60}

    # 2. 学历匹配
    edu = score_education(jd)

    # 3. 证书匹配
    cert = score_certificates(jd)

    return JobMatchScore(
        skill_match=result.get("skill_match", 60),
        experience_match=result.get("experience_match", 60),
        education_match=edu.get("education_match", 75),
        certificate_match=cert,
        softskill_match=result.get("softskill_match", 60),
    )
