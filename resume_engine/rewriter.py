"""AI 简历改写引擎

LangGraph-inspired 4-stage pipeline:
  Splitter → Architect → Critic (80分门槛) → Formatter → PDF

整合自 Auto-JobHunter 的 prompt 结构，适配金融场景。
"""

from shared.llm import get_llm
from resume_engine.parser import (
    parse_markdown_resume,
    extract_keywords,
    get_resume_summary,
)


def rewrite_resume(
    job_title: str,
    job_company: str,
    jd_text: str,
    resume_md: str,
    finance_direction: str = "行研",
) -> dict:
    """
    四阶段简历改写

    Args:
        job_title: 岗位名称
        job_company: 公司名称
        jd_text: 岗位描述
        resume_md: 用户原始简历（Markdown）
        finance_direction: 行研/投行/量化/PEVC

    Returns:
        {
            "tailored_md": "改写后的 Markdown 简历",
            "cover_letter": "求职信",
            "score": 85,  # Critic 评分
            "changes_summary": "修改摘要",
        }
    """
    llm = get_llm()
    resume_sections = parse_markdown_resume(resume_md)
    keywords = extract_keywords(resume_sections)
    resume_summary = get_resume_summary(resume_sections)

    # ── Stage 1: Splitter — 拆解 JD 能力要求 ──
    split_prompt = f"""作为金融招聘专家，拆解以下 JD 的关键能力要求。

岗位: {job_title} @ {job_company}
JD: {jd_text[:2500]}

输出 JSON:
{{
  "hard_skills": ["财务建模", "Python"],
  "soft_skills": ["沟通能力"],
  "experience_required": ["买方/卖方研究经验"],
  "education_required": "硕士及以上",
  "certificates_preferred": ["CFA", "证券从业"],
  "hidden_requirements": ["能承受高压"]  // JD未明说但隐含的要求
}}
"""
    stage1 = llm.chat_json([{"role": "user", "content": split_prompt}],
                           system="你是金融招聘专家。只输出 JSON。")

    # ── Stage 2: Architect — 构建简历改写策略 ──
    arch_prompt = f"""作为简历优化专家，为以下岗位设计简历改写策略。

JD 能力要求: {stage1}
候选人简历摘要: {resume_summary}
简历中已有关键词: {keywords}
金融方向: {finance_direction}

输出 JSON:
{{
  "strategy": "3-5句话的改写策略",
  "sections_to_enhance": ["实习经历", "项目经历"],
  "keywords_to_add": ["产业链研究", "估值建模"],
  "keywords_to_emphasize": ["DCF模型"],
  "sections_to_trim": [],
  "story_angles": ["用具体数字量化研究成果"]
}}
"""
    stage2 = llm.chat_json([{"role": "user", "content": arch_prompt}],
                           system="你是简历优化专家。只输出 JSON。")

    # ── Stage 3: Critic — 评分 + 改写 ──
    rewrite_prompt = f"""你是顶级金融猎头，为候选人改写简历。

目标岗位: {job_title} @ {job_company}
JD: {jd_text[:2000]}

原始简历:
{resume_md[:3000]}

改写策略: {stage2.get('strategy', '')}
需要强调的关键词: {stage2.get('keywords_to_emphasize', [])}
需要添加的关键词: {stage2.get('keywords_to_add', [])}
金融方向模板: {finance_direction}

规则:
1. 用 STAR 法则重写每条实习经历
2. 每条经历必须有可量化的成果
3. 突出与 JD 匹配的关键词
4. 保持简洁，1 页 A4 纸
5. 使用金融行业专业术语
6. 所有内容真实，不编造经历

输出 JSON:
{{
  "tailored_resume_md": "完整的改写后简历 Markdown",
  "cover_letter": "200-300字的中文求职信",
  "score": 85,
  "improvements": ["添加了估值模型经历量化", "突出了行业研究深度"],
  "match_highlights": ["教育背景完全对口", "有相关实习经历"]
}}
"""
    stage3 = llm.chat_json([{"role": "user", "content": rewrite_prompt}],
                           system="你是顶级金融猎头。只输出 JSON。")

    # ── Stage 4: Critic 评分 + 重写循环 ──
    score = stage3.get("score", 70)
    attempts = 0
    while score < 80 and attempts < 2:
        critique_prompt = f"""你上一份简历评分只有 {score} 分，需要达到 80 分。
请改进以下方面:
- 量化成果不够充分
- 关键词密度不足
- 与 JD 的匹配度可提升

按之前相同格式输出改进后的 JSON。
"""
        stage3 = llm.chat_json([
            {"role": "user", "content": rewrite_prompt},
            {"role": "assistant", "content": str(stage3)},
            {"role": "user", "content": critique_prompt},
        ], system="你是顶级金融猎头。只输出 JSON。")
        score = stage3.get("score", 80)
        attempts += 1

    return {
        "tailored_md": stage3.get("tailored_resume_md", resume_md),
        "cover_letter": stage3.get("cover_letter", ""),
        "score": score,
        "changes_summary": stage3.get("improvements", []),
        "match_highlights": stage3.get("match_highlights", []),
    }
