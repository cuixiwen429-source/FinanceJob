"""评分引擎数据模型"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JobMatchScore:
    skill_match: float = 0
    experience_match: float = 0
    education_match: float = 0
    certificate_match: float = 0
    softskill_match: float = 0

    @property
    def total(self) -> float:
        return (
            self.skill_match * 0.30 +
            self.experience_match * 0.25 +
            self.education_match * 0.20 +
            self.certificate_match * 0.15 +
            self.softskill_match * 0.10
        )


@dataclass
class IndustryMatchScore:
    growth: float = 0
    stability: float = 0
    barrier: float = 0
    personal_fit: float = 0

    @property
    def total(self) -> float:
        return (
            self.growth * 0.35 +
            self.stability * 0.25 +
            self.barrier * 0.20 +
            self.personal_fit * 0.20
        )


@dataclass
class SalaryScore:
    absolute: float = 0
    growth_potential: float = 0
    bonus_structure: float = 0
    benefits: float = 0

    @property
    def total(self) -> float:
        return (
            self.absolute * 0.40 +
            self.growth_potential * 0.30 +
            self.bonus_structure * 0.20 +
            self.benefits * 0.10
        )


@dataclass
class CareerDevScore:
    promotion_path: float = 0
    skill_accumulation: float = 0
    exit_options: float = 0
    platform_value: float = 0

    @property
    def total(self) -> float:
        return (
            self.promotion_path * 0.30 +
            self.skill_accumulation * 0.30 +
            self.exit_options * 0.25 +
            self.platform_value * 0.15
        )


@dataclass
class Adjustment:
    type: str
    value: float
    reason: str


@dataclass
class CompositeScore:
    job_id: str
    job_match: JobMatchScore = field(default_factory=JobMatchScore)
    industry_match: IndustryMatchScore = field(default_factory=IndustryMatchScore)
    salary: SalaryScore = field(default_factory=SalaryScore)
    career_dev: CareerDevScore = field(default_factory=CareerDevScore)
    adjustments: list[Adjustment] = field(default_factory=list)

    rank: int = 0
    percentile: float = 0

    @property
    def total(self) -> float:
        adj_sum = sum(a.value for a in self.adjustments)
        raw = (
            self.job_match.total * 0.40 +
            self.industry_match.total * 0.25 +
            self.salary.total * 0.15 +
            self.career_dev.total * 0.20 +
            adj_sum
        )
        return max(0, min(100, raw))

    @property
    def decision(self) -> str:
        if self.total >= 75:
            return "强烈推荐"
        elif self.total >= 60:
            return "推荐投递"
        elif self.total >= 45:
            return "可投递"
        else:
            return "建议跳过"
