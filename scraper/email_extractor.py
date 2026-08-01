"""JD 正文邮箱提取器

正则匹配中国常见邮箱格式，排除平台官方邮箱。
"""

import re
from typing import Optional

# 邮箱正则
EMAIL_PATTERN = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')

# 平台官方邮箱域名（排除）
EXCLUDED_DOMAINS = {
    "@zhaopin.com", "@zhaopin.com.cn",
    "@liepin.com", "@51job.com",
    "@lagou.com", "@kanzhun.com",
    "@shixiseng.com",
    "@58.com", "@ganji.com",
    "@service.alibaba.com",
}


def extract_emails(text: str) -> list[str]:
    """从文本中提取所有邮箱地址"""
    if not text:
        return []
    emails = EMAIL_PATTERN.findall(text)
    return list(dict.fromkeys(emails))  # 去重保序


def extract_recruiter_email(text: str) -> Optional[str]:
    """从 JD/公司介绍中提取最可能的 HR 邮箱"""
    emails = extract_emails(text)
    valid_emails = [
        e for e in emails
        if not any(e.lower().endswith(d) for d in EXCLUDED_DOMAINS)
    ]
    return valid_emails[0] if valid_emails else None


def is_platform_email(email: str) -> bool:
    """判断是否为平台官方邮箱"""
    return any(email.lower().endswith(d) for d in EXCLUDED_DOMAINS)


def parse_salary_range(salary_text: str) -> Optional[tuple[float, float]]:
    """解析薪资文本，返回 (月薪下限, 月薪上限)"""
    if not salary_text:
        return None

    text = salary_text.strip().lower()

    # 处理 "200-300/天" 格式
    if "/天" in text or "/day" in text:
        nums = re.findall(r'(\d+)', text)
        if len(nums) >= 1:
            daily = float(nums[0])
            return (daily * 22, daily * 22)  # 按22工作日
        return None

    # 处理 "8k-12k" / "8000-12000/月" 格式
    nums = re.findall(r'(\d+\.?\d*)', text)
    if len(nums) >= 2:
        lo, hi = float(nums[0]), float(nums[1])
        if "k" in text.lower():
            lo *= 1000
            hi *= 1000
        return (lo, hi)
    elif len(nums) == 1:
        val = float(nums[0])
        if "k" in text.lower():
            val *= 1000
        return (val, val)

    # 处理 "年薪30-50万" 格式
    if "万" in text or "年" in text:
        nums = re.findall(r'(\d+\.?\d*)', text)
        if len(nums) >= 2:
            lo = float(nums[0]) * 10000 / 12
            hi = float(nums[1]) * 10000 / 12
            return (lo, hi)
        elif len(nums) == 1:
            val = float(nums[0]) * 10000 / 12
            return (val, val)

    return None


def detect_remote(text: str) -> bool:
    """检测 JD 是否支持远程"""
    remote_keywords = [
        "远程", "线上", "可远程", "remote", "线上办公",
        "不限地点", "远程办公", "居家办公", "远程实习",
    ]
    text_lower = text.lower()
    return any(kw in text_lower for kw in remote_keywords)
