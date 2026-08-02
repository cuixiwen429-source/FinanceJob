"""FinanceJob API — clean job board backend"""
import json
import os
import sys
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from shared.db import FinanceJobDB

FILTER_COLUMNS = {
    "industry": "industry",
    "company_type": "company_type",
    "location": "location",
    "decision": "decision",
    "status": "status",
}

# v3: 新增 track 和 company_tier 多值筛选
MULTI_VALUE_FILTERS = {
    "track": "track",          # 多选，逗号分隔，精确匹配
    "company_tier": "company_tier",  # 多选，逗号分隔，精确匹配
}


class APIHandler(BaseHTTPRequestHandler):
    db: FinanceJobDB = None

    def _cors(self, status=200, ct="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", ct)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._cors(204, "text/plain")

    def _json(self, data):
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode())

    def _qs(self):
        """Parse query string into dict, values are strings (not lists)"""
        parsed = urlparse(self.path)
        raw = parse_qs(parsed.query)
        return {k: v[0] for k, v in raw.items()}

    # ── GET ──
    def do_GET(self):
        path = urlparse(self.path).path

        if path.startswith("/api/") or path == "/health":
            self._cors()
            try:
                if path == "/api/stats":
                    self._json(self.db.get_stats())
                elif path == "/api/jobs":
                    self._json(self._get_jobs_filtered())
                elif path == "/api/filters":
                    self._json(self._get_filter_options())
                elif path == "/health" or path == "/api/health":
                    self._json({"status": "ok", "version": "2.0"})
                else:
                    # /api/jobs/<id>
                    job_id = path.split("/")[-1]
                    if path.startswith("/api/jobs/") and job_id:
                        self._json(self._get_job_by_id(job_id))
                    else:
                        self._json({"error": "not found"})
            except Exception as e:
                self._json({"error": str(e)})
            return

        self._serve_static(path)

    def _get_jobs_filtered(self):
        qs = self._qs()
        conditions = []
        params = []

        # 原有的 LIKE 模糊筛选
        for qk, col in FILTER_COLUMNS.items():
            if qk in qs and qs[qk]:
                keywords = [v.strip() for v in qs[qk].split(",") if v.strip()]
                if keywords:
                    like_clauses = " OR ".join([f"{col} LIKE ?" for _ in keywords])
                    conditions.append(f"({like_clauses})")
                    params.extend([f"%{k}%" for k in keywords])

        # v3: track/company_tier 精确多选
        for qk, col in MULTI_VALUE_FILTERS.items():
            if qk in qs and qs[qk]:
                values = [v.strip() for v in qs[qk].split(",") if v.strip()]
                if values:
                    placeholders = ",".join(["?"] * len(values))
                    conditions.append(f"{col} IN ({placeholders})")
                    params.extend(values)

        if "remote" in qs:
            conditions.append("is_remote = 1")
        if "min_score" in qs:
            conditions.append("composite_score >= ?")
            params.append(float(qs["min_score"]))
        if "max_score" in qs:
            conditions.append("composite_score <= ?")
            params.append(float(qs["max_score"]))
        if "search" in qs and qs["search"]:
            kw = qs["search"]
            conditions.append(
                "(title LIKE ? OR company LIKE ? OR jd_clean LIKE ? OR industry LIKE ?)"
            )
            params.extend([f"%{kw}%"] * 4)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else "WHERE 1=1"

        limit = min(int(qs.get("limit", 50)), 200)
        offset = int(qs.get("offset", 0))
        order = qs.get("order", "composite_score DESC")
        allowed = {"composite_score DESC", "composite_score ASC", "salary_monthly_est DESC",
                   "scraped_at DESC", "company ASC", "job_match_score DESC",
                   "industry_match_score DESC", "salary_score DESC", "career_dev_score DESC",
                   "track ASC", "company_tier ASC", "track DESC", "company_tier DESC"}
        if order not in allowed:
            order = "composite_score DESC"

        sql = f"SELECT * FROM jobs {where} ORDER BY {order} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self.db.conn.execute(sql, params).fetchall()

        count_sql = f"SELECT COUNT(*) FROM jobs {where}"
        total = self.db.conn.execute(count_sql, params[:-2]).fetchone()[0]

        return {
            "jobs": [self._fmt(dict(r)) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def _get_filter_options(self):
        """Return distinct values for each filter column (v3: 包含 track 和 company_tier)"""
        options = {}
        for key, col in FILTER_COLUMNS.items():
            rows = self.db.conn.execute(
                f"SELECT DISTINCT {col} FROM jobs WHERE {col} != '' AND {col} IS NOT NULL ORDER BY {col}"
            ).fetchall()
            options[key] = [r[0] for r in rows]
        rows = self.db.conn.execute(
            "SELECT DISTINCT location FROM jobs WHERE location != '' AND location IS NOT NULL ORDER BY location"
        ).fetchall()
        options["location"] = [r[0] for r in rows]

        # v3: track 和 company_tier 选项
        track_rows = self.db.conn.execute(
            "SELECT DISTINCT track, track_label FROM jobs WHERE track != '' ORDER BY track"
        ).fetchall()
        options["track"] = [{"id": r[0], "label": r[1] or r[0]} for r in track_rows]

        tier_rows = self.db.conn.execute(
            "SELECT DISTINCT company_tier, company_tier_label FROM jobs WHERE company_tier != '' ORDER BY company_tier"
        ).fetchall()
        options["company_tier"] = [{"id": r[0], "label": r[1] or r[0]} for r in tier_rows]

        return options

    def _get_job_by_id(self, job_id):
        row = self.db.conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._fmt(dict(row)) if row else {"error": "not found"}

    def _fmt(self, d):
        for f in ["job_match_detail", "industry_match_detail", "salary_detail",
                   "career_dev_detail", "adjustments", "reputation"]:
            if d.get(f) and isinstance(d[f], str):
                try:
                    d[f] = json.loads(d[f])
                except Exception:
                    pass
        return d

    def _serve_static(self, path):
        base = Path(__file__).resolve().parent / "dist"
        if path == "/":
            target = base / "index.html"
        else:
            rel = unquote(path.lstrip("/"))
            target = base / rel
            if not target.exists() or target.is_dir():
                target = base / "index.html"
        if not target.exists():
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return
        ct, _ = mimetypes.guess_type(str(target))
        self.send_response(200)
        self.send_header("Content-Type", ct or "application/octet-stream")
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        with open(target, "rb") as f:
            self.wfile.write(f.read())

    # ── POST: AI Analysis ──
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        self._cors()
        try:
            if self.path == "/api/analyze":
                self._json(self._analyze_with_ai(body))
            else:
                self._json({"error": "not found"})
        except Exception as e:
            self._json({"error": str(e)})

    def _analyze_with_ai(self, data):
        job_id = data.get("job_id", "")
        row = self.db.conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return {"error": "job not found"}
        job = self._fmt(dict(row))

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            return {"error": "AI not configured (set DEEPSEEK_API_KEY in .env)"}

        # v3: 注入用户画像
        try:
            from shared.user_profile import get_profile
            profile = get_profile()
            user_context = profile.to_ai_context()
        except Exception:
            user_context = ""

        prompt = f"""你是一位资深金融职业导师。请基于用户画像分析以下实习岗位，从崔曦文的个人背景出发给出建议。

{user_context}

---
岗位：{job.get('title','')}
公司：{job.get('company','')}（{job.get('company_tier_label','') or job.get('company_tier','')}机构）
赛道：{job.get('track_label','') or job.get('track','')}
行业：{job.get('industry','')}
地点：{job.get('location','')}
薪资：{job.get('salary_raw','')}
JD：{job.get('jd_raw','')[:2000]}

请从崔曦文的背景出发（水利工程本科 -> 华师金融硕士 + 长江证券资本市场部实习），分析：
1. 这个岗位对他而言是否值得投递
2. 他的背景在这个岗位上的优劣势
3. 如果要投，准备重点是什么

返回 JSON：
{{
  "fit_score": 0-100,
  "pros": ["优势1", "优势2", "优势3"],
  "cons": ["劣势1"],
  "advice": "2-3句话建议（是否值得投递、准备重点、面试注意事项）",
  "salary_analysis": "薪资水平分析",
  "skill_gaps": ["需要补强的技能"],
  "company_brief": "公司一句话评价"
}}
"""

        import urllib.request

        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions",
            data=json.dumps({
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 1200,
            }).encode(),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"]
            # Strip markdown code fences if present
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content[:-3]
            return json.loads(content)

    def log_message(self, format, *args):
        pass


def main():
    db = FinanceJobDB()
    APIHandler.db = db
    port = int(os.getenv("PORT", "5175"))
    server = HTTPServer(("0.0.0.0", port), APIHandler)
    print(f"FinanceJob API -> http://0.0.0.0:{port}")
    print(f"   AI: {'enabled' if os.getenv('DEEPSEEK_API_KEY') else 'not configured'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        db.close()
        print("\nDone")


if __name__ == "__main__":
    main()
