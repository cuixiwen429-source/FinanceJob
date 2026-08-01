"""简历结构化解析器

从 Markdown/PDF 简历中提取结构化信息。
目前支持 Markdown 格式（用户简历已可导出为 MD）。
"""

import re
from typing import Optional


def parse_markdown_resume(md_text: str) -> dict:
    """解析 Markdown 简历为结构化 dict"""
    sections = {
        "education": [],
        "internships": [],
        "projects": [],
        "skills": [],
        "certificates": [],
        "languages": [],
        "other": [],
    }

    current_section = "other"
    lines = md_text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 检测 section 标题
        section_lower = line.lower().lstrip("# ").strip()
        if any(kw in section_lower for kw in ["教育", "education", "学历"]):
            current_section = "education"
            continue
        elif any(kw in section_lower for kw in ["实习", "intern", "工作", "work", "经历"]):
            current_section = "internships"
            continue
        elif any(kw in section_lower for kw in ["项目", "project", "科研", "研究"]):
            current_section = "projects"
            continue
        elif any(kw in section_lower for kw in ["技能", "skill", "技术"]):
            current_section = "skills"
            continue
        elif any(kw in section_lower for kw in ["证书", "certif", "资格"]):
            current_section = "certificates"
            continue
        elif any(kw in section_lower for kw in ["语言", "language"]):
            current_section = "languages"
            continue
        elif line.startswith("#"):
            continue

        sections[current_section].append(line)

    return sections


def extract_skills(resume_sections: dict) -> list[str]:
    """提取技能列表"""
    skills = []
    for line in resume_sections.get("skills", []):
        # 按逗号/分号/顿号分割
        parts = re.split(r'[,，;；、/]', line)
        for p in parts:
            p = p.strip().rstrip("等。，")
            if p and len(p) > 1:
                skills.append(p)
    return skills


def extract_keywords(resume_sections: dict) -> list[str]:
    """提取简历中的金融行业关键词"""
    all_text = " ".join(
        " ".join(v) for v in resume_sections.values()
    )
    keywords = []

    finance_keywords = [
        "DCF", "估值", "财务建模", "行研", "行业研究",
        "尽职调查", "IPO", "并购", "定增", "二级市场",
        "Python", "Wind", "同花顺", "iFinD", "Bloomberg",
        "CFA", "FRM", "CPA", "证券从业", "基金从业",
        "量化", "因子", "回测", "夏普比率", "VaR",
        "研报", "深度报告", "产业链", "新能源", "汽车",
    ]
    for kw in finance_keywords:
        if kw.lower() in all_text.lower():
            keywords.append(kw)

    return keywords


def get_resume_summary(resume_sections: dict) -> str:
    """生成简历摘要"""
    education = " | ".join(resume_sections.get("education", [])[:3])
    internships = " | ".join(resume_sections.get("internships", [])[:5])
    skills = " | ".join(resume_sections.get("skills", [])[:5])
    certs = " | ".join(resume_sections.get("certificates", [])[:3])

    return f"""教育: {education}
实习: {internships}
技能: {skills}
证书: {certs}"""
