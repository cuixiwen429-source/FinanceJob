"""SMTP 邮件投递引擎

双通道:
  通道 A: SMTP 自动发送 (163邮箱, 10封/分钟)
  通道 B: .eml 草稿（人工审核后发送）

用法:
    python -m email_sender.sender
    python -m email_sender.sender --draft-only  # 仅生成.eml草稿
"""

import argparse
import smtplib
import time
from email.header import Header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formataddr
from datetime import datetime
from pathlib import Path

from shared.db import FinanceJobDB
from shared.config import UserConfig


def send_email(
    smtp_server: str,
    smtp_port: int,
    auth_code: str,
    from_addr: str,
    from_name: str,
    to_addr: str,
    subject: str,
    body: str,
    attachment_path: str = None,
) -> tuple[bool, str]:
    """发送单封邮件

    Returns:
        (success, error_message)
    """
    try:
        msg = MIMEMultipart()
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = formataddr((from_name, from_addr))
        msg["To"] = to_addr

        # 正文
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # 附件
        if attachment_path and Path(attachment_path).exists():
            with open(attachment_path, "rb") as f:
                att = MIMEApplication(f.read())
                filename = Path(attachment_path).name
                att.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=("utf-8", "", filename),
                )
                msg.attach(att)

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
            smtp.login(from_addr, auth_code)
            smtp.sendmail(from_addr, [to_addr], msg.as_string())

        return True, ""

    except Exception as e:
        return False, str(e)


def generate_eml_draft(
    from_addr: str,
    from_name: str,
    to_addr: str,
    subject: str,
    body: str,
    attachment_path: str = None,
) -> str:
    """生成 .eml 草稿文件（人工审核后手动发送）"""
    msg = MIMEMultipart()
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((from_name, from_addr))
    msg["To"] = to_addr
    msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800")

    msg.attach(MIMEText(body, "plain", "utf-8"))

    if attachment_path and Path(attachment_path).exists():
        with open(attachment_path, "rb") as f:
            att = MIMEApplication(f.read())
            filename = Path(attachment_path).name
            att.add_header(
                "Content-Disposition", "attachment",
                filename=("utf-8", "", filename),
            )
            msg.attach(att)

    eml_dir = Path(__file__).resolve().parent.parent / "data" / "eml_drafts"
    eml_dir.mkdir(parents=True, exist_ok=True)

    safe_subject = subject.replace("/", "-").replace(" ", "_")[:50]
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M')}_{safe_subject}.eml"
    eml_path = eml_dir / filename
    eml_path.write_text(msg.as_string(), encoding="utf-8")

    return str(eml_path)


def build_subject(job: dict, config: UserConfig) -> str:
    """生成邮件主题"""
    title = job.get("title", "实习生")
    company = job.get("company", "")
    grad_year = config.graduation_year

    # 提取岗位简称
    title_short = title.replace("实习生", "").replace("实习", "").strip()
    if len(title_short) > 10:
        title_short = title_short[:8]

    subject = f"{grad_year}届-应聘{title_short}-{config.name}-{config.school}-{config.degree}"
    return subject[:60]


def build_body(job: dict, config: UserConfig) -> str:
    """生成邮件正文（求职信）"""
    cover_letter = job.get("cover_letter", "")
    if cover_letter:
        return cover_letter

    company = job.get("company", "贵公司")
    title = job.get("title", "实习生")

    return f"""尊敬的{company}招聘负责人：

您好！

我是{config.name}，{config.school}{config.degree}在读（{config.graduation_year}届），
对贵公司的"{title}"岗位非常感兴趣。

我在证券研究领域有扎实的实习经历，独立完成过行业深度研究报告和DCF估值模型。
具备财务建模、Python数据分析和Wind/同花顺等金融终端使用能力。

附件是我的简历，包含详细的项目经历和研究成果。
期待有机会与您进一步交流！

祝工作顺利！

{config.name}
{datetime.now().strftime('%Y.%m.%d')}
"""


class EmailSender:
    """邮件投递引擎"""

    def __init__(self, db: FinanceJobDB, config: UserConfig):
        self.db = db
        self.config = config
        self.sent_count = 0
        self.minute_start = time.time()
        self.rate_limit = 10  # 封/分钟

    def send_all(self, draft_only: bool = False, max_send: int = 50):
        """对简历就绪的岗位进行邮件投递，按综合评分降序"""
        rows = self.db.conn.execute(
            """SELECT * FROM jobs
               WHERE status = 'resume_ready'
               AND (recruiter_email != '' AND recruiter_email IS NOT NULL)
               ORDER BY composite_score DESC
               LIMIT ?""",
            (max_send,)
        ).fetchall()
        jobs = [dict(r) for r in rows]

        if not jobs:
            print("[邮件] 暂无待投递的岗位（需要状态=resume_ready 且有 HR 邮箱）")
            return

        print(f"[邮件] 准备投递 {len(jobs)} 个岗位...")

        sent = 0
        skipped = 0
        draft_count = 0

        for job in jobs:
            jid = job.get("id", "")
            to_email = job.get("recruiter_email", "")
            title = job.get("title", "")
            decision = job.get("decision", "")
            composite = job.get("composite_score", 0)
            resume_path = job.get("tailored_resume_path", "")

            # 跳过近期已发送的邮箱
            if self.db.is_email_sent_recently(to_email, days=7):
                skipped += 1
                continue

            subject = build_subject(job, self.config)

            if draft_only or decision == "可投递":
                # 通道 B: .eml 草稿
                body = build_body(job, self.config)
                eml_path = generate_eml_draft(
                    self.config.email_address, self.config.name,
                    to_email, subject, body, resume_path,
                )
                draft_count += 1
                self.db.log_email(jid, to_email, subject, "draft")
            else:
                # 通道 A: 自动发送
                self._rate_limit_wait()
                body = build_body(job, self.config)

                success, error = send_email(
                    self.config.email_smtp_server,
                    self.config.email_smtp_port,
                    self.config.email_auth_code,
                    self.config.email_address,
                    self.config.name,
                    to_email,
                    subject,
                    body,
                    resume_path,
                )

                if success:
                    sent += 1
                    self.db.log_email(jid, to_email, subject, "sent")
                    self.db.update_status(jid, "applied")
                    print(f"  ✓ [{composite:.0f}分] {title} → {to_email}")
                else:
                    self.db.log_email(jid, to_email, subject, "failed", error)
                    print(f"  ✗ {title}: {error[:80]}")

        self.sent_count = sent

        print(f"\n[邮件] 完成! 发送: {sent} | 草稿: {draft_count} | 跳过(7天内): {skipped}")

    def _rate_limit_wait(self):
        """速率控制: 10封/分钟"""
        elapsed = time.time() - self.minute_start
        if self.sent_count >= self.rate_limit:
            if elapsed < 60:
                wait = 60 - elapsed + 2
                time.sleep(wait)
            self.sent_count = 0
            self.minute_start = time.time()


def main():
    parser = argparse.ArgumentParser(description="FinanceJob 邮件投递")
    parser.add_argument("--draft-only", action="store_true", help="仅生成 .eml 草稿，不自动发送")
    parser.add_argument("--max-send", type=int, default=50, help="最大发送数量")
    args = parser.parse_args()

    config = UserConfig.load()

    if not config.email_auth_code or not config.email_address:
        print("[邮件] ⚠ 未配置邮箱。请设置环境变量 EMAIL_ADDRESS 和 EMAIL_AUTH_CODE")
        print("  或编辑 .env 文件。")
        return

    db = FinanceJobDB()
    sender = EmailSender(db, config)
    sender.send_all(draft_only=args.draft_only, max_send=args.max_send)
    db.close()


if __name__ == "__main__":
    main()
