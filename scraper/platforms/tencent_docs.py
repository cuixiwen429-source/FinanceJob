#!/usr/bin/env python3
"""腾讯文档在线表格实习 JD 导入器

支持两种模式:
1. 实时拉取: 传入腾讯文档在线表格 URL 或 file_id，通过 MCP 读取内容并导入
2. 本地缓存: 从项目 data/tencent_docs_jobs_raw.json 导入（默认）

用法:
    from scraper.platforms.tencent_docs import TencentDocsImporter
    importer = TencentDocsImporter(db)
    importer.import_from_local_cache()          # 从本地缓存导入
    importer.import_from_sheet("CZtmrcBwcOeh")  # 实时从云端导入
"""

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from shared.db import FinanceJobDB
from scraper.email_extractor import extract_recruiter_email, parse_salary_range, detect_remote


# Columns we care about (first 11 columns of the sheet)
SHEET_COLUMNS = [
    "公司", "类型", "行业", "录入时间", "申请截止",
    "岗位名称", "地点", "岗位描述", "岗位要求", "投递方式",
    "其他(薪资情况、实习证明等）",
]

# Path to the tencentdocs.py MCP helper (provided by WorkBuddy)
TENCENTDOCS_SCRIPT = Path(
    r"C:\Users\ChainsXes\AppData\Local\Programs\WorkBuddy\resources\app.asar.unpacked"
    r"\resources\builtin-plugins\tencent-docs-plugin\skills\tencent-docs\tencentdocs.py"
)


class TencentDocsImporter:
    """腾讯文档实习 JD 导入器"""

    platform_name = "tencent-docs-sheet"
    source_type = "tencent_docs_sheet"

    def __init__(self, db: FinanceJobDB, tencentdocs_script: Optional[Path] = None):
        self.db = db
        self.tencentdocs_script = tencentdocs_script or TENCENTDOCS_SCRIPT
        self._cells_per_request = 20000
        self._cols = len(SHEET_COLUMNS)
        self._batch_rows = self._cells_per_request // self._cols

    # ── 公共入口 ─────────────────────────────────────────────

    def import_from_local_cache(self, cache_path: Optional[Path] = None) -> dict:
        """从本地 JSON 缓存导入（默认 data/tencent_docs_jobs_raw.json）"""
        cache_path = cache_path or self._default_cache_path()
        if not cache_path.exists():
            raise FileNotFoundError(f"缓存文件不存在: {cache_path}")

        rows = json.loads(cache_path.read_text(encoding="utf-8"))
        return self._import_rows(rows)

    def import_from_sheet(self, file_id_or_url: str) -> dict:
        """实时从腾讯文档在线表格导入"""
        file_id = self._extract_file_id(file_id_or_url)
        sheet_info = self._get_sheet_info(file_id)
        sheet_id = sheet_info["sheets"][0]["sheet_id"]
        total_rows = sheet_info["sheets"][0]["row_count"]

        headers = self._fetch_header(file_id, sheet_id)
        rows = self._fetch_all_rows(file_id, sheet_id, headers, total_rows)
        return self._import_rows(rows)

    # ── MCP 调用 ─────────────────────────────────────────────

    def _tdoc_call(self, service: str, tool: str, args: dict) -> dict:
        """调用 tencentdocs.py 并返回解析后的业务 payload"""
        if not self.tencentdocs_script.exists():
            raise RuntimeError(f"腾讯文档 MCP 脚本不存在: {self.tencentdocs_script}")

        cmd = [
            sys.executable, str(self.tencentdocs_script),
            "tdoc_call", service, tool, json.dumps(args),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if result.returncode != 0:
            raise RuntimeError(f"MCP 调用失败 [{tool}]: {result.stderr}")

        data = json.loads(result.stdout)
        text = data["result"]["content"][0]["text"]
        return json.loads(text)

    def _get_sheet_info(self, file_id: str) -> dict:
        return self._tdoc_call("sheet-mcp", "get_sheet_info", {"file_id": file_id})

    def _fetch_header(self, file_id: str, sheet_id: str) -> list[str]:
        payload = self._tdoc_call(
            "sheet-mcp", "get_cell_data",
            {
                "file_id": file_id, "sheet_id": sheet_id,
                "start_row": 0, "end_row": 0,
                "start_col": 0, "end_col": self._cols - 1,
                "return_csv": False,
            }
        )
        headers = [""] * self._cols
        for cell in payload.get("cells", []):
            col = cell.get("col", 0)
            if 0 <= col < self._cols:
                headers[col] = self._cell_text(cell)
        # Fallback if header fetch is empty
        if not any(headers):
            headers = list(SHEET_COLUMNS)
        return headers

    def _fetch_all_rows(self, file_id: str, sheet_id: str, headers: list[str], total_rows: int) -> list[dict]:
        rows = []
        start = 1
        while start < total_rows:
            end = min(start + self._batch_rows - 1, total_rows - 1)
            print(f"  [TencentDocs] 读取行 {start}-{end}...")
            payload = self._tdoc_call(
                "sheet-mcp", "get_cell_data",
                {
                    "file_id": file_id, "sheet_id": sheet_id,
                    "start_row": start, "end_row": end,
                    "start_col": 0, "end_col": self._cols - 1,
                    "return_csv": False,
                }
            )
            cells = payload.get("cells", [])
            if not cells:
                break
            batch = self._cells_to_rows(cells, headers)
            if not batch:
                break
            rows.extend(batch)
            start = end + 1
        return rows

    @staticmethod
    def _cell_text(cell: dict) -> str:
        vt = cell.get("value_type", "")
        if vt == "STRING":
            return cell.get("string_value", "")
        if vt == "NUMBER":
            return str(cell.get("number_value", ""))
        return str(cell.get("string_value", cell.get("number_value", "")))

    @staticmethod
    def _cells_to_rows(cells: list[dict], headers: list[str]) -> list[dict]:
        rows_map = {}
        for cell in cells:
            row = cell.get("row", 0)
            col = cell.get("col", 0)
            if row not in rows_map:
                rows_map[row] = {}
            rows_map[row][col] = TencentDocsImporter._cell_text(cell)

        rows = []
        for row_idx in sorted(rows_map.keys()):
            if row_idx == 0:
                continue
            row_data = rows_map[row_idx]
            row = {}
            for col_idx, header in enumerate(headers):
                row[header] = row_data.get(col_idx, "")
            rows.append(row)
        return rows

    # ── 转换 & 入库 ──────────────────────────────────────────

    def _import_rows(self, rows: list[dict]) -> dict:
        inserted = 0
        skipped = 0
        empty = 0

        for row in rows:
            company = row.get("公司", "").strip()
            title = row.get("岗位名称", "").strip()
            if not company or not title:
                empty += 1
                continue

            job = self._transform_row(row)

            # Check duplicate by the actual unique constraint (platform, company, title)
            existing = self.db.conn.execute(
                "SELECT id FROM jobs WHERE platform = ? AND company = ? AND title = ?",
                (self.platform_name, job["company"], job["title"]),
            ).fetchone()
            if existing:
                skipped += 1
                continue

            job_id = self.db.insert_job(job)
            if job_id:
                inserted += 1
            else:
                skipped += 1

        return {
            "total": len(rows),
            "inserted": inserted,
            "skipped": skipped,
            "empty": empty,
        }

    def _transform_row(self, row: dict) -> dict:
        company = row.get("公司", "").strip()
        title = row.get("岗位名称", "").strip()
        industry = row.get("行业", "").strip()
        location_raw = row.get("地点", "").strip()
        other = row.get("其他(薪资情况、实习证明等）", "").strip()
        apply_method = row.get("投递方式", "").strip()
        jd_desc = row.get("岗位描述", "").strip()
        jd_req = row.get("岗位要求", "").strip()
        jd_raw = f"岗位描述:\n{jd_desc}\n\n岗位要求:\n{jd_req}" if jd_desc or jd_req else ""

        location, is_remote = self._normalize_location(location_raw)
        salary_raw = self._extract_salary(other, title)
        salary_monthly_est = None
        if salary_raw:
            parsed = parse_salary_range(salary_raw)
            if parsed:
                salary_monthly_est = (parsed[0] + parsed[1]) / 2

        email = extract_recruiter_email(f"{apply_method} {other}") or ""
        scraped_at = self._excel_serial_to_date(row.get("录入时间", ""))

        return {
            "platform": self.platform_name,
            "source_type": self.source_type,
            "title": title,
            "company": company,
            "company_type": self._normalize_company_type(industry, title, company),
            "industry": industry,
            "location": location,
            "is_remote": is_remote,
            "salary_raw": salary_raw,
            "salary_monthly_est": salary_monthly_est,
            "jd_raw": jd_raw,
            "jd_clean": jd_raw,
            "recruiter_email": email,
            "apply_url": apply_method,
            "scraped_at": scraped_at or datetime.now().isoformat(),
            "status": "new",
        }

    @staticmethod
    def _make_job_id(platform: str, company: str, title: str, apply_url: str) -> str:
        # Same logic as shared.db.insert_job for consistency
        raw = f"{platform}|{company}|{title}|{apply_url}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    @staticmethod
    def _extract_file_id(url_or_id: str) -> str:
        url_or_id = url_or_id.strip()
        if "/" not in url_or_id:
            return url_or_id
        m = re.search(r"/sheet/([A-Za-z0-9_-]+)", url_or_id)
        if m:
            return m.group(1)
        raise ValueError(f"无法从 URL 中提取 file_id: {url_or_id}")

    @staticmethod
    def _default_cache_path() -> Path:
        return Path(__file__).resolve().parent.parent.parent / "data" / "tencent_docs_jobs_raw.json"

    @staticmethod
    def _excel_serial_to_date(serial: str) -> str:
        try:
            days = float(serial)
        except (ValueError, TypeError):
            return ""
        if days <= 0:
            return ""
        dt = datetime(1899, 12, 30) + timedelta(days=days)
        return dt.strftime("%Y-%m-%d")

    @staticmethod
    def _normalize_company_type(industry: str, title: str, company: str) -> str:
        text = f"{industry} {title} {company}".lower()
        mapping = [
            ("量化", "量化私募"),
            ("私募", "PE/VC"),
            ("pe/vc", "PE/VC"),
            ("pe ", "PE/VC"),
            ("vc ", "PE/VC"),
            ("风险投资", "PE/VC"),
            ("fa", "精品投行"),
            ("精品投行", "精品投行"),
            ("券商", "券商"),
            ("证券", "券商"),
            ("公募", "公募基金"),
            ("基金", "公募基金"),
            ("保险", "保险"),
            ("信托", "AMC"),
            ("amc", "AMC"),
            ("银行", "银行"),
            ("战投", "互联网战投"),
            ("战略投资", "互联网战投"),
            ("硬科技", "硬科技VC"),
            ("外资", "外资买方"),
            ("评级", "评级/数据"),
            ("数据", "评级/数据"),
        ]
        for keyword, ctype in mapping:
            if keyword in text:
                return ctype
        return "其他"

    @staticmethod
    def _normalize_location(location: str) -> tuple[str, bool]:
        is_remote = detect_remote(location)
        loc = location
        for kw in ["支持 Remote 远程实习", "支持 Remote", "支持远程", "Remote", "远程", "线上"]:
            loc = loc.replace(kw, "")
        loc = loc.replace(" / ", " ").replace("/", " ").strip(" ,、")
        if not loc:
            loc = "全国" if is_remote else ""
        return loc, is_remote

    @staticmethod
    def _extract_salary(other: str, title: str) -> str:
        text = f"{other} {title}"
        patterns = [
            r"(\d{2,4})\s*[-～]\s*(\d{2,4})\s*元?\s*/\s*天",
            r"(\d{2,4})\s*元?\s*/\s*天",
            r"实习补贴\s*(\d{2,4})\s*元?\s*/\s*天",
            r"(\d{2,4})\s*元\s*日",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                return m.group(0)
        return ""


def main():
    """CLI entry for quick import testing"""
    import argparse
    parser = argparse.ArgumentParser(description="腾讯文档实习 JD 导入器")
    parser.add_argument("--cache", type=Path, help="本地缓存 JSON 路径")
    parser.add_argument("--sheet", type=str, help="腾讯文档 URL 或 file_id")
    args = parser.parse_args()

    db = FinanceJobDB()
    importer = TencentDocsImporter(db)

    if args.sheet:
        result = importer.import_from_sheet(args.sheet)
    else:
        result = importer.import_from_local_cache(args.cache)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    db.close()


if __name__ == "__main__":
    main()
