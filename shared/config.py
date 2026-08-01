"""FinanceJob 共享配置管理

从 config.yaml + .env 加载用户配置，支持学术日历动态切换。
"""

import os
from datetime import date
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
DATA_DIR = PROJECT_ROOT / "data"
COOKIES_DIR = PROJECT_ROOT / "cookies"
DB_PATH = PROJECT_ROOT / "shared" / "financejob.db"


class SearchStrategy(BaseModel):
    cities: list[str] = ["深圳", "上海"]
    remote: bool = True
    keywords: list[str] = [
        "行研实习", "证券研究", "投资分析", "投行实习",
        "量化实习", "PE实习", "VC实习", "战投实习",
        "行业研究", "金融实习", "远程行研", "远程实习",
    ]
    boost_cities: list[str] = ["深圳"]
    boost_remote: bool = False
    remote_first: bool = False


class UserConfig(BaseModel):
    name: str = "崔曦文"
    graduation_year: int = 2028
    school: str = "华东师范大学"
    degree: str = "金融硕士"
    target_cities_break: list[str] = ["深圳", "上海"]  # 寒暑假
    target_cities_semester: list[str] = ["上海"]       # 在校
    remote_preferred: bool = True
    finance_directions: list[str] = ["行研", "投行", "量化", "PE/VC", "战投"]

    # 邮箱配置
    email_provider: str = "163"        # 163 / qq / custom
    email_address: str = ""
    email_smtp_server: str = "smtp.163.com"
    email_smtp_port: int = 465
    email_auth_code: str = ""          # 从 .env 加载

    # AI 配置
    ai_provider: str = "deepseek"
    ai_api_key: str = ""               # 从 .env 加载
    ai_base_url: str = "https://api.deepseek.com"
    ai_model: str = "deepseek-chat"

    # 黑名单
    blacklist_companies: list[str] = []
    blacklist_keywords: list[str] = [
        "外包", "外派", "单休", "大小周", "996",
        "销售", "客服", "催收", "保险代理",
    ]

    # 评分阈值
    score_strong_recommend: float = 75.0
    score_recommend: float = 60.0
    score_consider: float = 45.0

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "UserConfig":
        path = config_path or CONFIG_PATH
        data = {}
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

        # 从环境变量覆盖敏感信息
        data["email_auth_code"] = os.getenv("EMAIL_AUTH_CODE", data.get("email_auth_code", ""))
        data["email_address"] = os.getenv("EMAIL_ADDRESS", data.get("email_address", ""))
        data["ai_api_key"] = os.getenv("DEEPSEEK_API_KEY", os.getenv("OPENAI_API_KEY", data.get("ai_api_key", "")))

        return cls(**{k: v for k, v in data.items() if k in cls.model_fields})


def get_academic_term(today: Optional[date] = None) -> str:
    """根据日期返回当前学期阶段"""
    today = today or date.today()
    month, day = today.month, today.day

    if (month == 1) or (month == 2):
        return "winter_break"
    elif (month == 7) or (month == 8):
        return "summer_break"
    elif month >= 3 and month <= 6:
        return "spring_semester"
    else:
        return "fall_semester"


def get_search_strategy(today: Optional[date] = None) -> SearchStrategy:
    """根据学术日历返回动态搜索策略"""
    term = get_academic_term(today)

    if term in ("winter_break", "summer_break"):
        return SearchStrategy(
            cities=["深圳", "上海"],
            remote=True,
            keywords=[
                "行研实习", "证券研究", "投资分析", "投行实习",
                "量化实习", "PE实习", "VC实习", "战投实习",
                "行业研究", "金融实习",
            ],
            boost_cities=["深圳"],
            boost_remote=False,
            remote_first=False,
        )
    else:
        return SearchStrategy(
            cities=["上海"],
            remote=True,
            keywords=[
                "远程实习", "线上实习", "远程行研", "远程投研",
                "行研实习", "投资分析", "战投实习", "金融实习",
            ],
            boost_cities=["上海"],
            boost_remote=True,
            remote_first=True,
        )
