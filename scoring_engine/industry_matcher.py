"""维度2: 行业匹配度 IMS (0-100, 权重25%)"""

from scoring_engine.industry_benchmark import get_industry_benchmark, get_industry_for_company_type
from scoring_engine.models import IndustryMatchScore


def score_industry_match(job: dict) -> IndustryMatchScore:
    """计算行业匹配度"""
    company_type = job.get("company_type", "")
    industry = job.get("industry", "")

    # 查找基准分
    if not industry:
        industry = get_industry_for_company_type(company_type)
    benchmark = get_industry_benchmark(industry)

    return IndustryMatchScore(
        growth=benchmark.get("growth", 70),
        stability=benchmark.get("stability", 65),
        barrier=benchmark.get("barrier", 60),
        personal_fit=benchmark.get("personal_fit", 70),
    )
