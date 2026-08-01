"""★ 全网口碑采集器

六平台并行采集 + 多源数据融合 + LLM 情感分析。

数据源:
  看准网 (30%) — 公司评分/薪资/面经
  脉脉 (25%) — 员工匿名评价
  牛客网 (20%) — 面经/Offer对比
  知乎 (10%) — 长文深度评价
  小红书 (10%) — 实习体验/避雷
  Glassdoor (5%) — 外资公司评分

频率: 首次爬取立即采集，每7天刷新。
"""

import re
import time
import random
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from shared.llm import get_llm
from shared.db import FinanceJobDB
# CompanyReputation 在 shared/models.py 中定义


REPUTATION_SCHEMA = {
    "kanzhun_score": "number|null — 看准网评分 1-5",
    "maimai_sentiment": "number|null — 脉脉情感 -1到1",
    "niuke_positive_ratio": "number|null — 牛客正面比例 0-1",
    "zhihu_summary": "string|null — 知乎评价摘要 ≤100字",
    "xiaohongshu_summary": "string|null — 小红书评价摘要 ≤100字",
    "glassdoor_score": "number|null — Glassdoor评分 1-5",
    "overall_sentiment": "number — 综合情感 -1到1",
    "risk_flags": "string[] — 风险标签列表",
}


class ReputationFetcher:
    """全网口碑采集器"""

    def __init__(self, db: FinanceJobDB):
        self.db = db
        self._llm = None
        self.session = requests.Session()

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm()
        return self._llm
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        })

    def fetch_company(self, company: str) -> dict:
        """采集单家公司口碑"""
        # 检查缓存（7天内）
        cached = self.db.get_reputation(company)
        if cached:
            last_updated = cached.get("last_updated", "")
            if last_updated:
                try:
                    dt = datetime.fromisoformat(last_updated)
                    if (datetime.now() - dt).days < 7:
                        return dict(cached)
                except Exception:
                    pass

        # 并行采集（串行实现，避免反爬）
        results = {
            "kanzhun": None,
            "maimai": None,
            "niuke": None,
            "zhihu": None,
            "xiaohongshu": None,
            "glassdoor": None,
        }

        try:
            results["kanzhun"] = self._fetch_kanzhun(company)
        except Exception:
            pass
        time.sleep(random.uniform(0.5, 1.5))

        try:
            results["zhihu"] = self._fetch_zhihu(company)
        except Exception:
            pass
        time.sleep(random.uniform(0.5, 1.5))

        try:
            results["niuke"] = self._fetch_niuke(company)
        except Exception:
            pass

        # 如果是外资公司，同时查 Glassdoor
        if self._is_foreign_company(company):
            try:
                results["glassdoor"] = self._fetch_glassdoor(company)
            except Exception:
                pass

        # LLM 融合多源数据
        merged = self._merge_with_llm(company, results)

        # 存入缓存
        self.db.upsert_reputation(company, merged)
        return merged

    def _fetch_kanzhun(self, company: str) -> Optional[dict]:
        """看准网采集 — 公司评分"""
        try:
            search_url = f"https://www.kanzhun.com/search/?q={company}"
            resp = self.session.get(search_url, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")

            # 提取评分
            score_el = soup.select_one(".score-num, .rating-score, [class*='score']")
            score = None
            if score_el:
                score_text = score_el.get_text(strip=True)
                match = re.search(r'(\d+\.?\d*)', score_text)
                if match:
                    score = float(match.group(1))

            # 提取评价数
            review_count = 0
            review_el = soup.select_one("[class*='review-count'], [class*='comment-count']")
            if review_el:
                count_text = review_el.get_text(strip=True)
                match = re.search(r'(\d+)', count_text)
                if match:
                    review_count = int(match.group(1))

            return {"score": score, "reviews": review_count}
        except Exception:
            return None

    def _fetch_zhihu(self, company: str) -> Optional[str]:
        """知乎采集 — 搜索公司评价"""
        try:
            search_url = f"https://www.zhihu.com/search?type=content&q={company}+工作体验"
            resp = self.session.get(search_url, timeout=15,
                                   headers={"Referer": "https://www.zhihu.com"})
            soup = BeautifulSoup(resp.text, "lxml")
            # 提取搜索结果摘要
            summaries = []
            for item in soup.select(".RichText, .SearchItem-summary, [class*='summary']")[:5]:
                text = item.get_text(strip=True)[:200]
                if text:
                    summaries.append(text)
            return " | ".join(summaries) if summaries else None
        except Exception:
            return None

    def _fetch_niuke(self, company: str) -> Optional[dict]:
        """牛客网采集 — 面经评价"""
        try:
            search_url = f"https://www.nowcoder.com/search?type=post&query={company}+面经"
            resp = self.session.get(search_url, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")
            positive = 0
            total = 0
            for item in soup.select(".discuss-main, .post-item, [class*='post']")[:10]:
                text = item.get_text(strip=True)
                if text:
                    total += 1
                    if any(w in text for w in ["好评", "推荐", "不错", "很好", "值得", "nice"]):
                        positive += 1
            if total == 0:
                return None
            return {"positive_ratio": positive / total, "total_posts": total}
        except Exception:
            return None

    def _fetch_glassdoor(self, company: str) -> Optional[float]:
        """Glassdoor 评分 — 外资公司"""
        try:
            search_url = f"https://www.glassdoor.com/Search/results.htm?keyword={company}"
            resp = self.session.get(search_url, timeout=15,
                                   headers={"Accept-Language": "en-US,en;q=0.9"})
            soup = BeautifulSoup(resp.text, "lxml")
            score_el = soup.select_one("[class*='rating'], [class*='Rating']")
            if score_el:
                text = score_el.get_text(strip=True)
                match = re.search(r'(\d+\.?\d*)', text)
                if match:
                    return float(match.group(1))
            return None
        except Exception:
            return None

    def _is_foreign_company(self, company: str) -> bool:
        foreign_names = [
            "Goldman", "Morgan", "J.P.", "BlackRock", "Fidelity", "Bridgewater",
            "UBS", "HSBC", "Citi", "Point72", "Lazard", "Evercore", "Moelis",
        ]
        return any(n.lower() in company.lower() for n in foreign_names)

    def _merge_with_llm(self, company: str, results: dict) -> dict:
        """用 LLM 融合多平台数据为结构化口碑"""
        prompt = f"""你是口碑分析专家。请根据以下多平台采集数据，为公司 "{company}" 生成结构化口碑报告。

采集数据:
- 看准网: {results.get('kanzhun')}
- 知乎: {results.get('zhihu', '无数据')[:500]}
- 牛客网: {results.get('niuke')}
- Glassdoor: {results.get('glassdoor')}

请输出 JSON，格式要求:
{REPUTATION_SCHEMA}

规则:
- kanzhun_score: 直接使用看准网评分，无则为 null
- overall_sentiment: 综合所有平台评价，-1(极负面)到1(极正面)
- risk_flags: 提取所有风险信号（如"加班严重"、"管理混乱"、"裁员风险"、"薪资低于行业"）
- 用中文输出
"""
        try:
            result = self.llm.chat_json(
                [{"role": "user", "content": prompt}],
                system="你是口碑分析专家。只输出 JSON。",
                temperature=0.1,
            )
            return result
        except Exception:
            return {
                "overall_sentiment": 0,
                "risk_flags": [],
                "last_updated": datetime.now().isoformat(),
            }

    def close(self):
        self.session.close()
