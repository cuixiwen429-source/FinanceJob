#!/usr/bin/env python3
"""FinanceJob Launcher — 启动 API + Web 看板并打开浏览器

跨平台支持: macOS / Windows / Linux
用法:
    python launcher.py
"""
import os
import platform
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API_PORT, WEB_PORT = 5175, 5174


def _kill_port(port: int):
    """尝试释放指定端口上的进程"""
    system = platform.system()
    try:
        if system == "Windows":
            # netstat -ano | findstr :PORT
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True, check=False,
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and ("LISTENING" in line or "ESTABLISHED" in line):
                    parts = line.strip().split()
                    if parts:
                        pid = parts[-1]
                        subprocess.run(["taskkill", "/F", "/PID", pid],
                                       capture_output=True, check=False)
        else:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True, text=True, check=False,
            )
            for pid in result.stdout.strip().split("\n"):
                if pid:
                    os.kill(int(pid), signal.SIGTERM)
    except Exception:
        pass


def kill_ports():
    for p in [API_PORT, WEB_PORT]:
        _kill_port(p)


def _wait_for_server(port: int, timeout: int = 60) -> bool:
    """等待服务就绪"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(f"http://localhost:{port}", timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


def _open_browser(url: str):
    """跨平台打开浏览器"""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["open", url], check=False)
        elif system == "Windows":
            os.startfile(url)
        else:
            subprocess.run(["xdg-open", url], check=False)
    except Exception as e:
        print(f"  无法自动打开浏览器: {e}")


def main():
    kill_ports()
    time.sleep(0.5)

    print("🚀 FinanceJob — 金融求职全自动系统启动中...\n")

    # Start API
    api = subprocess.Popen(
        [sys.executable, str(ROOT / "dashboard" / "api_server.py")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(ROOT),
    )

    # Start Web (Next.js dev server)
    web_cwd = ROOT / "dashboard"
    web = subprocess.Popen(
        ["npx", "next", "dev", "-p", str(WEB_PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        cwd=str(web_cwd),
    )

    # Wait for web server
    print(f"  等待 Web 服务启动 (port {WEB_PORT})...")
    if _wait_for_server(WEB_PORT, timeout=60):
        print(f"  Web 服务已就绪")
    else:
        print(f"  ⚠ Web 服务未在 60 秒内就绪，请检查 dashboard 依赖是否安装")

    time.sleep(1)

    url = f"http://localhost:{WEB_PORT}"
    _open_browser(url)

    print(f"✅ 看板地址: {url}")
    print(f"   API 地址: http://localhost:{API_PORT}")
    print("   按 Ctrl+C 停止所有服务\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for p in [api, web]:
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        kill_ports()
        print("\n👋 FinanceJob 已停止")


if __name__ == "__main__":
    main()
