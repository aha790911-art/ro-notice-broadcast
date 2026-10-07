import os
import re
import time
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
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
        page.wait_for_timeout(4000)
        html_content = page.content()
        browser.close()
        return html_content

def clean_title(raw_text):
    """去除標題末端黏在一起的日期時間"""
    cleaned = re.sub(r"\d{4}\.\d{2}\.\d{2}.*$", "", raw_text).strip()
    return cleaned if cleaned else raw_text

def main():
    try:
        html = fetch_rendered_html()
        soup = BeautifulSoup(html, "html.parser")

        link_tags = soup.find_all("a", href=re.compile(r"Notice_Info\?id=\d+"))
        notices = []

        for tag in link_tags:
            href = tag.get("href", "")
            title = clean_title(tag.get_text(strip=True))
            match = re.search(r"id=(\d+)", href)
            if match and title:
                notice_id = int(match.group(1))
                correct_url = f"https://roz.gnjoy.com.tw/Notice/Notice_Info?id={notice_id}"
                notices.append({
                    "id": notice_id,
                    "title": title,
                    "link": correct_url
                })

        if not notices:
            print("[-] 未能解析到公告項目")
            return

        last_id_str = load_last_id()

        # 首次初始化：只記錄最新篇號，避免把整頁舊公告洗出來
        if not last_id_str or not last_id_str.isdigit():
            max_id = max(n["id"] for n in notices)
            print(f"[+] 首次記錄最新 ID：{max_id}")
            save_last_id(max_id)
            return

        last_id = int(last_id_str)

        # 篩選出所有比上次紀錄還要新的公告
        new_notices = [n for n in notices if n["id"] > last_id]

        if not new_notices:
            print(f"[*] 無新公告，當前最新篇號：{last_id}")
            return

        # 依 ID 由小到大排序（按照發布先後順序推送）
        new_notices.sort(key=lambda x: x["id"])

        print(f"[!] 偵測到 {len(new_notices)} 篇新公告！開始推送...")
        for n in new_notices:
            print(f"    - 推送：{n['title']} (ID: {n['id']})")
            send_discord_notify(n["title"], n["link"])
            time.sleep(1.5)  # 間隔 1.5 秒，避免觸發 Discord 頻率限制

        # 將這次推播中最新的一篇 ID 存回檔案
        save_last_id(new_notices[-1]["id"])

    except Exception as e:
        print(f"[-] 執行出錯: {e}")

if __name__ == "__main__":
    main()
