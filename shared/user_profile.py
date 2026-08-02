"""崔曦文个人画像 — 评分引擎和 AI 分析的统一用户画像"""

from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import json


@dataclass
class UserProfile:
    """崔曦文的完整求职画像，注入到所有评分和 AI 分析中"""

    name: str = "崔曦文"

    # ── 教育背景 ──
    education: list[dict] = field(default_factory=lambda: [
        {
            "degree": "工学学士",
            "major": "水利水电工程",
            "school": "黑龙江大学",
            "rank": "前10%",
            "year": "2026届",
            "note": "理工科定量分析底子扎实，具备数学建模和数据分析训练",
        },
        {
            "degree": "金融硕士",
            "school": "华东师范大学",
            "status": "2026年9月入学（已录取）",
            "note": "考研已上岸，金融学综合基础已建立",
        },
    ])

    # ── 实习经历 ──
    internships: list[dict] = field(default_factory=lambda: [
        {
            "company": "长江证券承销保荐有限公司",
            "department": "资本市场部",
            "role": "实习生",
            "focus": ["定向增发", "基石投资", "股权项目"],
            "duration": "每周5天，进行中",
            "skills_gained": [
                "定增流程与法规",
                "基石投资者沟通与尽调",
                "发行方案设计",
                "股权融资项目执行",
            ],
        },
    ])

    # ── 技能 ──
    hard_skills: list[str] = field(default_factory=lambda: [
        "财务建模（DCF、可比公司）",
        "Python/Pandas 数据分析",
        "Wind/同花顺/iFinD 金融终端",
        "Excel 高级应用",
        "行业研究框架",
        "尽职调查",
        "AI 工具多模型协同工作流",
    ])

    soft_skills: list[str] = field(default_factory=lambda: [
        "快速学习（跨专业考研成功）",
        "定量分析思维",
        "多线程项目管理",
    ])

    # ── 证书 ──
    certificates: list[str] = field(default_factory=lambda: [
        "证券从业资格（备考中）",
        "CFA Level 1（计划中）",
    ])

    # ── 赛道偏好 ──
    track_preferences: dict = field(default_factory=lambda: {
        # track_id → preference_weight (1-10)
        "ecm_dcm": 10,        # 直接对口
        "ibd": 9,             # 高度相关
        "research": 8,        # 理工背景优势
        "fa_boutique": 7,     # 门槛适中
        "pe_vc": 6,           # 可尝试
        "asset_mgmt": 5,
        "ficc": 4,
        "sales_trading": 3,
        "middle_back": 2,
        "quant": 2,           # 非优势赛道
    })

    # ── 地点偏好 ──
    location_preferences: list[str] = field(default_factory=lambda: [
        "上海", "北京", "深圳",
    ])

    # ── 竞争优势 ──
    competitive_edge: list[str] = field(default_factory=lambda: [
        "理工+金融复合背景：行研（尤其制造业/能源/基建/TMT）赛道有差异化优势",
        "已有券商资本市场部实战经验（非纯校园经历），了解股权融资全流程",
        "水利工程学科的数据分析训练可迁移至研究岗的定量分析工作",
        "跨专业考研成功证明学习能力和自我驱动力",
    ])

    # ── 竞争劣势 ──
    competitive_weakness: list[str] = field(default_factory=lambda: [
        "本科非财经类 target school（黑龙江大学）",
        "硕士华师在金融圈不是一线 target（非清北复交人两财一贸）",
        "金融知识体系仍在构建中（刚跨考上岸），传统商科课程（会计/公司金融/投资学）需系统补",
        "没有顶级买方/大平台经历",
        "量化背景弱，纯量化岗位竞争力不足",
    ])

    # ── 职业目标 ──
    career_goals: dict = field(default_factory=lambda: {
        "short_term": "6-12个月内进入券商投行部或资本市场部实习/正式岗，积累项目经验",
        "mid_term": "1-3年积累股权融资项目经验，建立行业专长（能源/基建方向）",
        "long_term": "利用理工+金融复合背景在投行/产业投资领域深耕，向VP/Director发展",
    })

    # ── 位置 ──
    school_location: str = "上海"

    # ── 辅助方法 ──

    def to_ai_context(self) -> str:
        """生成注入 AI prompt 的完整上下文"""
        return f"""## 用户画像：崔曦文

【教育背景】
- 本科：黑龙江大学 水利水电工程专业（GPA前10%），2026年毕业
- 硕士：华东师范大学 金融硕士，2026年9月入学（已录取）
- 特点：理工科转金融，具备定量分析底子

【实习经历】
- 当前在长江证券承销保荐有限公司 资本市场部实习
- 参与股权项目：定向增发、基石投资
- 每周5天，熟悉股权融资全流程

【核心技能】
{chr(10).join(f"- {s}" for s in self.hard_skills)}

【竞争优势】
{chr(10).join(f"- {s}" for s in self.competitive_edge)}

【竞争劣势】
{chr(10).join(f"- {s}" for s in self.competitive_weakness)}

【职业目标】
- 短期：{self.career_goals['short_term']}
- 中期：{self.career_goals['mid_term']}
- 长期：{self.career_goals['long_term']}

【偏好】
- 地点：{', '.join(self.location_preferences)}（学校在{self.school_location}）
- 最优先赛道：ECM/DCM、投行IBD、行业研究"""

    def get_track_fit_score(self, track_id: str) -> float:
        """获取用户对某条赛道的天然适配分数 (0-100)"""
        pref = self.track_preferences.get(track_id, 5)
        return min(100, pref * 10)

    def is_preferred_location(self, location: str) -> bool:
        """检查地点是否在用户偏好中"""
        if not location:
            return False
        return any(city in location for city in self.location_preferences)

    @classmethod
    def load(cls) -> "UserProfile":
        """加载用户画像（可从 data/user_profile.json 覆盖默认值）"""
        profile_path = Path(__file__).resolve().parent.parent / "data" / "user_profile.json"
        if profile_path.exists():
            data = json.loads(profile_path.read_text(encoding="utf-8"))
            return cls(**data)
        return cls()


# 全局单例
_user_profile: Optional[UserProfile] = None


def get_profile() -> UserProfile:
    global _user_profile
    if _user_profile is None:
        _user_profile = UserProfile.load()
    return _user_profile
