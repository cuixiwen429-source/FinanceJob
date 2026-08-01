"""FinanceJob API Server — QQ邮箱版"""
import json, os, sys, smtplib, mimetypes
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import Header
from email.utils import formataddr
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from shared.db import FinanceJobDB

def get_email_config():
    return {
        "address": os.getenv("EMAIL_ADDRESS", ""),
        "smtp": os.getenv("EMAIL_SMTP", "smtp.qq.com"),
        "port": int(os.getenv("EMAIL_PORT", "465")),
        "provider": os.getenv("EMAIL_PROVIDER", "qq"),
        "connected": bool(os.getenv("EMAIL_ADDRESS") and os.getenv("EMAIL_AUTH_CODE")),
        "auth_code_set": bool(os.getenv("EMAIL_AUTH_CODE")),
        "daily_limit": 400,
        "rate_per_min": 10,
    }

class APIHandler(BaseHTTPRequestHandler):
    db: FinanceJobDB = None

    def _cors(self, status=200, content_type="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._cors(204, "text/plain")

    def _json(self, data):
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))

    # ── GET ──
    def do_GET(self):
        path = self.path.split("?")[0]

        # API routes
        if path.startswith("/api/") or path == "/health":
            self._cors()
            try:
                if path == "/api/stats":              self._json(self.db.get_stats())
                elif path == "/api/jobs":             self._json(self._get_jobs())
                elif path == "/api/jobs/scored":      self._json(self._get_jobs("scored", 50))
                elif path == "/api/jobs/high-priority": self._json(self._get_jobs(None, 20, "WHERE decision IN ('强烈推荐','推荐投递')"))
                elif path == "/api/reputation":       self._json(self._get_reputation())
                elif path == "/api/email-logs":       self._json(self._get_email_logs())
                elif path == "/api/companies":        self._json(self._get_companies())
                elif path == "/api/email-config":     self._json(get_email_config())
                elif path == "/health":               self._json({"status":"ok","version":"1.0"})
                else:                                 self._json({"error":"not found"})
            except Exception as e:
                self._json({"error": str(e)})
            return

        # Static files
        self._serve_static(path)

    def _get_jobs(self, status=None, limit=100, extra_where=""):
        where = f"WHERE status='{status}'" if status else extra_where if extra_where else "WHERE 1=1"
        sql = f"SELECT * FROM jobs {where} ORDER BY composite_score DESC LIMIT {limit}"
        rows = self.db.conn.execute(sql).fetchall()
        return [self._format_job(dict(r)) for r in rows]

    def _format_job(self, d):
        for f in ["job_match_detail","industry_match_detail","salary_detail","career_dev_detail","adjustments","reputation"]:
            if d.get(f) and isinstance(d[f], str):
                try: d[f] = json.loads(d[f])
                except: pass
        return d

    def _get_reputation(self):
        rows = self.db.conn.execute("SELECT * FROM company_reputation ORDER BY overall_sentiment DESC LIMIT 20").fetchall()
        return [dict(r) for r in rows]

    def _get_email_logs(self):
        rows = self.db.conn.execute("SELECT * FROM email_logs ORDER BY id DESC LIMIT 100").fetchall()
        return [dict(r) for r in rows]

    def _get_companies(self):
        rows = self.db.conn.execute("SELECT * FROM company_db WHERE is_active=1 ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def _serve_static(self, path):
        """Serve dashboard/dist static files; fall back to index.html for SPA routes."""
        base = Path(__file__).resolve().parent / "dist"
        if path == "/":
            target = base / "index.html"
        else:
            # Remove leading slash and decode URL
            rel = unquote(path.lstrip("/"))
            target = base / rel
            # If it's a directory or doesn't exist, serve index.html (SPA fallback)
            if not target.exists() or target.is_dir():
                target = base / "index.html"

        if not target.exists():
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        content_type, _ = mimetypes.guess_type(str(target))
        content_type = content_type or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        with open(target, "rb") as f:
            self.wfile.write(f.read())

    # ── POST ──
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        self._cors()
        try:
            if self.path == "/api/email-config":       self._json(self._save_config(body))
            elif self.path == "/api/test-email":        self._json(self._test_email(body))
            elif self.path == "/api/send-email":         self._json(self._send_email(body))
            else:                                        self._json({"error":"not found"})
        except Exception as e:
            self._json({"success": False, "error": str(e)})

    def _save_config(self, data):
        email = data.get("email",""); auth = data.get("auth_code","")
        if email and auth:
            # Write to .env
            env_path = Path(__file__).resolve().parent.parent / ".env"
            lines = env_path.read_text().split("\n") if env_path.exists() else []
            new_lines = []
            replaced = {"EMAIL_ADDRESS":False,"EMAIL_AUTH_CODE":False}
            for line in lines:
                if line.startswith("EMAIL_ADDRESS=") and email:
                    new_lines.append(f"EMAIL_ADDRESS={email}"); replaced["EMAIL_ADDRESS"]=True
                elif line.startswith("EMAIL_AUTH_CODE=") and auth:
                    new_lines.append(f"EMAIL_AUTH_CODE={auth}"); replaced["EMAIL_AUTH_CODE"]=True
                else:
                    new_lines.append(line)
            if not replaced["EMAIL_ADDRESS"]: new_lines.append(f"EMAIL_ADDRESS={email}")
            if not replaced["EMAIL_AUTH_CODE"]: new_lines.append(f"EMAIL_AUTH_CODE={auth}")
            env_path.write_text("\n".join(new_lines))
            os.environ["EMAIL_ADDRESS"] = email
            os.environ["EMAIL_AUTH_CODE"] = auth
            return {"success":True,"message":"配置已保存"}
        return {"success":False,"error":"缺少邮箱或授权码"}

    def _test_email(self, data):
        email = data.get("email","") or os.getenv("EMAIL_ADDRESS","")
        auth = data.get("auth_code","") or os.getenv("EMAIL_AUTH_CODE","")
        if not email or not auth:
            return {"success":False,"error":"缺少邮箱地址或授权码"}
        try:
            with smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=15) as smtp:
                smtp.login(email, auth)
            return {"success":True,"message":"QQ邮箱SMTP连接成功"}
        except smtplib.SMTPAuthenticationError:
            return {"success":False,"error":"授权码错误，请检查是否复制了完整的16位授权码"}
        except Exception as e:
            return {"success":False,"error":f"连接失败: {str(e)[:100]}"}

    def _send_email(self, data):
        to_addr = data.get("to","")
        if not to_addr:
            return {"success":False,"error":"缺少收件人邮箱"}

        email_addr = os.getenv("EMAIL_ADDRESS","")
        auth_code = os.getenv("EMAIL_AUTH_CODE","")
        if not email_addr or not auth_code:
            return {"success":False,"error":"邮箱未配置，请先在「登录邮箱」页面连接QQ邮箱"}

        job_id = data.get("job_id","")
        company = data.get("company","")
        title = data.get("title","实习生")
        resume_path = data.get("resume_path","")

        subject = f"2028届-应聘{title}-崔曦文-华东师大-金融硕士"
        body = f"""尊敬的{company}招聘负责人：

您好！

我是崔曦文，华东师范大学金融硕士在读（2028届）。
对贵公司的"{title}"岗位非常感兴趣。

我在证券研究领域有扎实的实习经历，独立完成过行业深度研究报告和DCF估值模型。
具备财务建模、Python数据分析和Wind/iFinD等金融终端使用能力。

附件是我的简历，包含详细的项目经历和研究成果。
期待有机会与您进一步交流！

祝工作顺利！

崔曦文
"""

        try:
            msg = MIMEMultipart()
            msg["Subject"] = Header(subject, "utf-8")
            msg["From"] = formataddr(("崔曦文", email_addr))
            msg["To"] = to_addr
            msg.attach(MIMEText(body, "plain", "utf-8"))

            if resume_path and Path(resume_path).exists():
                with open(resume_path, "rb") as f:
                    att = MIMEApplication(f.read())
                    att.add_header("Content-Disposition", "attachment", filename=("utf-8","",Path(resume_path).name))
                    msg.attach(att)

            with smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=30) as smtp:
                smtp.login(email_addr, auth_code)
                smtp.sendmail(email_addr, [to_addr], msg.as_string())

            self.db.log_email(job_id, to_addr, subject, "sent")
            self.db.update_status(job_id, "applied")
            return {"success":True,"message":"邮件已通过QQ邮箱发送"}
        except smtplib.SMTPAuthenticationError:
            return {"success":False,"error":"QQ邮箱授权码错误，请重新登录"}
        except smtplib.SMTPDataError as e:
            return {"success":False,"error":f"发送被拒(可能超每日限额): {str(e)[:80]}"}
        except Exception as e:
            error_str = str(e)
            self.db.log_email(job_id, to_addr, subject, "failed", error_str[:200])
            return {"success":False,"error":f"发送失败: {error_str[:100]}"}

    def log_message(self, format, *args):
        pass


def main():
    db = FinanceJobDB()
    APIHandler.db = db
    port = int(os.getenv("PORT", "5175"))
    server = HTTPServer(("0.0.0.0", port), APIHandler)
    print(f"FinanceJob API -> http://0.0.0.0:{port}")
    print(f"   QQ: {'connected' if os.getenv('EMAIL_AUTH_CODE') else 'not configured'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        db.close()
        print("\n👋 Done")

if __name__ == "__main__":
    main()
