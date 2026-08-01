"""学术日历驱动的动态搜索策略

根据当前日期自动切换:
- 寒暑假: 深圳+上海+远程
- 在校期间: 远程优先 + 上海其次
"""

from datetime import date
from enum import Enum


class Term(str, Enum):
    WINTER_BREAK = "winter_break"    # 1月-2月
    SPRING_SEMESTER = "spring_semester"  # 3月-6月
    SUMMER_BREAK = "summer_break"    # 7月-8月
    FALL_SEMESTER = "fall_semester"  # 9月-12月


def get_current_term(today: date = None) -> Term:
    today = today or date.today()
    m = today.month

    if m in (1, 2):
        return Term.WINTER_BREAK
    elif m in (7, 8):
        return Term.SUMMER_BREAK
    elif 3 <= m <= 6:
        return Term.SPRING_SEMESTER
    else:
        return Term.FALL_SEMESTER


def is_break(today: date = None) -> bool:
    term = get_current_term(today)
    return term in (Term.WINTER_BREAK, Term.SUMMER_BREAK)


def get_city_score(city: str, today: date = None) -> int:
    """根据学术日历返回城市匹配加分"""
    term = get_current_term(today)
    city_lower = city.lower()

    if is_break(today):
        if "深圳" in city_lower:
            return 3
        elif "上海" in city_lower:
            return 3
        elif "remote" in city_lower or "远程" in city_lower or "线上" in city_lower:
            return 3
    else:
        if "remote" in city_lower or "远程" in city_lower or "线上" in city_lower:
            return 3
        elif "上海" in city_lower:
            return 1

    return 0


def get_remote_bonus(is_remote: bool, today: date = None) -> int:
    """在校期间远程岗位额外加分"""
    if is_remote and not is_break(today):
        return 2
    return 0
