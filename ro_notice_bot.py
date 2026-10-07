import os
import re
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
BASE_URL = "https://roz.gnjoy.com.tw"

# GNJOY 真正的公告列表完整路徑
TARGET_URLS = [
    "https://roz.gnjoy.com.tw/Notice/Notice_List",
    "https://roz.gnjoy.com.tw/Notice"
]
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

def fetch_notices():
    """優先抓取 Notice_List，若失敗則回退至 Notice"""
    for url in TARGET_URLS:
        try:
            print(f"[*] 嘗試請求頁面：{url}")
            res = requests.get(url, headers=HEADERS, timeout=15)
            res.encoding = "utf-8"
            if res.status_code != 200:
                continue

            soup = BeautifulSoup(res.text, "html.parser")
            
            # 同時比對 a 標籤與全域帶有 Notice_Info 的連結
            link_tags = soup.find_all("a", href=re.compile(r"Notice_Info\?id=\d+"))
            notices = []
            
            for tag in link_tags:
                href = tag.get("href", "")
                title = tag.get_text(strip=True)
                match = re.search(r"id=(\d+)", href)
                if match and title:
                    notice_id = int(match.group(1))
                    notices.append({
                        "id": notice_id,
                        "title": title,
                        "link": urljoin(BASE_URL, href)
                    })

            # 若抓到的公告數量大於 1，代表成功取得清單
            if len(notices) > 1:
                return notices
        except Exception as e:
            print(f"[-] 請求 {url} 發生錯誤: {e}")

    return notices

def main():
    notices = fetch_notices()
    if not notices:
        print("[-] 警告：完全未在官網抓到任何公告！")
        return

    # 依照 ID 數值由大到小排序
    notices.sort(key=lambda x: x["id"], reverse=True)

    print("[*] 成功解析公告列表（顯示最新前 3 筆）：")
    for item in notices[:3]:
        print(f"    - ID: {item['id']} | 標題: {item['title']}")

    latest = notices[0]
    latest_id = str(latest["id"])
    title = latest["title"]
    full_url = latest["link"]

    last_id = load_last_id()

    # 首次啟動初始化
    if not last_id:
        print(f"[+] 首次記錄最新 ID：{latest_id}（{title}）")
        save_last_id(latest_id)
        return

    # 偵測到新公告
    if latest_id != last_id:
        print(f"[!] 偵測到新公告：{title} (ID: {latest_id})")
        send_discord_notify(title, full_url)
        save_last_id(latest_id)
    else:
        print(f"[*] 無新公告，當前最新篇號：{latest_id}")

if __name__ == "__main__":
    main()
