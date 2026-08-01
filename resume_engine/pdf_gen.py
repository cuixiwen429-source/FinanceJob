"""PDF 简历生成器

支持两种模式:
1. Markdown → HTML → PDF (weasyprint, 轻量)
2. 复用 reactive-resume 的导出引擎 (高质量 ATS 适配)
"""

import subprocess
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RESUMES_DIR = DATA_DIR / "resumes"


def markdown_to_html(md_text: str) -> str:
    """Markdown 转 HTML（简单版）"""
    import re

    html = md_text

    # 标题
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # 加粗
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)

    # 列表
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', html)

    # 段落
    html = re.sub(r'\n\n', '</p><p>', html)
    html = f"<p>{html}</p>"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 11pt; line-height: 1.6; max-width: 800px; margin: 40px auto; color: #222; }}
  h1 {{ font-size: 18pt; border-bottom: 2px solid #1a365d; padding-bottom: 8px; }}
  h2 {{ font-size: 14pt; color: #1a365d; margin-top: 18px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }}
  h3 {{ font-size: 12pt; }}
  ul {{ padding-left: 20px; }}
  li {{ margin-bottom: 4px; }}
  strong {{ color: #1a365d; }}
  p {{ margin: 6px 0; }}
</style>
</head>
<body>
{html}
</body>
</html>"""


def generate_pdf(md_text: str, output_path: str, name: str = "崔曦文",
                 job_title: str = "", company: str = "") -> str:
    """生成 PDF 简历

    Returns:
        str: PDF 文件路径
    """
    RESUMES_DIR.mkdir(parents=True, exist_ok=True)
    output = Path(output_path) if output_path else (
        RESUMES_DIR / f"{name}_{job_title}_{company}_简历.pdf"
    )

    try:
        # 优先尝试 weasyprint
        from weasyprint import HTML
        html_content = markdown_to_html(md_text)
        HTML(string=html_content).write_pdf(str(output))
        return str(output)
    except ImportError:
        pass

    # 备选: markdown → 文本保存（待后续转换）
    txt_path = output.with_suffix(".txt")
    txt_path.write_text(md_text, encoding="utf-8")
    print(f"  [PDF] weasyprint 未安装，简历已保存为文本: {txt_path}")
    return str(txt_path)


def generate_pdf_reactive_resume(md_text: str, output_path: str) -> str:
    """通过 reactive-resume 的 API 生成高质量 PDF

    用户已有 reactive-resume 项目在 ~/reactive-resume/
    尝试通过其 CLI/API 导出 PDF。
    """
    REACTIVE_RESUME_DIR = Path.home() / "reactive-resume"

    if not REACTIVE_RESUME_DIR.exists():
        print("  [PDF] reactive-resume 未找到，使用 weasyprint 降级方案")
        return generate_pdf(md_text, output_path)

    # 将 Markdown 写入临时文件
    temp_md = Path("/tmp/financejob_resume.md")
    temp_md.write_text(md_text, encoding="utf-8")

    # 尝试调用 reactive-resume 的导出
    try:
        result = subprocess.run(
            ["pnpm", "run", "export", "--input", str(temp_md), "--output", output_path],
            cwd=str(REACTIVE_RESUME_DIR),
            capture_output=True,
            timeout=30,
        )
        if result.returncode == 0 and Path(output_path).exists():
            return output_path
    except Exception:
        pass

    # 降级
    return generate_pdf(md_text, output_path)
