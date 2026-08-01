"""FinanceJob SQLite 数据库封装

WAL 模式，支持多进程并发读写。
存储: 岗位(jobs) + 公司口碑(company_reputation) + 发送日志(email_logs)
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from shared.config import DB_PATH


class FinanceJobDB:
    """SQLite WAL 模式数据库"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            source_type TEXT DEFAULT 'platform',
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            company_type TEXT,
            industry TEXT DEFAULT '',
            location TEXT DEFAULT '',
            is_remote INTEGER DEFAULT 0,
            salary_raw TEXT DEFAULT '',
            salary_monthly_est REAL,
            salary_annual_est REAL,
            jd_raw TEXT DEFAULT '',
            jd_clean TEXT DEFAULT '',
            recruiter_email TEXT DEFAULT '',
            apply_url TEXT DEFAULT '',
            scraped_at TEXT,

            -- scoring
            composite_score REAL DEFAULT 0,
            rank INTEGER DEFAULT 0,
            percentile REAL DEFAULT 0,
            decision TEXT,
            job_match_score REAL DEFAULT 0,
            job_match_detail TEXT DEFAULT '{}',
            industry_match_score REAL DEFAULT 0,
            industry_match_detail TEXT DEFAULT '{}',
            salary_score REAL DEFAULT 0,
            salary_detail TEXT DEFAULT '{}',
            career_dev_score REAL DEFAULT 0,
            career_dev_detail TEXT DEFAULT '{}',
            adjustments TEXT DEFAULT '[]',
            reputation TEXT,
            reasoning TEXT DEFAULT '',

            -- resume
            tailored_resume_path TEXT DEFAULT '',
            cover_letter TEXT DEFAULT '',

            -- status
            status TEXT DEFAULT 'new',
            sent_at TEXT,

            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
        CREATE INDEX IF NOT EXISTS idx_jobs_decision ON jobs(decision);
        CREATE INDEX IF NOT EXISTS idx_jobs_composite ON jobs(composite_score DESC);
        CREATE INDEX IF NOT EXISTS idx_jobs_platform ON jobs(platform);
        CREATE INDEX IF NOT EXISTS idx_jobs_company_type ON jobs(company_type);
        CREATE INDEX IF NOT EXISTS idx_jobs_is_remote ON jobs(is_remote);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_dedup ON jobs(platform, company, title);

        CREATE TABLE IF NOT EXISTS company_reputation (
            company TEXT PRIMARY KEY,
            kanzhun_score REAL,
            maimai_sentiment REAL,
            niuke_positive_ratio REAL,
            zhihu_summary TEXT,
            xiaohongshu_summary TEXT,
            glassdoor_score REAL,
            overall_sentiment REAL DEFAULT 0,
            risk_flags TEXT DEFAULT '[]',
            last_updated TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            recipient_email TEXT NOT NULL,
            subject TEXT,
            status TEXT DEFAULT 'pending',
            sent_at TEXT,
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );

        CREATE TABLE IF NOT EXISTS company_db (
            name TEXT PRIMARY KEY,
            company_type TEXT,
            career_url TEXT,
            ats_type TEXT DEFAULT 'custom',
            is_active INTEGER DEFAULT 1,
            last_scraped TEXT,
            notes TEXT
        );
        """)
        self.conn.commit()

    # ── Job CRUD ──────────────────────────────────────────

    def insert_job(self, job_dict: dict) -> Optional[str]:
        """插入岗位，已存在则跳过（幂等）"""
        import hashlib
        raw = f"{job_dict.get('platform','')}|{job_dict.get('company','')}|{job_dict.get('title','')}|{job_dict.get('apply_url','')}"
        job_id = hashlib.md5(raw.encode()).hexdigest()[:12]

        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO jobs (id, platform, source_type, title, company, company_type,
                    industry, location, is_remote, salary_raw, salary_monthly_est, salary_annual_est,
                    jd_raw, jd_clean, recruiter_email, apply_url, scraped_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                job_dict.get("platform", ""),
                job_dict.get("source_type", "platform"),
                job_dict.get("title", ""),
                job_dict.get("company", ""),
                job_dict.get("company_type"),
                job_dict.get("industry", ""),
                job_dict.get("location", ""),
                1 if job_dict.get("is_remote") else 0,
                job_dict.get("salary_raw", ""),
                job_dict.get("salary_monthly_est"),
                job_dict.get("salary_annual_est"),
                job_dict.get("jd_raw", ""),
                job_dict.get("jd_clean", ""),
                job_dict.get("recruiter_email", ""),
                job_dict.get("apply_url", ""),
                job_dict.get("scraped_at", datetime.now().isoformat()),
                job_dict.get("status", "new"),
            ))
            self.conn.commit()
            return job_id
        except Exception as e:
            return None

    def update_scores(self, job_id: str, score_data: dict):
        """更新评分数据"""
        self.conn.execute("""
            UPDATE jobs SET
                composite_score = ?, rank = ?, percentile = ?, decision = ?,
                job_match_score = ?, job_match_detail = ?,
                industry_match_score = ?, industry_match_detail = ?,
                salary_score = ?, salary_detail = ?,
                career_dev_score = ?, career_dev_detail = ?,
                adjustments = ?, reputation = ?, reasoning = ?,
                status = 'scored', updated_at = ?
            WHERE id = ?
        """, (
            score_data.get("composite_score", 0),
            score_data.get("rank", 0),
            score_data.get("percentile", 0),
            score_data.get("decision"),
            score_data.get("job_match_score", 0),
            json.dumps(score_data.get("job_match_detail", {}), ensure_ascii=False),
            score_data.get("industry_match_score", 0),
            json.dumps(score_data.get("industry_match_detail", {}), ensure_ascii=False),
            score_data.get("salary_score", 0),
            json.dumps(score_data.get("salary_detail", {}), ensure_ascii=False),
            score_data.get("career_dev_score", 0),
            json.dumps(score_data.get("career_dev_detail", {}), ensure_ascii=False),
            json.dumps(score_data.get("adjustments", []), ensure_ascii=False),
            json.dumps(score_data.get("reputation"), ensure_ascii=False) if score_data.get("reputation") else None,
            score_data.get("reasoning", ""),
            datetime.now().isoformat(),
            job_id,
        ))
        self.conn.commit()

    def get_new_jobs(self, limit: int = 100) -> list[dict]:
        """获取待评分的新岗位"""
        rows = self.conn.execute(
            "SELECT * FROM jobs WHERE status = 'new' ORDER BY scraped_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_scored_jobs(self, decision: Optional[str] = None, limit: int = 50) -> list[dict]:
        """获取已评分的岗位"""
        if decision:
            rows = self.conn.execute(
                "SELECT * FROM jobs WHERE status = 'scored' AND decision = ? ORDER BY composite_score DESC LIMIT ?",
                (decision, limit)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM jobs WHERE status = 'scored' ORDER BY composite_score DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_jobs_by_status(self, status: str, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
            (status, limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def update_status(self, job_id: str, status: str):
        self.conn.execute(
            "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(), job_id)
        )
        self.conn.commit()

    # ── 去重 ──────────────────────────────────────────────

    def is_duplicate(self, platform: str, company: str, title: str) -> bool:
        row = self.conn.execute(
            "SELECT id FROM jobs WHERE platform = ? AND company = ? AND title = ?",
            (platform, company, title)
        ).fetchone()
        return row is not None

    def is_email_sent_recently(self, email: str, days: int = 7) -> bool:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        row = self.conn.execute(
            "SELECT id FROM email_logs WHERE recipient_email = ? AND sent_at > ?",
            (email, cutoff)
        ).fetchone()
        return row is not None

    # ── 公司口碑 ──────────────────────────────────────────

    def upsert_reputation(self, company: str, rep_data: dict):
        self.conn.execute("""
            INSERT OR REPLACE INTO company_reputation
                (company, kanzhun_score, maimai_sentiment, niuke_positive_ratio,
                 zhihu_summary, xiaohongshu_summary, glassdoor_score,
                 overall_sentiment, risk_flags, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company,
            rep_data.get("kanzhun_score"),
            rep_data.get("maimai_sentiment"),
            rep_data.get("niuke_positive_ratio"),
            rep_data.get("zhihu_summary"),
            rep_data.get("xiaohongshu_summary"),
            rep_data.get("glassdoor_score"),
            rep_data.get("overall_sentiment", 0),
            json.dumps(rep_data.get("risk_flags", []), ensure_ascii=False),
            datetime.now().isoformat(),
        ))
        self.conn.commit()

    def get_reputation(self, company: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM company_reputation WHERE company = ?", (company,)
        ).fetchone()
        return dict(row) if row else None

    # ── 邮件日志 ──────────────────────────────────────────

    def log_email(self, job_id: str, recipient: str, subject: str, status: str = "pending",
                  error: Optional[str] = None):
        self.conn.execute("""
            INSERT INTO email_logs (job_id, recipient_email, subject, status, sent_at, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (job_id, recipient, subject, status, datetime.now().isoformat() if status == "sent" else None, error))
        self.conn.commit()

    # ── 公司库 ────────────────────────────────────────────

    def get_active_companies(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM company_db WHERE is_active = 1"
        ).fetchall()
        return [dict(r) for r in rows]

    def insert_company(self, name: str, company_type: str, career_url: str,
                       ats_type: str = "custom"):
        self.conn.execute("""
            INSERT OR IGNORE INTO company_db (name, company_type, career_url, ats_type)
            VALUES (?, ?, ?, ?)
        """, (name, company_type, career_url, ats_type))
        self.conn.commit()

    # ── 统计 ──────────────────────────────────────────────

    def get_stats(self) -> dict:
        """获取仪表盘统计数据"""
        total = self.conn.execute("SELECT COUNT(*) as c FROM jobs").fetchone()["c"]
        new_count = self.conn.execute("SELECT COUNT(*) as c FROM jobs WHERE status='new'").fetchone()["c"]
        scored = self.conn.execute("SELECT COUNT(*) as c FROM jobs WHERE status='scored'").fetchone()["c"]
        applied = self.conn.execute("SELECT COUNT(*) as c FROM jobs WHERE status IN ('applied','resume_ready')").fetchone()["c"]
        replied = self.conn.execute("SELECT COUNT(*) as c FROM jobs WHERE status='replied'").fetchone()["c"]
        interview = self.conn.execute("SELECT COUNT(*) as c FROM jobs WHERE status='interview'").fetchone()["c"]
        offer = self.conn.execute("SELECT COUNT(*) as c FROM jobs WHERE status='offer'").fetchone()["c"]

        strong = self.conn.execute("SELECT COUNT(*) as c FROM jobs WHERE decision='强烈推荐'").fetchone()["c"]
        recommend = self.conn.execute("SELECT COUNT(*) as c FROM jobs WHERE decision='推荐投递'").fetchone()["c"]

        return {
            "total": total, "new": new_count, "scored": scored,
            "applied": applied, "replied": replied, "interview": interview,
            "offer": offer,
            "strong_recommend": strong, "recommend": recommend,
        }

    def close(self):
        self.conn.close()
