"""FinanceJob 共享数据模型

统一的 Pydantic 数据模型贯穿爬虫→评分→简历→投递全流程。
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    NEW = "new"
    SCORED = "scored"
    RESUME_READY = "resume_ready"
    APPLIED = "applied"
    REPLIED = "replied"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class Decision(str, Enum):
    STRONG_RECOMMEND = "强烈推荐"
    RECOMMEND = "推荐投递"
    CONSIDER = "可投递"
    SKIP = "建议跳过"


class CompanyType(str, Enum):
    SECURITIES = "券商"
    FUND = "公募基金"
    QUANT = "量化私募"
    PEVC = "PE/VC"
    FA = "精品投行"
    BANK = "银行"
    INSURANCE = "保险"
    AMC = "AMC"
    TECH_INVEST = "互联网战投"
    HARD_TECH_VC = "硬科技VC"
    FOREIGN_IB = "外资投行"
    FOREIGN_BUY = "外资买方"
    RATING_DATA = "评级/数据"
    OTHER = "其他"


class JobMatchDetail(BaseModel):
    skill_match: float = 0
    experience_match: float = 0
    education_match: float = 0
    certificate_match: float = 0
    softskill_match: float = 0


class IndustryMatchDetail(BaseModel):
    growth: float = 0
    stability: float = 0
    barrier: float = 0
    personal_fit: float = 0


class SalaryDetail(BaseModel):
    absolute: float = 0
    growth_potential: float = 0
    bonus_structure: float = 0
    benefits: float = 0


class CareerDevDetail(BaseModel):
    promotion_path: float = 0
    skill_accumulation: float = 0
    exit_options: float = 0
    platform_value: float = 0


class Adjustment(BaseModel):
    type: str
    value: float
    reason: str


class CompanyReputation(BaseModel):
    """全网口碑汇总"""
    kanzhun_score: Optional[float] = None      # 看准网 1-5
    maimai_sentiment: Optional[float] = None   # 脉脉情感 -1到1
    niuke_positive_ratio: Optional[float] = None  # 牛客正面比例
    zhihu_summary: Optional[str] = None
    xiaohongshu_summary: Optional[str] = None
    glassdoor_score: Optional[float] = None    # Glassdoor 1-5
    overall_sentiment: float = 0               # 综合情感 -1到1
    risk_flags: list[str] = []                 # 风险标签
    last_updated: Optional[datetime] = None


class Job(BaseModel):
    """统一岗位数据模型"""
    # 基础信息
    id: Optional[str] = None
    platform: str = ""
    source_type: str = "platform"  # platform / company_careers
    title: str = ""
    company: str = ""
    company_type: Optional[CompanyType] = None
    industry: str = ""
    location: str = ""
    is_remote: bool = False
    salary_raw: str = ""
    salary_monthly_est: Optional[float] = None
    salary_annual_est: Optional[float] = None
    jd_raw: str = ""
    jd_clean: str = ""
    recruiter_email: str = ""
    apply_url: str = ""
    scraped_at: Optional[datetime] = None

    # 科学评分
    composite_score: float = 0
    rank: int = 0
    percentile: float = 0
    decision: Optional[Decision] = None

    job_match_score: float = 0
    job_match_detail: JobMatchDetail = Field(default_factory=JobMatchDetail)

    industry_match_score: float = 0
    industry_match_detail: IndustryMatchDetail = Field(default_factory=IndustryMatchDetail)

    salary_score: float = 0
    salary_detail: SalaryDetail = Field(default_factory=SalaryDetail)

    career_dev_score: float = 0
    career_dev_detail: CareerDevDetail = Field(default_factory=CareerDevDetail)

    adjustments: list[Adjustment] = []

    # 口碑
    reputation: Optional[CompanyReputation] = None

    # 简历
    tailored_resume_path: str = ""
    cover_letter: str = ""

    # 状态
    status: JobStatus = JobStatus.NEW
    reasoning: str = ""
    sent_at: Optional[datetime] = None

    def generate_id(self) -> str:
        """生成唯一 ID"""
        import hashlib
        raw = f"{self.platform}|{self.company}|{self.title}|{self.apply_url}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def is_high_priority(self) -> bool:
        return self.decision in (Decision.STRONG_RECOMMEND, Decision.RECOMMEND)
