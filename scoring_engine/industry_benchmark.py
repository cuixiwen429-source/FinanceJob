"""金融子行业预设评分表

静态基准分 + 可被 iFinD 数据动态修正。
"""

# 金融子行业四维基准评分 (0-100)
INDUSTRY_BENCHMARKS = {
    "证券研究/行研": {
        "growth": 85, "stability": 65, "barrier": 75, "personal_fit": 90,
        "description": "证券行业研究员，对标买方/卖方研究",
    },
    "投资银行IBD": {
        "growth": 80, "stability": 55, "barrier": 90, "personal_fit": 70,
        "description": "一级市场投行，IPO/并购/再融资",
    },
    "量化交易": {
        "growth": 90, "stability": 50, "barrier": 85, "personal_fit": 60,
        "description": "量化策略研究，多因子/高频/CTA",
    },
    "PE/VC": {
        "growth": 85, "stability": 50, "barrier": 80, "personal_fit": 65,
        "description": "私募股权/风险投资",
    },
    "固收/债券": {
        "growth": 70, "stability": 75, "barrier": 70, "personal_fit": 65,
        "description": "固定收益研究/交易",
    },
    "风控/合规": {
        "growth": 75, "stability": 80, "barrier": 75, "personal_fit": 60,
        "description": "风险管理/合规管理",
    },
    "财富管理": {
        "growth": 80, "stability": 70, "barrier": 55, "personal_fit": 55,
        "description": "财富管理/私人银行",
    },
    "银行总行管培": {
        "growth": 60, "stability": 95, "barrier": 60, "personal_fit": 50,
        "description": "银行总行管理培训生",
    },
    "金融科技": {
        "growth": 90, "stability": 70, "barrier": 70, "personal_fit": 55,
        "description": "金融科技/互金",
    },
    "保险精算": {
        "growth": 65, "stability": 85, "barrier": 80, "personal_fit": 40,
        "description": "保险精算/产品开发",
    },
    "战略投资/战投": {
        "growth": 85, "stability": 70, "barrier": 75, "personal_fit": 70,
        "description": "互联网/科技公司战略投资部",
    },
    "精品投行/FA": {
        "growth": 80, "stability": 50, "barrier": 65, "personal_fit": 75,
        "description": "财务顾问/精品投行",
    },
    "评级/金融数据": {
        "growth": 70, "stability": 80, "barrier": 60, "personal_fit": 60,
        "description": "信用评级/金融信息服务",
    },
}


def get_industry_benchmark(industry: str) -> dict:
    """返回行业基准评分，未匹配则返回中性默认值"""
    # 模糊匹配
    for key, val in INDUSTRY_BENCHMARKS.items():
        if key in industry or industry in key:
            return val
    return {"growth": 70, "stability": 65, "barrier": 60, "personal_fit": 50}


# 公司类型 → 行业映射
COMPANY_TYPE_TO_INDUSTRY = {
    "券商": "证券研究/行研",
    "公募基金": "证券研究/行研",
    "量化私募": "量化交易",
    "PE/VC": "PE/VC",
    "硬科技VC": "PE/VC",
    "精品投行": "精品投行/FA",
    "银行": "银行总行管培",
    "保险": "保险精算",
    "AMC": "证券研究/行研",
    "互联网战投": "战略投资/战投",
    "外资投行": "投资银行IBD",
    "外资买方": "证券研究/行研",
    "评级/数据": "评级/金融数据",
}


def get_industry_for_company_type(company_type: str) -> str:
    return COMPANY_TYPE_TO_INDUSTRY.get(company_type, "证券研究/行研")
