import os
import re
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# 從 GitHub Secrets 注入的環境變數讀取
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
BASE_URL = "https://roz.gnjoy.com.tw"
NOTICE_URL = "https://roz.gnjoy.com.tw/Notice"
CACHE_FILE = "last_notice_id.txt"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    )
}

def load_last_id():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def save_last_id(notice_id):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        f.write(str(notice_id))

def send_discord_notify(title, link, category="最新消息"):
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
                "description": f"分類：`{category}`\n點擊標題即可查看官網完整公告！",
                "footer": {"text": "RO仙境傳說Online：樂園 自動廣播"},
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        ],
    }
    
    resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    resp.raise_for_status()

def main():
    try:
        res = requests.get(NOTICE_URL, headers=HEADERS, timeout=15)
        res.encoding = "utf-8"
        if res.status_code != 200:
            print(f"[-] 伺服器響應異常：{res.status_code}")
            return

        soup = BeautifulSoup(res.text, "html.parser")
        links = soup.find_all("a", href=re.compile(r"Notice_Info\?id=\d+"))
        if not links:
            print("[-] 未在頁面上解析到任何公告連結")
            return

        latest_link = links[0]
        href = latest_link.get("href", "")
        title = latest_link.get_text(strip=True)
        
        match = re.search(r"id=(\d+)", href)
        if not match:
            return
            
        latest_id = match.group(1)
        full_url = urljoin(BASE_URL, href)
        last_id = load_last_id()

        # 首次執行：先記錄 ID 避免洗頻
        if not last_id:
            print(f"[+] 首次初始化快取 ID：{latest_id}")
            save_last_id(latest_id)
            return

        # 發現新公告
        if latest_id != last_id:
            print(f"[!] 偵測到新公告：{title} (ID: {latest_id})")
            send_discord_notify(title, full_url)
            save_last_id(latest_id)
        else:
            print(f"[*] 無新公告，最新篇號仍為：{last_id}")

    except Exception as e:
        print(f"[-] 執行出錯: {e}")

if __name__ == "__main__":
    main()
