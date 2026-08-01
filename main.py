#!/usr/bin/env python3
"""FinanceJob — 金融求职全自动投递系统

一键全流程:
    python main.py full

分步执行:
    python main.py scan     # 全网爬取
    python main.py score    # 科学评分
    python main.py tailor   # 简历定制
    python main.py send     # 邮件投递
    python main.py status   # 查看进度
"""

import sys
import argparse
from datetime import datetime

from shared.db import FinanceJobDB
from shared.config import UserConfig


def cmd_scan():
    """全网爬取岗位"""
    print(f"\n{'='*60}")
    print(f"  FinanceJob · 全网岗位爬取")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    from scraper.cron import run_full_scrape
    run_full_scrape()
    sys.stdout.flush()


def cmd_score(args=None):
    """科学评分 + 口碑采集"""
    print(f"\n{'='*60}")
    print(f"  FinanceJob · 四维科学评分")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    from scoring_engine.pipeline import ScoringPipeline
    db = FinanceJobDB()
    pipeline = ScoringPipeline(db)

    score_kwargs = {}
    if args:
        score_kwargs["limit"] = args.score_limit
        score_kwargs["use_llm"] = not args.score_no_llm
        score_kwargs["skip_reputation"] = args.score_skip_reputation

    results = pipeline.score_all_new(**score_kwargs)

    if results:
        print(f"\n  ★ 综合评分 TOP 5:")
        for i, r in enumerate(sorted(results, key=lambda x: x["total"], reverse=True)[:5], 1):
            print(f"  {i}. [{r['decision']}] {r['company']} — {r['title']} ({r['total']:.1f}分)")

    db.close()


def cmd_tailor():
    """简历定制"""
    print(f"\n{'='*60}")
    print(f"  FinanceJob · AI 简历定制")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    from resume_engine.pipeline import run_resume_pipeline
    run_resume_pipeline()


def cmd_send():
    """邮件投递"""
    print(f"\n{'='*60}")
    print(f"  FinanceJob · 邮件投递")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    config = UserConfig.load()
    if not config.email_auth_code:
        print("  ⚠ 未配置邮箱，生成 .eml 草稿模式...")
        from email_sender.sender import EmailSender
        db = FinanceJobDB()
        sender = EmailSender(db, config)
        sender.send_all(draft_only=True)
        db.close()
    else:
        from email_sender.sender import EmailSender
        db = FinanceJobDB()
        sender = EmailSender(db, config)
        sender.send_all()
        db.close()


def cmd_import_tencent_docs():
    """从腾讯文档导入实习 JD"""
    print(f"\n{'='*60}")
    print(f"  FinanceJob · 腾讯文档 JD 导入")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    from scraper.platforms.tencent_docs import TencentDocsImporter
    db = FinanceJobDB()
    importer = TencentDocsImporter(db)
    result = importer.import_from_local_cache()

    print(f"  读取: {result['total']} 行")
    print(f"  新增: {result['inserted']}")
    print(f"  去重跳过: {result['skipped']}")
    print(f"  空行: {result['empty']}")

    stats = db.get_stats()
    print(f"\n  数据库总岗位: {stats['total']}")
    db.close()


def cmd_status():
    """查看进度"""
    db = FinanceJobDB()
    stats = db.get_stats()

    print(f"\n{'='*50}")
    print(f"  FinanceJob · 求职进度看板")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    print(f"  总岗位: {stats['total']}")
    print(f"  待评分: {stats['new']}")
    print(f"  已评分: {stats['scored']}")
    print(f"  已投递: {stats['applied']}")
    print(f"  已回复: {stats['replied']}")
    print(f"  面试中: {stats['interview']}")
    print(f"  Offer:  {stats['offer']}")
    print(f"\n  强烈推荐: {stats['strong_recommend']}")
    print(f"  推荐投递: {stats['recommend']}")

    # 显示高分岗位
    rows = db.conn.execute(
        """SELECT company, title, composite_score, decision, location, is_remote
           FROM jobs WHERE status='scored'
           ORDER BY composite_score DESC LIMIT 8"""
    ).fetchall()

    if rows:
        print(f"\n  ★ 高分岗位:")
        for r in rows:
            remote_tag = "🌐远程" if r["is_remote"] else r["location"]
            print(f"  [{r['decision']}] {r['company']} — {r['title']} "
                  f"({r['composite_score']:.0f}分) {remote_tag}")

    # 投递统计
    sent_count = db.conn.execute(
        "SELECT COUNT(*) as c FROM email_logs WHERE status='sent'"
    ).fetchone()["c"]
    draft_count = db.conn.execute(
        "SELECT COUNT(*) as c FROM email_logs WHERE status='draft'"
    ).fetchone()["c"]
    print(f"\n  已发送邮件: {sent_count} | 草稿: {draft_count}")

    db.close()


def cmd_full():
    """一键全流程"""
    cmd_scan()
    cmd_score(args=None)
    cmd_tailor()
    cmd_send()
    cmd_status()


def main():
    parser = argparse.ArgumentParser(
        description="FinanceJob — 金融求职全自动投递系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py full                一键全流程
  python main.py scan                全网爬取岗位
  python main.py import-tencent-docs 从腾讯文档导入实习JD
  python main.py score               科学评分+排序
  python main.py tailor              AI简历定制
  python main.py send                邮件投递
  python main.py status              查看进度
        """,
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="status",
        choices=["full", "scan", "score", "tailor", "send", "status", "import-tencent-docs"],
        help="执行命令",
    )
    parser.add_argument(
        "--score-limit", type=int, default=200,
        help="评分模式: 最多评分岗位数（默认200）",
    )
    parser.add_argument(
        "--score-no-llm", action="store_true",
        help="评分模式: 使用规则快速评分，不调用LLM",
    )
    parser.add_argument(
        "--score-skip-reputation", action="store_true",
        help="评分模式: 跳过口碑采集",
    )
    args = parser.parse_args()

    commands = {
        "full": lambda: cmd_full(),
        "scan": cmd_scan,
        "score": lambda: cmd_score(args),
        "tailor": cmd_tailor,
        "send": cmd_send,
        "status": cmd_status,
        "import-tencent-docs": cmd_import_tencent_docs,
    }

    commands[args.command]()


if __name__ == "__main__":
    main()
