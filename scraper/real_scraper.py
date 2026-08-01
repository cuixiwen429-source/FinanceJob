"""真实岗位爬虫 — 抓取当前在线的金融实习岗位

平台:
  1. 实习僧 shixiseng.com — 最大实习平台
  2. 应届生求职网 yingjiesheng.com — 校招/实习
  3. 猎聘 liepin.com — 中高端+实习
  4. LinkedIn — 外资金融岗位
  5. 51job/智联 — 综合平台
"""

import re, json, time, random, hashlib
from datetime import datetime
from typing import Optional
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from bs4 import BeautifulSoup

from shared.db import FinanceJobDB
from scraper.email_extractor import extract_recruiter_email, parse_salary_range, detect_remote

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

db: FinanceJobDB = None

def make_id(platform, company, title, url=""):
    return hashlib.md5(f"{platform}|{company}|{title}|{url}".encode()).hexdigest()[:12]

def insert(platform, title, company, location, salary_raw, jd_raw, apply_url,
           source_type="platform", company_type=None, is_remote=False):
    """入库，去重"""
    if db.is_duplicate(platform, company, title):
        return False

    salary_monthly = None
    s = parse_salary_range(salary_raw)
    if s: salary_monthly = (s[0]+s[1])/2

    if not is_remote:
        is_remote = detect_remote(f"{title} {jd_raw}")

    recruiter = extract_recruiter_email(f"{jd_raw} {company}") or ""

    job = {
        "platform": platform, "source_type": source_type, "title": title,
        "company": company, "company_type": company_type, "location": location,
        "is_remote": is_remote, "salary_raw": salary_raw, "salary_monthly_est": salary_monthly,
        "jd_raw": jd_raw, "jd_clean": jd_raw, "recruiter_email": recruiter,
        "apply_url": apply_url, "scraped_at": datetime.now().isoformat(), "status": "new"
    }
    db.insert_job(job)
    return True

# ══════════════════════════════════════════════════════════
# 1. 实习僧 shixiseng.com
# ══════════════════════════════════════════════════════════

SHIXISENG_KEYWORDS = ["金融", "行研", "投行", "投资", "证券", "基金", "PE", "VC", "量化", "战投"]
SHIXISENG_CITIES = ["深圳", "上海", "全国"]

def scrape_shixiseng():
    """实习僧 — 最大实习平台，API直接返回JSON"""
    count = 0
    session = requests.Session()
    session.headers.update(HEADERS)

    for keyword in SHIXISENG_KEYWORDS:
        try:
            # 实习僧搜索API
            url = f"https://www.shixiseng.com/interns?keyword={keyword}&city=全国&type=intern"
            resp = session.get(url, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")

            # 提取岗位卡片
            cards = soup.select(".intern-wrap .intern-item, .job-list .job-item, [class*='intern'], [class*='job-card']")
            for card in cards[:15]:
                try:
                    title_el = card.select_one("a.title, .job-name, h3 a, [class*='title'] a")
                    company_el = card.select_one(".company-name, .company, [class*='company']")
                    salary_el = card.select_one(".salary, [class*='salary'], [class*='pay']")
                    location_el = card.select_one(".addr, .location, [class*='addr'], [class*='city']")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    salary = salary_el.get_text(strip=True) if salary_el else ""
                    location = location_el.get_text(strip=True) if location_el else ""
                    link = title_el.get("href","") if title_el else ""

                    if not title or not company: continue
                    if link and not link.startswith("http"):
                        link = "https://www.shixiseng.com" + link

                    # 尝试获取JD详情
                    jd_text = ""
                    if link:
                        try:
                            jd_resp = session.get(link, timeout=10)
                            jd_soup = BeautifulSoup(jd_resp.text, "lxml")
                            jd_el = jd_soup.select_one(".job-detail, .job_desc, [class*='detail'], [class*='desc'], [class*='content']")
                            if jd_el: jd_text = jd_el.get_text(strip=True)[:3000]
                        except: pass

                    if insert("实习僧", title, company, location, salary, jd_text, link,
                             company_type=_guess_type(title, company)):
                        count += 1
                    time.sleep(random.uniform(0.3, 0.8))
                except: continue
        except Exception as e:
            print(f"  [实习僧] {keyword}: {e}")
        time.sleep(random.uniform(1, 2))

    print(f"  [实习僧] +{count}")
    return count

# ══════════════════════════════════════════════════════════
# 2. 应届生求职网 yingjiesheng.com
# ══════════════════════════════════════════════════════════

def scrape_yingjiesheng():
    """应届生求职网"""
    count = 0
    session = requests.Session()
    session.headers.update(HEADERS)
    session.headers["Referer"] = "https://www.yingjiesheng.com/"

    search_urls = [
        "https://www.yingjiesheng.com/commsearch?keyword=金融实习&city=深圳",
        "https://www.yingjiesheng.com/commsearch?keyword=金融实习&city=上海",
        "https://www.yingjiesheng.com/commsearch?keyword=行研",
        "https://www.yingjiesheng.com/commsearch?keyword=证券",
    ]

    for url in search_urls:
        try:
            resp = session.get(url, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")

            items = soup.select(".job-item, .result-item, li, [class*='job'], [class*='result']")
            for item in items[:10]:
                try:
                    title_el = item.select_one("a[href*='job'], a[href*='com'], h3 a, .title a")
                    company_el = item.select_one(".company, .cname, [class*='company']")
                    if not title_el: continue

                    title = title_el.get_text(strip=True)
                    company = company_el.get_text(strip=True) if company_el else ""
                    link = title_el.get("href","")
                    if link and not link.startswith("http"):
                        link = "https://www.yingjiesheng.com" + link

                    if "金融" not in title and "行研" not in title and "证券" not in title and "投资" not in title:
                        continue

                    jd_text = ""
                    location, salary = "", ""
                    if link:
                        try:
                            jd_resp = session.get(link, timeout=10)
                            jd_soup = BeautifulSoup(jd_resp.text, "lxml")
                            jd_el = jd_soup.select_one(".job-detail, .job-info, [class*='detail'], [class*='content'], [class*='job']")
                            if jd_el: jd_text = jd_el.get_text(strip=True)[:3000]
                            loc_el = jd_soup.select_one(".addr, .location, [class*='addr']")
                            if loc_el: location = loc_el.get_text(strip=True)
                        except: pass

                    if insert("应届生求职网", title, company, location, salary, jd_text, link,
                             company_type=_guess_type(title, company)):
                        count += 1
                    time.sleep(random.uniform(0.3, 0.7))
                except: continue
        except Exception as e:
            print(f"  [应届生] {url}: {e}")
        time.sleep(random.uniform(1, 2))

    print(f"  [应届生] +{count}")
    return count

# ══════════════════════════════════════════════════════════
# 3. 猎聘 liepin.com
# ══════════════════════════════════════════════════════════

def scrape_liepin():
    """猎聘 — 金融实习"""
    count = 0
    session = requests.Session()
    session.headers.update(HEADERS)

    keywords = ["金融实习", "行研", "投行实习生", "PE投资", "量化研究"]
    cities = ["深圳", "上海"]

    for kw in keywords:
        for city in cities:
            try:
                url = f"https://www.liepin.com/zhaopin/?key={kw}&dqs={_city_code(city)}"
                resp = session.get(url, timeout=15)
                soup = BeautifulSoup(resp.text, "lxml")

                cards = soup.select(".job-list-item, .job-card, [class*='job'], [class*='card']")
                for card in cards[:12]:
                    try:
                        title_el = card.select_one("a[data-promid], .job-title a, h3 a, [class*='title'] a")
                        company_el = card.select_one(".company-name, .company, [class*='company']")
                        salary_el = card.select_one(".job-salary, .salary, [class*='salary']")
                        loc_el = card.select_one(".job-area, .location, [class*='area']")

                        if not title_el: continue
                        title = title_el.get_text(strip=True)
                        company = company_el.get_text(strip=True) if company_el else ""
                        salary = salary_el.get_text(strip=True) if salary_el else ""
                        location = loc_el.get_text(strip=True) if loc_el else city
                        link = title_el.get("href","")

                        if not link.startswith("http") and link:
                            link = "https://www.liepin.com" + link

                        jd_text = ""
                        if link:
                            try:
                                jd_resp = session.get(link, timeout=10,
                                    headers={"Referer":"https://www.liepin.com/"})
                                jd_soup = BeautifulSoup(jd_resp.text, "lxml")
                                jd_el = jd_soup.select_one(".job-description, .job-main-content, [class*='description'], [class*='content'], [class*='detail']")
                                if jd_el: jd_text = jd_el.get_text(strip=True)[:3000]
                            except: pass

                        if insert("猎聘", title, company, location, salary, jd_text, link,
                                 company_type=_guess_type(title, company)):
                            count += 1
                        time.sleep(random.uniform(0.5, 1.0))
                    except: continue
            except Exception as e:
                print(f"  [猎聘] {kw}@{city}: {e}")
            time.sleep(random.uniform(1.5, 3))

    print(f"  [猎聘] +{count}")
    return count

# ══════════════════════════════════════════════════════════
# 4. LinkedIn
# ══════════════════════════════════════════════════════════

def scrape_linkedin():
    """LinkedIn — 外资金融 + 国内金融"""
    count = 0
    session = requests.Session()
    session.headers.update(HEADERS)
    session.headers["Accept-Language"] = "en-US,en;q=0.9,zh-CN;q=0.8"

    keywords = ["investment intern China", "equity research intern China",
                "investment banking intern Shanghai", "PE intern Shenzhen",
                "quantitative intern Shanghai", "asset management intern China"]

    for kw in keywords:
        try:
            url = f"https://www.linkedin.com/jobs/search?keywords={kw.replace(' ','%20')}&f_TPR=r604800"
            resp = session.get(url, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")

            cards = soup.select(".job-search-card, .base-card, [class*='job-card'], [class*='result-card']")
            for card in cards[:10]:
                try:
                    title_el = card.select_one(".base-search-card__title, [class*='title'], h3")
                    company_el = card.select_one(".base-search-card__subtitle, [class*='company'], h4")
                    loc_el = card.select_one(".job-search-card__location, [class*='location']")
                    link_el = card.select_one("a.base-card__full-link, a[href*='jobs']")

                    if not title_el: continue
                    title = title_el.get_text(strip=True)
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = loc_el.get_text(strip=True) if loc_el else ""
                    link = link_el.get("href","") if link_el else ""

                    if link and link.startswith("/"): link = "https://www.linkedin.com" + link

                    jd_text = ""
                    if link:
                        try:
                            jd_resp = session.get(link, timeout=10)
                            jd_soup = BeautifulSoup(jd_resp.text, "lxml")
                            jd_el = jd_soup.select_one(".description__text, .show-more-less-html__markup, [class*='description']")
                            if jd_el: jd_text = jd_el.get_text(strip=True)[:3000]
                        except: pass

                    if insert("LinkedIn", title, company, location, "", jd_text, link,
                             company_type=_guess_type(title, company)):
                        count += 1
                    time.sleep(random.uniform(0.5, 1.0))
                except: continue
        except Exception as e:
            print(f"  [LinkedIn] {kw}: {e}")
        time.sleep(random.uniform(2, 3))

    print(f"  [LinkedIn] +{count}")
    return count

# ══════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════

def _city_code(city):
    return {"深圳":"050090","上海":"020020","北京":"010010"}.get(city,"")

def _guess_type(title, company):
    t = f"{title} {company}"
    if any(k in t for k in ["量化","Quant","quant"]): return "量化私募"
    if any(k in t for k in ["投行","IBD","IPO","并购","M&A"]): return "券商"
    if any(k in t for k in ["证券","券商","研究所"]): return "券商"
    if any(k in t for k in ["基金","Fund","Asset"]): return "公募基金"
    if any(k in t for k in ["PE","VC","投资","Capital","Venture"]): return "PE/VC"
    if any(k in t for k in ["银行","Bank"]): return "银行"
    if any(k in t for k in ["战投","战略"]): return "互联网战投"
    if any(k in t for k in ["保险","Insurance"]): return "保险"
    if any(k in t for k in ["评级","Wind","Bloomberg"]): return "评级/数据"
    return "券商"


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def run():
    global db
    db = FinanceJobDB()
    total = 0

    print("🕷️  FinanceJob 真实岗位爬虫启动...\n")

    scrapers = [
        ("实习僧", scrape_shixiseng),
        ("应届生求职网", scrape_yingjiesheng),
        ("猎聘", scrape_liepin),
        ("LinkedIn", scrape_linkedin),
    ]

    for name, fn in scrapers:
        print(f"  [{name}] 搜索中...")
        try:
            n = fn()
            total += n
        except Exception as e:
            print(f"  [{name}] 出错: {e}")

    # Show what we got
    stats = db.get_stats()
    print(f"\n✅ 爬取完成: +{total} 个新岗位")
    print(f"   数据库: {stats['total']} 总岗位, {stats['new']} 待评分")

    # Show latest
    rows = db.conn.execute(
        "SELECT platform,company,title,location,apply_url,recruiter_email FROM jobs ORDER BY scraped_at DESC LIMIT 15"
    ).fetchall()
    print("\n📋 最新岗位:")
    for r in rows:
        email_tag = "📧" if r["recruiter_email"] else "  "
        url_tag = "🔗" if r["apply_url"] else "  "
        print(f"  {email_tag}{url_tag} [{r['platform']}] {r['company']} — {r['title']} @{r['location']}")

    db.close()
    return total

if __name__ == "__main__":
    run()
