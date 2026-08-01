"""★ 金融企业官网招聘页面爬取器

三级策略：
  1) ATS API 反向工程 (Greenhouse/Lever/Workday)
  2) 自建招聘页面 DOM 提取
  3) 通用 HTML 解析 + LLM 提取
"""

import re
import json
import time
import random
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from shared.db import FinanceJobDB
from scraper.email_extractor import extract_recruiter_email, parse_salary_range, detect_remote


# ── ATS 检测 + API 适配 ─────────────────────────────────

def detect_ats_type(html: str, url: str) -> str:
    """检测页面使用的 ATS 类型"""
    html_lower = html.lower()
    url_lower = url.lower()

    if "greenhouse.io" in url_lower or "grnhse" in html_lower or "greenhouse" in html_lower:
        return "greenhouse"
    if "lever.co" in url_lower or "lever" in html_lower:
        return "lever"
    if "workday" in url_lower or "myworkdayjobs" in url_lower:
        return "workday"
    if "taleo" in url_lower:
        return "taleo"
    if "zhaopin" in url_lower or "career" in url_lower or "jobs" in url_lower:
        return "custom"
    return "unknown"


def fetch_greenhouse_jobs(board_token: str) -> list[dict]:
    """从 Greenhouse API 获取岗位"""
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    try:
        resp = requests.get(url, params={"content": "true"}, timeout=30,
                          headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        jobs = []
        for item in data.get("jobs", []):
            jobs.append({
                "title": item.get("title", ""),
                "company": item.get("company_name", ""),
                "location": item.get("location", {}).get("name", ""),
                "jd_raw": item.get("content", ""),
                "apply_url": item.get("absolute_url", ""),
                "salary_raw": "",
            })
        return jobs
    except Exception:
        return []


def fetch_lever_jobs(company_slug: str) -> list[dict]:
    """从 Lever API 获取岗位"""
    url = f"https://api.lever.co/v0/postings/{company_slug}"
    try:
        resp = requests.get(url, params={"mode": "json"}, timeout=30,
                          headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        jobs = []
        for item in data:
            jobs.append({
                "title": item.get("text", ""),
                "company": company_slug.replace("-", " ").title(),
                "location": item.get("categories", {}).get("location", ""),
                "jd_raw": item.get("descriptionPlain", item.get("description", "")),
                "apply_url": item.get("applyUrl", item.get("hostedUrl", "")),
                "salary_raw": "",
            })
        return jobs
    except Exception:
        return []


# ── 通用 HTML 解析 ──────────────────────────────────────

def fetch_custom_careers(url: str) -> list[dict]:
    """通用企业招聘页面解析（中国金融企业通常使用自建页面）"""
    try:
        resp = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        resp.encoding = resp.apparent_encoding or "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")

        jobs = []

        # 常见的岗位列表容器
        job_selectors = [
            ".job-list li", ".job-item", ".position-item",
            ".career-list li", ".recruit-list li", ".post-list li",
            "table.job-table tr", ".job-card",
            "[class*='job']", "[class*='position']", "[class*='career']",
        ]

        for selector in job_selectors:
            items = soup.select(selector)
            if len(items) >= 2:
                for item in items:
                    title_el = (item.select_one("a") or
                               item.select_one("h3") or
                               item.select_one("h4") or
                               item.select_one(".title"))
                    if not title_el:
                        continue

                    title = title_el.get_text(strip=True)
                    link = title_el.get("href", "") if title_el.name == "a" else ""

                    # 过滤非岗位链接
                    if len(title) < 3 or len(title) > 60:
                        continue

                    jobs.append({
                        "title": title,
                        "apply_url": link if link.startswith("http") else (url.rstrip("/") + "/" + link.lstrip("/")) if link else url,
                        "location": "",
                        "jd_raw": "",
                        "salary_raw": "",
                    })
                break

        return jobs

    except Exception as e:
        return []


# ── 公司库 ──────────────────────────────────────────────

FINANCE_COMPANIES = [
    # ===== 券商 =====
    {"name": "中信证券", "type": "券商", "url": "https://www.citics.com/careers", "ats": "custom"},
    {"name": "中金公司", "type": "券商", "url": "https://career.cicc.com/", "ats": "custom"},
    {"name": "华泰证券", "type": "券商", "url": "https://www.htsc.com.cn/careers", "ats": "custom"},
    {"name": "国泰君安", "type": "券商", "url": "https://www.gtja.com/careers", "ats": "custom"},
    {"name": "中信建投", "type": "券商", "url": "https://www.csc.com.cn/careers", "ats": "custom"},
    {"name": "招商证券", "type": "券商", "url": "https://www.cmschina.com/careers", "ats": "custom"},
    {"name": "广发证券", "type": "券商", "url": "https://www.gf.com.cn/careers", "ats": "custom"},
    {"name": "国信证券", "type": "券商", "url": "https://www.guosen.com.cn/careers", "ats": "custom"},
    {"name": "东方证券", "type": "券商", "url": "https://www.dfzq.com.cn/careers", "ats": "custom"},

    # ===== 精品投行/FA =====
    {"name": "华兴资本", "type": "精品投行", "url": "https://www.huaxing.com/careers", "ats": "custom"},
    {"name": "泰合资本", "type": "精品投行", "url": "https://www.taihecap.com", "ats": "custom"},
    {"name": "光源资本", "type": "精品投行", "url": "https://www.lighthousecap.cn", "ats": "custom"},

    # ===== 公募基金 =====
    {"name": "易方达基金", "type": "公募基金", "url": "https://www.efunds.com.cn/careers", "ats": "custom"},
    {"name": "华夏基金", "type": "公募基金", "url": "https://www.chinaamc.com/careers", "ats": "custom"},
    {"name": "南方基金", "type": "公募基金", "url": "https://www.southernfund.com/careers", "ats": "custom"},
    {"name": "嘉实基金", "type": "公募基金", "url": "https://www.jsfund.cn/careers", "ats": "custom"},

    # ===== 量化私募 =====
    {"name": "幻方量化", "type": "量化私募", "url": "https://www.high-flyer.cn/careers", "ats": "custom"},
    {"name": "九坤投资", "type": "量化私募", "url": "https://www.ubiquant.com/careers", "ats": "custom"},
    {"name": "明汯投资", "type": "量化私募", "url": "https://www.mhfunds.com/careers", "ats": "custom"},

    # ===== PE/VC =====
    {"name": "高瓴资本", "type": "PE/VC", "url": "https://www.hillhousecap.com/careers", "ats": "custom"},
    {"name": "红杉中国", "type": "PE/VC", "url": "https://www.sequoiacap.com/china/careers", "ats": "greenhouse"},
    {"name": "IDG资本", "type": "PE/VC", "url": "https://www.idgcapital.com/careers", "ats": "custom"},
    {"name": "经纬中国", "type": "PE/VC", "url": "https://www.matrixpartners.com.cn/careers", "ats": "custom"},
    {"name": "深创投", "type": "PE/VC", "url": "https://www.szvc.com.cn/careers", "ats": "custom"},

    # ===== 硬科技 VC =====
    {"name": "中芯聚源", "type": "硬科技VC", "url": "https://www.smic-capital.com", "ats": "custom"},
    {"name": "中科创星", "type": "硬科技VC", "url": "https://www.casstarchain.com/careers", "ats": "custom"},

    # ===== 互联网战投 =====
    {"name": "腾讯", "type": "互联网战投", "url": "https://careers.tencent.com", "ats": "custom"},
    {"name": "字节跳动", "type": "互联网战投", "url": "https://jobs.bytedance.com", "ats": "custom"},
    {"name": "阿里巴巴", "type": "互联网战投", "url": "https://talent.alibaba.com", "ats": "custom"},
    {"name": "美团", "type": "互联网战投", "url": "https://zhaopin.meituan.com", "ats": "custom"},
    {"name": "小红书", "type": "互联网战投", "url": "https://www.xiaohongshu.com/careers", "ats": "custom"},
    {"name": "蚂蚁集团", "type": "互联网战投", "url": "https://talent.antgroup.com", "ats": "custom"},
    {"name": "京东", "type": "互联网战投", "url": "https://zhaopin.jd.com", "ats": "custom"},
    {"name": "快手", "type": "互联网战投", "url": "https://zhaopin.kuaishou.cn", "ats": "custom"},
    {"name": "大疆", "type": "互联网战投", "url": "https://we.dji.com", "ats": "custom"},

    # ===== 银行 =====
    {"name": "招商银行", "type": "银行", "url": "https://career.cmbchina.com", "ats": "custom"},
    {"name": "平安银行", "type": "银行", "url": "https://talent.pingan.com", "ats": "custom"},
    {"name": "微众银行", "type": "银行", "url": "https://www.webank.com/careers", "ats": "custom"},

    # ===== 保险/AMC =====
    {"name": "平安集团", "type": "保险", "url": "https://talent.pingan.com", "ats": "custom"},
    {"name": "泰康资产", "type": "保险", "url": "https://www.taikangasset.com.cn", "ats": "custom"},

    # ===== 外资投行 =====
    {"name": "Goldman Sachs", "type": "外资投行", "url": "https://www.goldmansachs.com/careers", "ats": "workday"},
    {"name": "Morgan Stanley", "type": "外资投行", "url": "https://www.morganstanley.com/careers", "ats": "workday"},
    {"name": "J.P. Morgan", "type": "外资投行", "url": "https://careers.jpmorgan.com", "ats": "taleo"},

    # ===== 外资买方 =====
    {"name": "BlackRock", "type": "外资买方", "url": "https://careers.blackrock.com", "ats": "workday"},
    {"name": "Fidelity", "type": "外资买方", "url": "https://careers.fidelity.com", "ats": "workday"},

    # ===== 评级/数据 =====
    {"name": "万得 Wind", "type": "评级/数据", "url": "https://www.wind.com.cn/careers", "ats": "custom"},
    {"name": "东方财富", "type": "评级/数据", "url": "https://www.eastmoney.com/careers", "ats": "custom"},
    {"name": "同花顺", "type": "评级/数据", "url": "https://www.10jqka.com.cn", "ats": "custom"},
]


class CompanyCareerScraper:
    """金融企业官网招聘页面爬取器"""

    def __init__(self, db: FinanceJobDB):
        self.db = db
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        })

    def seed_companies(self):
        """首次启动时将公司库写入 DB"""
        for c in FINANCE_COMPANIES:
            self.db.insert_company(c["name"], c["type"], c["url"], c["ats"])
        print(f"[公司库] 已入库 {len(FINANCE_COMPANIES)} 家企业")

    def run(self) -> int:
        """遍历所有公司，爬取官网招聘页面"""
        companies = self.db.get_active_companies()
        if not companies:
            self.seed_companies()
            companies = self.db.get_active_companies()

        total_jobs = 0

        for company in companies:
            try:
                name = company["name"]
                url = company["career_url"]
                ats = company["ats_type"]

                jobs = []
                if ats == "greenhouse":
                    # 尝试从 URL 提取 board token
                    token = self._extract_greenhouse_token(url)
                    if token:
                        jobs = fetch_greenhouse_jobs(token)
                elif ats == "lever":
                    slug = self._extract_lever_slug(url)
                    if slug:
                        jobs = fetch_lever_jobs(slug)
                else:
                    jobs = fetch_custom_careers(url)

                # 入库
                for job in jobs:
                    job["platform"] = f"官网-{name}"
                    job["source_type"] = "company_careers"
                    job["company"] = name
                    job["company_type"] = company["company_type"]
                    job["scraped_at"] = datetime.now().isoformat()
                    job["status"] = "new"

                    # 邮箱提取
                    full_text = f"{job.get('jd_raw','')} {name}"
                    job["recruiter_email"] = extract_recruiter_email(full_text) or ""

                    # 薪资解析
                    salary = parse_salary_range(job.get("salary_raw", ""))
                    if salary:
                        job["salary_monthly_est"] = (salary[0] + salary[1]) / 2

                    # 远程检测
                    job["is_remote"] = detect_remote(
                        f"{job.get('title','')} {job.get('jd_raw','')}"
                    )

                    # 去重
                    if not self.db.is_duplicate(job["platform"], name, job.get("title", "")):
                        job_id = self.db.insert_job(job)
                        if job_id:
                            total_jobs += 1

                # 友好延迟
                time.sleep(random.uniform(1.0, 3.0))

            except Exception as e:
                print(f"[官网爬取] {company.get('name', '?')} 失败: {e}")
                continue

        return total_jobs

    def _extract_greenhouse_token(self, url: str) -> Optional[str]:
        """从 URL 中提取 Greenhouse board token"""
        m = re.search(r'greenhouse\.io/([^/]+)', url)
        return m.group(1) if m else None

    def _extract_lever_slug(self, url: str) -> Optional[str]:
        """从 URL 提取 Lever company slug"""
        m = re.search(r'lever\.co/([^/]+)', url)
        return m.group(1) if m else None

    def close(self):
        self.session.close()
