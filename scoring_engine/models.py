"""评分引擎数据模型 v3 — 赛道感知 + 个人化评分 + 四档决策分桶"""

from dataclasses import dataclass, field
from typing import Optional


# ── 旧维度保留（兼容） ──

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


# ── v3: 个人化评分维度 ──

@dataclass
class PersonalizedScore:
    """五个个人化评分维度（替代原来的四维）"""

    track_fit: float = 0         # 赛道契合度（该赛道对用户的天然适配程度）
    threshold_match: float = 0   # 准入门槛匹配（学历/年级/经验要求是否达标）
    tier_match: float = 0        # 机构层级匹配（公司tier与用户竞争力的匹配度）
    edge_leverage: float = 0     # 背景优势发挥（岗位是否能发挥理工+金融复合优势）
    growth_value: float = 0      # 成长价值（对职业路径的长期贡献）

    # 原始维度备份
    job_match: JobMatchScore = field(default_factory=JobMatchScore)
    industry_match: IndustryMatchScore = field(default_factory=IndustryMatchScore)
    salary: SalaryScore = field(default_factory=SalaryScore)
    career_dev: CareerDevScore = field(default_factory=CareerDevScore)

    @property
    def total(self) -> float:
        """五维加权综合分（0-100）"""
        raw = (
            self.track_fit * 0.30 +
            self.threshold_match * 0.25 +
            self.tier_match * 0.20 +
            self.edge_leverage * 0.15 +
            self.growth_value * 0.10
        )
        return max(0, min(100, raw))

    @property
    def decision(self) -> str:
        """四档决策分桶（v3 核心输出）"""
        # 门槛不满足 → 直接不推荐
        if self.threshold_match < 40:
            return "不推荐"

        t = self.total
        if t >= 72:
            return "优先投"
        elif t >= 55:
            return "值得投"
        elif t >= 38:
            return "可考虑"
        else:
            return "不推荐"

    @property
    def decision_emoji(self) -> str:
        return {
            "优先投": "🟢",
            "值得投": "🔵",
            "可考虑": "🟡",
            "不推荐": "⚪",
        }.get(self.decision, "⚪")

    @property
    def reasoning(self) -> str:
        """生成决策理由"""
        parts = [
            f"赛道契合={self.track_fit:.0f}",
            f"门槛匹配={self.threshold_match:.0f}",
            f"机构层级={self.tier_match:.0f}",
            f"优势发挥={self.edge_leverage:.0f}",
            f"成长价值={self.growth_value:.0f}",
        ]
        return " | ".join(parts)


# 兼容旧 CompositeScore
@dataclass
class CompositeScore:
    job_id: str
    job_match: JobMatchScore = field(default_factory=JobMatchScore)
    industry_match: IndustryMatchScore = field(default_factory=IndustryMatchScore)
    salary: SalaryScore = field(default_factory=SalaryScore)
    career_dev: CareerDevScore = field(default_factory=CareerDevScore)
    adjustments: list[Adjustment] = field(default_factory=list)
    personalized: Optional[PersonalizedScore] = None

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
        # 优先用个性化评分
        if self.personalized:
            return self.personalized.decision
        # 兼容旧逻辑
        if self.total >= 75:
            return "强烈推荐"
        elif self.total >= 60:
            return "推荐投递"
        elif self.total >= 45:
            return "可投递"
        else:
            return "建议跳过"
