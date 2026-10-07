import os
import re
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
BASE_URL = "https://roz.gnjoy.com.tw"
NOTICE_URL = "https://roz.gnjoy.com.tw/Notice"
CACHE_FILE = "last_notice_id.txt"

def load_last_id():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def save_last_id(notice_id):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        f.write(str(notice_id))

def send_discord_notify(title, link):
    if not DISCORD_WEBHOOK_URL:
        print("[-] 錯誤：未找到 DISCORD_WEBHOOK_URL 環境變數")
        return

    color = 0x3498DB
    if "開機" in title:
        color = 0x2ECC71
    elif "關機" in title or "維護" in title:
        color = 0xE74C3C
    elif "異常" in title:
        color = 0xE67E22

    payload = {
        "username": "RO樂園 官網廣播站",
        "avatar_url": "https://roz.gnjoy.com.tw/favicon.ico",
        "embeds": [
            {
                "title": f"📢 {title}",
                "url": link,
                "color": color,
                "description": "官網發布了最新公告，點擊上方標題即可前往查看完整內容！",
                "footer": {"text": "RO仙境傳說Online：樂園 自動廣播"},
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        ],
    }
    
    resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    resp.raise_for_status()

def fetch_rendered_html():
    """使用無頭 Chrome 完整執行 JavaScript 並渲染網頁"""
    print("[*] 正在啟動 Chrome 載入官網公告...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            )
        )
        page.goto(NOTICE_URL, timeout=45000)
        # 等待 4 秒，讓 JavaScript 完整把後台最新公告填入頁面
        page.wait_for_timeout(4000)
        html_content = page.content()
        browser.close()
        return html_content

def main():
    try:
        html = fetch_rendered_html()
        soup = BeautifulSoup(html, "html.parser")

        # 掃描頁面上所有帶有 Notice_Info 的連結
        link_tags = soup.find_all("a", href=re.compile(r"Notice_Info\?id=\d+"))
        notices = []

        for tag in link_tags:
            href = tag.get("href", "")
            title = tag.get_text(strip=True)
            match = re.search(r"id=(\d+)", href)
            if match and title:
                notices.append({
                    "id": int(match.group(1)),
                    "title": title,
                    "link": urljoin(BASE_URL, href)
                })

        if not notices:
            print("[-] 未能解析到公告項目")
            return

        # 依文章 ID 由大到小排序（數值最大的絕對是最新公告）
        notices.sort(key=lambda x: x["id"], reverse=True)

        print("[*] 頁面成功解析！當前公告列表前 3 筆：")
        for item in notices[:3]:
            print(f"    - ID: {item['id']} | 標題: {item['title']}")

        latest_notice = notices[0]
        latest_id = str(latest_notice["id"])
        title = latest_notice["title"]
        full_url = latest_notice["link"]

        last_id = load_last_id()

        # 首次初始化
        if not last_id:
            print(f"[+] 首次記錄最新 ID：{latest_id}（{title}）")
            save_last_id(latest_id)
            return

        # 比對新公告
        if latest_id != last_id:
            print(f"[!] 偵測到新公告：{title} (ID: {latest_id})")
            send_discord_notify(title, full_url)
            save_last_id(latest_id)
        else:
            print(f"[*] 無新公告，當前最新篇號：{latest_id}")

    except Exception as e:
        print(f"[-] 執行出錯: {e}")

if __name__ == "__main__":
    main()
