"""修正因子计算 — Adjustments

公司口碑 + 城市匹配(学术日历动态) + 国企加分 + 急聘信号 + 面试口碑
"""

from datetime import date

from scoring_engine.models import Adjustment
from scraper.academic_calendar import get_city_score, get_remote_bonus, is_break


def calculate_adjustments(job: dict, reputation: dict = None) -> list[Adjustment]:
    """计算全部修正因子"""
    adjustments = []

    city = job.get("location", "")
    is_remote = job.get("is_remote", False)
    company = job.get("company", "")
    company_type = job.get("company_type", "")
    jd_text = (job.get("jd_raw", "") + job.get("title", "")).lower()
    today = date.today()

    # ── 公司口碑 ──
    if reputation:
        kscore = reputation.get("kanzhun_score")
        if kscore is not None:
            if kscore < 3.0:
                adjustments.append(Adjustment("看准网评分低", -8, f"看准网评分 {kscore}"))
            elif kscore >= 4.0:
                adjustments.append(Adjustment("看准网高评分", 3, f"看准网评分 {kscore}"))

        sentiment = reputation.get("overall_sentiment", 0)
        if sentiment < -0.3:
            adjustments.append(Adjustment("口碑偏负面", -5, f"综合情感 {sentiment:.2f}"))
        elif sentiment > 0.3:
            adjustments.append(Adjustment("口碑正面", 2, f"综合情感 {sentiment:.2f}"))

        risk_flags = reputation.get("risk_flags", [])
        for flag in risk_flags:
            if "裁员" in flag or "降薪" in flag:
                adjustments.append(Adjustment("风险预警-裁员降薪", -5, flag))
            elif "劳动仲裁" in flag or "欠薪" in flag:
                adjustments.append(Adjustment("风险预警-劳资纠纷", -10, flag))
            elif "PUA" in flag or "加班严重" in flag:
                adjustments.append(Adjustment("风险预警-工作环境", -3, flag))

    # ── 城市匹配 ──
    city_score = get_city_score(city, today)
    if is_remote:
        city_score = max(city_score, get_city_score("远程", today))
    remote_bonus = get_remote_bonus(is_remote, today)
    total_city_bonus = city_score + remote_bonus

    if total_city_bonus > 0:
        term_str = "寒暑假" if is_break(today) else "在校期间"
        reason = f"{city}{'远程+' if is_remote and remote_bonus else ''}"
        if remote_bonus > 0:
            reason += f" ({term_str}远程优先)"
        adjustments.append(Adjustment("城市匹配", total_city_bonus, reason))
    elif total_city_bonus < 0:
        adjustments.append(Adjustment("城市不匹配", total_city_bonus, f"目标城市不含{city}"))

    # ── 国企/央企加分 ──
    soe_keywords = ["国有企业", "央企", "中央企业", "事业单位", "国有控股", "国有独资"]
    if any(kw in company_type or kw in company for kw in soe_keywords):
        adjustments.append(Adjustment("国企/央企", 3, "国有企业加分"))

    # ── 急聘信号 ──
    urgent_keywords = ["急聘", "急招", "立即到岗", "尽快到岗", "尽快入职", "urgent", "immediate"]
    if any(kw in jd_text for kw in urgent_keywords):
        adjustments.append(Adjustment("急聘", 2, "标注急聘/立即到岗"))

    return adjustments
