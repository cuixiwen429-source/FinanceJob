#!/usr/bin/env python3
"""Seed the SQLite DB from local Tencent Docs cache if empty, then start the dashboard API server."""
import os
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.chdir(ROOT)

from shared.db import FinanceJobDB


def seed_if_empty():
    db = FinanceJobDB()
    stats = db.get_stats()
    total = stats.get("total", 0)
    if total > 0:
        print(f"[seed] database already has {total} jobs, skipping import")
        db.close()
        return

    raw_path = ROOT / "data" / "tencent_docs_jobs_raw.json"
    if not raw_path.exists():
        print(f"[seed] warning: {raw_path} not found, starting with empty database")
        db.close()
        return

    print("[seed] database empty, importing Tencent Docs jobs from local cache...")
    try:
        from scraper.platforms.tencent_docs import TencentDocsImporter

        importer = TencentDocsImporter(db)
        result = importer.import_from_local_cache(str(raw_path))
        print(f"[seed] import result: {result}")
    except Exception as e:
        print(f"[seed] import failed: {e}")
    finally:
        db.close()


def main():
    seed_if_empty()
    print("[serve] starting FinanceJob dashboard API server...")
    from dashboard.api_server import main as api_main

    api_main()


if __name__ == "__main__":
    main()
