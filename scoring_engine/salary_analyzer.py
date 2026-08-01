"""维度3: 薪资评分 SS (0-100, 权重15%)"""

from scoring_engine.models import SalaryScore


# 金融实习/校招岗位的薪资基准（月薪，深圳/上海）
SALARY_BENCHMARKS = {
    "行研实习生": {"p25": 2000, "p50": 4000, "p75": 6000},
    "投行实习生": {"p25": 3000, "p50": 5000, "p75": 8000},
    "量化实习生": {"p25": 4000, "p50": 8000, "p75": 15000},
    "PE/VC实习生": {"p25": 3000, "p50": 5000, "p75": 8000},
    "战投实习生": {"p25": 4000, "p50": 6000, "p75": 10000},
    "金融实习生": {"p25": 2000, "p50": 4000, "p75": 6000},
}


def _find_benchmark(title: str) -> dict[str, float]:
    """根据岗位标题匹配薪资基准"""
    for key, val in SALARY_BENCHMARKS.items():
        if key.replace("实习生", "") in title or key in title:
            return val
    return SALARY_BENCHMARKS["金融实习生"]


def score_salary(job: dict) -> SalaryScore:
    """计算薪资评分"""
    salary_est = job.get("salary_monthly_est")
    title = job.get("title", "")
    benchmark = _find_benchmark(title)

    # 1. 薪资绝对值评分 (vs P50)
    if salary_est and salary_est > 0:
        p50 = benchmark["p50"]
        p75 = benchmark["p75"]
        ratio = salary_est / p50 if p50 > 0 else 1.0
        if ratio >= p75 / p50:
            absolute = 90
        elif ratio >= 1.0:
            absolute = 75
        elif ratio >= 0.6:
            absolute = 60
        else:
            absolute = 40
    else:
        absolute = 60  # 无薪资标注，中性

    # 2. 薪资成长性（实习生→正式员工涨幅估计）
    company_type = job.get("company_type", "")
    if company_type in ("券商", "外资投行", "PE/VC"):
        growth_potential = 85
    elif company_type in ("公募基金", "量化私募", "互联网战投"):
        growth_potential = 80
    elif company_type in ("银行", "保险"):
        growth_potential = 60
    else:
        growth_potential = 70

    # 3. 奖金结构（实习生通常无奖金）
    bonus_structure = 50  # 实习生中立分

    # 4. 福利
    if company_type in ("券商", "外资投行", "互联网战投"):
        benefits = 75
    elif company_type in ("银行", "保险"):
        benefits = 80
    else:
        benefits = 65

    return SalaryScore(
        absolute=absolute,
        growth_potential=growth_potential,
        bonus_structure=bonus_structure,
        benefits=benefits,
    )
