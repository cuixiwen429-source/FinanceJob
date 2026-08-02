"""公司分层引擎 — 将公司映射到 S/A/B/C 四级 tier

包含：
1. 各公司类型下的 tier 映射表（手动维护）
2. LLM 辅助判断未知公司的 tier
3. 批量标注函数
"""

from dataclasses import dataclass
from typing import Optional, Literal
import json

TierLevel = Literal["S", "A", "B", "C", "U"]


@dataclass
class TierResult:
    tier: TierLevel
    tier_label: str  # S-顶级 / A-一线 / B-二线 / C-其他 / U-未知
    matched_by: str  # "exact" | "fuzzy" | "llm" | "rule"
    confidence: float = 1.0
    note: str = ""


# ── 券商 ──
BROKER_TIER: dict[str, TierLevel] = {
    # S-Tier：三中一华
    "中金": "S", "CICC": "S", "中金公司": "S", "中金财富": "S",
    "中信证券": "S", "CITIC": "S", "中信建投": "S",
    "华泰证券": "S", "华泰联合": "S", "华泰": "S",

    # A-Tier：颈部券商
    "国泰君安": "A", "国泰海通": "A", "海通证券": "A", "海通": "A",
    "招商证券": "A", "广发证券": "A", "广发": "A",
    "申万宏源": "A", "申万": "A", "中国银河": "A", "银河证券": "A",
    "国信证券": "A", "东方证券": "A",

    # B-Tier：腰部券商
    "兴业证券": "B", "光大证券": "B", "平安证券": "B",
    "安信证券": "B", "国投证券": "B",
    "中泰证券": "B", "方正证券": "B", "长江证券": "B",
    "天风证券": "B", "国金证券": "B", "东吴证券": "B",
    "浙商证券": "B", "华创证券": "B", "民生证券": "B",
    "国海证券": "B", "开源证券": "B", "中航证券": "B",
    "国元证券": "B", "财通证券": "B", "西部证券": "B",
    "东海证券": "B", "中银证券": "B", "东北证券": "B",
    "华西证券": "B", "西南证券": "B", "信达证券": "B",
    "长城证券": "B", "华鑫证券": "B", "太平洋证券": "B",
    "首创证券": "B", "万联证券": "B", "华安证券": "B",
}

# ── PE/VC ──
PEVC_TIER: dict[str, TierLevel] = {
    # S-Tier
    "高瓴": "S", "高瓴资本": "S", "Hillhouse": "S",
    "红杉": "S", "红杉中国": "S", "Sequoia": "S",
    "鼎晖": "S", "鼎晖投资": "S", "CDH": "S",
    "腾讯投资": "S", "阿里资本": "S", "阿里巴巴": "S",
    "字节跳动": "S", "美团战投": "S",
    "深创投": "S", "达晨": "S", "达晨财智": "S",

    # A-Tier
    "IDG": "A", "IDG资本": "A", "经纬中国": "A", "经纬": "A", "Matrix": "A",
    "启明创投": "A", "启明": "A", "Qiming": "A",
    "君联资本": "A", "君联": "A",
    "北极光创投": "A", "北极光": "A",
    "源码资本": "A", "源码": "A", "云九资本": "A",
    "高榕资本": "A", "蓝驰创投": "A",
    "GGV": "A", "纪源资本": "A", "顺为资本": "A",
    "华平投资": "A", "华平": "A", "Warburg": "A",
    "凯雷": "A", "Carlyle": "A", "淡马锡": "A", "Temasek": "A",
    "中金资本": "A", "中信产业基金": "A", "CPE": "A", "国开金融": "A",
    "云锋基金": "A",

    # B-Tier
    "钟鼎资本": "B", "元璟资本": "B", "天壹资本": "B",
    "方广资本": "B", "创瓴资本": "B", "奇迹资本": "B",
    "光源资本": "B", "领沨资本": "B", "海川资本": "B",
    "国科长三角资本": "B", "深石资本": "B", "九皓资本": "B",
    "聚源通汇资本": "B", "广发乾和": "B", "广发乾和投资": "B",
    "越秀产业基金": "B",
}

# ── 公募基金 ──
FUND_TIER: dict[str, TierLevel] = {
    # S-Tier
    "易方达": "S", "华夏基金": "S", "华夏": "S",
    "广发基金": "S", "南方基金": "S", "富国基金": "S",
    "汇添富": "S", "汇添富基金": "S",
    "招商基金": "S", "嘉实基金": "S", "嘉实": "S", "博时基金": "S",

    # A-Tier
    "鹏华基金": "A", "华安基金": "A", "银华基金": "A",
    "中欧基金": "A", "景顺长城": "A", "交银施罗德": "A",
    "工银瑞信": "A", "天弘基金": "A", "兴证全球": "A",
    "万家基金": "A", "中银基金": "A",

    # B-Tier
    "浦银安盛": "B", "浦银安盛基金": "B", "国金基金": "B",
    "国联安": "B",
}

# ── 量化私募 ──
QUANT_TIER: dict[str, TierLevel] = {
    # S-Tier
    "九坤": "S", "九坤投资": "S", "幻方": "S", "幻方量化": "S",
    "明汯": "S", "明汯投资": "S", "灵均": "S", "灵均投资": "S",
    "衍复": "S", "衍复投资": "S",

    # A-Tier
    "鸣石": "A", "鸣石投资": "A", "启林": "A", "启林投资": "A",
    "天演": "A", "天演资本": "A", "佳期": "A", "佳期投资": "A",
    "黑翼": "A", "黑翼资产": "A", "因诺": "A", "因诺资产": "A",
    "宽德": "A", "宽德投资": "A", "思勰": "A", "思勰投资": "A",
    "千象": "A", "千象资产": "A",

    # B-Tier
    "厚方投资": "B", "厚方": "B",
}

# ── 银行 ──
BANK_TIER: dict[str, TierLevel] = {
    "工商银行": "A", "建设银行": "A", "农业银行": "A", "中国银行": "A",
    "交通银行": "A", "邮储银行": "A",
    "招商银行": "A", "兴业银行": "A", "浦发银行": "A",
    "中信银行": "B", "民���银行": "B", "光大银行": "B",
    "平安银行": "B", "华夏银行": "B", "广发银行": "B",
}

# ── 保险 ──
INSURANCE_TIER: dict[str, TierLevel] = {
    "中国人寿": "A", "中国平安": "A", "中国太保": "A",
    "泰康": "A", "新华保险": "B", "阳光保险": "B",
}

# ── 互联网战投 ──
INTERNET_TIER: dict[str, TierLevel] = {
    "腾讯": "S", "阿里巴巴": "S", "阿里": "S", "字节跳动": "S",
    "美团": "A", "京东": "A", "百度": "A", "快手": "A",
    "小红书": "A", "拼多多": "A", "B站": "B", "bilibili": "B",
    "网易": "A",
}

# ── 按 company_type 选择映射表 ──

TIER_MAP_BY_TYPE: dict[str, dict[str, TierLevel]] = {
    "券商": BROKER_TIER,
    "pe/vc": PEVC_TIER,
    "硬科技vc": PEVC_TIER,
    "互联网战投": INTERNET_TIER,
    "公募基金": FUND_TIER,
    "量化私募": QUANT_TIER,
    "银行": BANK_TIER,
    "保险": INSURANCE_TIER,
    "精品投行": PEVC_TIER,   # 精品投行用 PE/VC 的分层逻辑
    "amc": BANK_TIER,        # AMC 按银行分
    "评级/数据": {},          # 暂无分层
    "其他": {},
}


TIER_LABELS: dict[TierLevel, str] = {
    "S": "顶级",
    "A": "一线",
    "B": "二线",
    "C": "其他",
    "U": "未知",
}


def match_company_tier(
    company: str,
    company_type: str,
    use_llm: bool = False,
    llm_client=None,
) -> TierResult:
    """根据公司名和类型判断 tier

    Args:
        company: 公司名称
        company_type: 公司类型（券商/PE:VC/公募基金等）
        use_llm: 如果未匹配，是否用 LLM 辅助判断
        llm_client: LLM 客户端实例

    Returns:
        TierResult
    """
    if not company:
        return TierResult(tier="U", tier_label="未知", matched_by="rule",
                          confidence=0.5, note="公司名为空")

    # 1. 精确匹配
    company_clean = company.strip().replace("（", "(").replace("）", ")")
    ct_lower = company_type.lower().replace("_", "/") if company_type else ""

    tier_map = TIER_MAP_BY_TYPE.get(ct_lower, {})
    # 如果该类型没有专属映射，尝试所有映射
    all_maps = [tier_map] if tier_map else [
        BROKER_TIER, PEVC_TIER, FUND_TIER, QUANT_TIER,
        BANK_TIER, INSURANCE_TIER, INTERNET_TIER,
    ]

    for tmap in all_maps:
        for key, tier in tmap.items():
            if key.lower() in company_clean.lower():
                return TierResult(
                    tier=tier,
                    tier_label=TIER_LABELS[tier],
                    matched_by="exact",
                    note=f"精确匹配: {key}",
                )

    # 2. 模糊匹配规则（基于关键词推断）
    tier = _rule_based_tier(company_clean, ct_lower)
    if tier != "U":
        return TierResult(
            tier=tier,
            tier_label=TIER_LABELS[tier],
            matched_by="fuzzy",
            confidence=0.6,
            note="关键词规则推断",
        )

    # 3. 含"证券"关键词的默认视为券商 B-Tier
    if "证券" in company_clean:
        return TierResult(
            tier="C",
            tier_label="其他",
            matched_by="rule",
            confidence=0.5,
            note="未在分层表中，含'证券'关键词，默认归为C-Tier",
        )

    # 4. LLM 辅助
    if use_llm and llm_client:
        try:
            return _llm_guess_tier(company, company_type, llm_client)
        except Exception:
            pass

    return TierResult(tier="U", tier_label="未知", matched_by="rule",
                      confidence=0.3, note="无法确定，需人工标注")


def _rule_based_tier(company: str, ct_lower: str) -> TierLevel:
    """基于公司名中的关键词做规则推断"""
    cl = company.lower()

    # 券商关键词
    if "证券" in company:
        # 头部关键词
        if any(k in cl for k in ["中信", "中金", "华泰", "国泰", "海通", "招商", "广发", "申万", "银河"]):
            return "A"
        if any(k in cl for k in ["兴业", "光大", "平安", "安信", "国投", "中泰", "方正", "长江", "天风", "东吴", "国金"]):
            return "B"
        return "C"

    # 银行
    if any(k in cl for k in ["银行", "bank"]):
        return "B"

    # PE/VC
    if any(k in company for k in ["资本", "投资", "Venture", "Capital", "capital"]):
        return "B"

    # 量化
    if "量化" in company:
        return "B"

    return "U"


def _llm_guess_tier(company: str, company_type: str, llm_client) -> TierResult:
    """用 LLM 判断未知公司的 tier"""
    prompt = f"""你是一个中国金融行业机构分层专家。请判断以下公司的行业层级。

公司名称：{company}
公司类型：{company_type}

行业层级定义：
- S (顶级)：行业公认头部，竞争非常激烈。如券商的三中一华（中金/中信/中信建投/华泰），PE的红杉/高瓴/鼎晖。
- A (一线)：知名机构，行业认可度高。如券商的国泰君安/海通/招商/广发，PE的IDG/经纬/启明。
- B (二线)：腰部机构，有一定知名度。如券商的兴业/光大/天风/东吴。
- C (其他)：中小机构或新设机构。
- U (未知)：无法判断。

请只返回 JSON：
{{"tier": "S/A/B/C/U", "reason": "一句话理由"}}
"""
    try:
        result = llm_client.chat_json(
            [{"role": "user", "content": prompt}],
            system="你是金融机构分层专家。只输出 JSON。",
            temperature=0.1,
        )
        tier = result.get("tier", "U")
        if tier not in ("S", "A", "B", "C", "U"):
            tier = "U"
        return TierResult(
            tier=tier,
            tier_label=TIER_LABELS[tier],
            matched_by="llm",
            confidence=0.7,
            note=result.get("reason", ""),
        )
    except Exception:
        return TierResult(
            tier="U", tier_label="未知", matched_by="rule",
            confidence=0.3, note="LLM 调用失败",
        )


def batch_assign_tiers(
    jobs: list[dict],
    use_llm: bool = False,
    llm_client=None,
    only_unknown: bool = False,
) -> list[dict]:
    """批量标注公司 tier

    Args:
        jobs: 岗位列表（需含 company 和 company_type 字段）
        use_llm: 是否对未匹配公司使用 LLM 判断
        llm_client: LLM 客户端
        only_unknown: 仅标注当前 tier 为 U 或空的岗位

    Returns:
        附带 company_tier 的岗位列表
    """
    results = []
    for job in jobs:
        company = job.get("company", "")
        company_type = job.get("company_type", "")

        # 如果 only_unknown 且已有非U的tier，跳过
        existing_tier = job.get("company_tier", "")
        if only_unknown and existing_tier and existing_tier != "U":
            results.append(job)
            continue

        result = match_company_tier(company, company_type, use_llm, llm_client)
        job["company_tier"] = result.tier
        job["company_tier_label"] = result.tier_label
        job["company_tier_note"] = result.note
        results.append(job)

    return results
