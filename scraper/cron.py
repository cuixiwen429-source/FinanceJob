"""爬虫调度入口

定时任务 + 命令行手动触发。
用法:
    python -m scraper.cron                    # 全量爬取
    python -m scraper.cron --platform boss     # 单平台
    python -m scraper.cron --companies-only    # 仅爬官网
"""

import argparse
import sys
from datetime import datetime

from shared.db import FinanceJobDB
from scraper.platforms.company_careers import CompanyCareerScraper


def run_full_scrape():
    """全量爬取：腾讯文档 + 企业官网 + 第三方平台（待实现）"""
    db = FinanceJobDB()
    total = 0

    print(f"[{datetime.now().strftime('%H:%M:%S')}] FinanceJob 爬虫启动...")

    # 1. 腾讯文档实习 JD（当前主要数据源）
    print("  → 腾讯文档实习表...")
    try:
        from scraper.platforms.tencent_docs import TencentDocsImporter
        importer = TencentDocsImporter(db)
        result = importer.import_from_local_cache()
        print(f"    读取: {result['total']} 行 | 新增: {result['inserted']} | 跳过: {result['skipped']}")
        total += result["inserted"]
    except Exception as e:
        print(f"    腾讯文档导入出错: {e}")

    # 2. 企业官网爬取
    print("  → 金融企业官网爬取...")
    try:
        company_scraper = CompanyCareerScraper(db)
        n = company_scraper.run()
        print(f"    官网岗位: +{n}")
        total += n
        company_scraper.close()
    except Exception as e:
        print(f"    官网爬取出错: {e}")

    # 3. 第三方平台（Boss/猎聘/51job 等）
    # Phase 1 先聚焦前两个平台
    platform_names = ["boss", "liepin"]
    for pname in platform_names:
        print(f"  → {pname}...")
        try:
            # 每个平台的 run 方法会自行遍历关键词+城市
            # 实际实现需要在具体的 platform adapter 中完成
            print(f"    [{pname}] adapter 待实现")
        except Exception as e:
            print(f"    [{pname}] 出错: {e}")

    stats = db.get_stats()
    print(f"\n  完成! 总岗位: {total} 新增")
    print(f"  数据库状态: {stats}")
    db.close()


def run_companies_only():
    """仅爬取企业官网"""
    db = FinanceJobDB()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 官网爬取模式...")

    scraper = CompanyCareerScraper(db)
    n = scraper.run()
    print(f"  新增岗位: {n}")

    stats = db.get_stats()
    print(f"  数据库状态: {stats}")
    scraper.close()
    db.close()


def main():
    parser = argparse.ArgumentParser(description="FinanceJob 爬虫")
    parser.add_argument("--companies-only", action="store_true", help="仅爬取企业官网")
    parser.add_argument("--platform", type=str, help="指定单个平台")
    args = parser.parse_args()

    if args.companies_only:
        run_companies_only()
    else:
        run_full_scrape()


if __name__ == "__main__":
    main()
