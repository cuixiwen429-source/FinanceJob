"""FinanceJob 爬虫引擎 — 浏览器封装

整合 Playwright + DrissionPage, 反检测策略来自 Auto-JobHunter + get_jobs。
"""

import random
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

COOKIES_DIR = Path(__file__).resolve().parent.parent / "cookies"


class StealthBrowser:
    """Playwright Stealth 浏览器封装"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None

    def start(self) -> Browser:
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-blink-features",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )
        return self.browser

    def new_context(self, platform: str) -> BrowserContext:
        """创建独立 context（物理配置隔离）"""
        cookie_file = COOKIES_DIR / f"{platform}_cookies.json"

        context = self.browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )

        # 注入反检测脚本
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            window.chrome = { runtime: {} };
        """)

        # 恢复 Cookie
        if cookie_file.exists():
            import json
            try:
                with open(cookie_file, "r") as f:
                    cookies = json.load(f)
                context.add_cookies(cookies)
            except Exception:
                pass

        return context

    def save_cookies(self, context: BrowserContext, platform: str):
        """持久化 Cookie"""
        cookie_file = COOKIES_DIR / f"{platform}_cookies.json"
        COOKIES_DIR.mkdir(parents=True, exist_ok=True)
        import json
        with open(cookie_file, "w") as f:
            json.dump(context.cookies(), f, ensure_ascii=False, indent=2)

    def random_delay(self, min_s: float = 0.5, max_s: float = 3.0):
        """随机延迟，模拟人类操作"""
        time.sleep(random.uniform(min_s, max_s))

    def human_type(self, page: Page, selector: str, text: str):
        """模拟人类逐字输入"""
        for char in text:
            page.type(selector, char, delay=random.randint(50, 200))
            time.sleep(random.uniform(0.02, 0.08))

    def close(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
