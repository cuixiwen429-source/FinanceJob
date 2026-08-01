"""爬虫平台基类 — 统一接口 + 通用逻辑"""

import time
import random
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from shared.db import FinanceJobDB
from shared.config import get_search_strategy
from scraper.email_extractor import extract_recruiter_email, parse_salary_range, detect_remote


class BasePlatform(ABC):
    """招聘平台基类"""

    platform_name: str = "base"

    def __init__(self, db: FinanceJobDB):
        self.db = db
        self.strategy = get_search_strategy()

    @abstractmethod
    def search_jobs(self, keyword: str, city: str, page: int = 1) -> list[dict]:
        """搜索岗位，返回 dict 列表"""
        ...

    @abstractmethod
    def get_jd_detail(self, url: str) -> Optional[str]:
        """获取岗位详情页的 JD 文本"""
        ...

    def run(self, max_pages: int = 3) -> int:
        """执行完整爬取流程，返回新增岗位数"""
        count = 0
        for city in self.strategy.cities:
            for keyword in self.strategy.keywords:
                for page in range(1, max_pages + 1):
                    try:
                        jobs = self.search_jobs(keyword, city, page)
                        if not jobs:
                            break

                        for job_raw in jobs:
                            # 获取详细 JD
                            if job_raw.get("apply_url"):
                                jd_detail = self.get_jd_detail(job_raw["apply_url"])
                                if jd_detail:
                                    job_raw["jd_raw"] = jd_detail
                                    job_raw["jd_clean"] = jd_detail  # 暂时用原始

                                # 随机延迟
                                time.sleep(random.uniform(1.0, 3.0))

                            # 邮箱提取
                            full_text = f"{job_raw.get('jd_raw','')} {job_raw.get('company','')}"
                            job_raw["recruiter_email"] = extract_recruiter_email(full_text) or ""

                            # 薪资解析
                            salary = parse_salary_range(job_raw.get("salary_raw", ""))
                            if salary:
                                job_raw["salary_monthly_est"] = (salary[0] + salary[1]) / 2

                            # 远程检测
                            job_raw["is_remote"] = detect_remote(
                                f"{job_raw.get('title','')} {job_raw.get('jd_raw','')}"
                            )

                            # 填充字段
                            job_raw["platform"] = self.platform_name
                            job_raw["source_type"] = "platform"
                            job_raw["scraped_at"] = datetime.now().isoformat()
                            job_raw["status"] = "new"

                            # 去重后入库
                            if not self.db.is_duplicate(
                                self.platform_name, job_raw.get("company", ""), job_raw.get("title", "")
                            ):
                                job_id = self.db.insert_job(job_raw)
                                if job_id:
                                    count += 1

                        # 翻页间延迟
                        time.sleep(random.uniform(2.0, 5.0))

                    except Exception as e:
                        print(f"[{self.platform_name}] 搜索异常: {keyword}@{city} p{page} — {e}")
                        continue

        return count

    def close(self):
        """清理资源"""
        pass
