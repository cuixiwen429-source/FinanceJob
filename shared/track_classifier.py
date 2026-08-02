"""赛道分类引擎 — 将 1000+ 个 industry 标签收敛到 10 条赛道

每条赛道有独立的评分标准和用户适配权重。
支持多选（一个岗位可能跨多个赛道，如"固收量化"同时属于 ficc 和 quant）。
"""

from dataclasses import dataclass, field
from typing import Optional


# ── 赛道定义 ──

@dataclass
class Track:
    id: str
    name: str            # 中文名
    keywords: list[str]  # title/industry 中的匹配关键词
    exclude_keywords: list[str] = field(default_factory=list)  # 排除关键词（减少误匹配）
    description: str = ""


# 排序按优先级：更特异的赛道排在前面，否则 "量化" 会吃掉 "固收量化" 的匹配
TRACKS: list[Track] = [
    Track(
        id="ecm_dcm",
        name="资本市场(ECM/DCM)",
        keywords=["ECM", "DCM", "资本市场", "承销", "定增", "基石", "配售", "再融资"],
        description="股权/债权承销发行，与用户实习经验直接对口",
    ),
    Track(
        id="ibd",
        name="投行股权",
        keywords=["投行", "IBD", "IPO", "并购", "重组", "承做", "保荐", "M&A", "投资银行"],
        exclude_keywords=["ECM", "DCM", "资本市场"],
        description="一级市场股权融资项目执行",
    ),
    Track(
        id="quant",
        name="量化/金工",
        keywords=["量化", "quant", "CTA", "金工", "金融工程", "算法交易", "因子", "回测", "高频"],
        description="量化研究与交易策略",
    ),
    Track(
        id="ficc",
        name="固收/FICC",
        keywords=["固收", "信用研究", "FICC", "债券", "利率债", "ABS", "REITs", "信用债", "可转债", "DCM"],
        exclude_keywords=["量化", "quant"],
        description="固定收益研究、交易与承销",
    ),
    Track(
        id="research",
        name="行业研究",
        keywords=[
            "行研", "卖方研究", "买方研究", "研究所", "行业研究", "research",
            "研究员", "行业组", "分析师", "深度报告", "研究助理",
        ],
        exclude_keywords=["量化", "quant", "固收", "信用", "FICC", "债券"],
        description="卖/买方行业研究",
    ),
    Track(
        id="sales_trading",
        name="销售交易",
        keywords=["销售交易", "机构销售", "交易员", "做市", "S&T", "sales & trading", "经纪业务"],
        description="销售交易与经纪",
    ),
    Track(
        id="pe_vc",
        name="PE/VC/战投",
        keywords=[
            "PE", "VC", "战投", "股权投资", "私募股权", "产业投资", "CVC",
            "风险投资", "天使投资", "母基金", "直投", "创投", "资本",
        ],
        exclude_keywords=["投行", "IBD", "FA", "精品", "量化"],
        description="一级市场股权投资",
    ),
    Track(
        id="fa_boutique",
        name="FA/精品投行",
        keywords=["FA", "精品投行", "融资顾问", "财务顾问", "boutique"],
        description="精品投行与财务顾问",
    ),
    Track(
        id="asset_mgmt",
        name="资管/基金",
        keywords=[
            "资管", "资产管理", "公募基金", "FOF", "组合管理", "基金投研",
            "基金研究", "基金投资", "ETF",
        ],
        exclude_keywords=["量化", "quant", "私募", "PE", "VC", "风投", "创业投资"],
        description="公募基金与资产管理",
    ),
    Track(
        id="middle_back",
        name="中后台",
        keywords=[
            "风控", "合规", "运营", "财务", "HR", "人力资源", "IT", "行政",
            "法务", "审计", "清算", "托管",
        ],
        description="金融机构中后台职能",
    ),
]


def classify_track(title: str, industry: str, company_type: str) -> dict:
    """对单个岗位进行赛道分类，返回分类结果

    Args:
        title: 岗位名称
        industry: 行业标签（原始）
        company_type: 公司类型

    Returns:
        {"primary_track": "xxx", "tracks": ["track1", "track2"], "primary_name": "赛道名"}
    """
    combined = f"{title} {industry}".lower()
    ct = company_type.lower() if company_type else ""

    # 先找主赛道（第一个命中的赛道）
    primary = None
    primary_name = None

    for track in TRACKS:
        # 检查排除关键词
        if track.exclude_keywords and any(ek.lower() in combined for ek in track.exclude_keywords):
            continue

        # 检查匹配关键词
        if any(kw.lower() in combined for kw in track.keywords):
            primary = track.id
            primary_name = track.name
            break

    # 如果标题/行业没找到，用 company_type 兜底
    if not primary:
        if "券商" in ct:
            primary = "research"  # 券商默认行研
            primary_name = "行业研究"
        elif "量化" in ct:
            primary = "quant"
            primary_name = "量化/金工"
        elif "公募" in ct or "基金" in ct:
            primary = "asset_mgmt"
            primary_name = "资管/基金"
        elif "银行" in ct:
            primary = "middle_back"
            primary_name = "中后台"
        elif "保险" in ct:
            primary = "middle_back"
            primary_name = "中后台"
        elif "AMC" in ct:
            primary = "asset_mgmt"
            primary_name = "资管/基金"
        else:
            primary = "pe_vc"  # 其他默认为投资类
            primary_name = "PE/VC/战投"

    # 再找所有匹配的赛道（允许多选）
    all_tracks = []
    for track in TRACKS:
        if track.exclude_keywords and any(ek.lower() in combined for ek in track.exclude_keywords):
            continue
        if any(kw.lower() in combined for kw in track.keywords):
            if track.id not in all_tracks:
                all_tracks.append(track.id)

    # 确保主赛道在列表中
    if primary and primary not in all_tracks:
        all_tracks.insert(0, primary)

    return {
        "primary_track": primary,
        "tracks": all_tracks if all_tracks else [primary],
        "primary_name": primary_name,
    }


def get_track_info(track_id: str) -> Optional[Track]:
    """根据赛道 ID 获取赛道信息"""
    for t in TRACKS:
        if t.id == track_id:
            return t
    return None


def list_tracks() -> list[dict]:
    """列出所有赛道及说明"""
    return [
        {"id": t.id, "name": t.name, "description": t.description}
        for t in TRACKS
    ]


def classify_batch(jobs: list[dict]) -> list[dict]:
    """批量分类，返回带 track 信息的结果列表"""
    results = []
    for job in jobs:
        result = classify_track(
            job.get("title", ""),
            job.get("industry", ""),
            job.get("company_type", ""),
        )
        results.append({**job, **result})
    return results
