import os
import re
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# 從 GitHub Secrets 讀取
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

def send_discord_notify(title, link, date_str=""):
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

    description = f"發布日期：`{date_str}`\n" if date_str else ""
    description += "點擊上方標題即可前往官網查看完整內容！"

    payload = {
        "username": "RO樂園 官網廣播站",
        "avatar_url": "https://roz.gnjoy.com.tw/favicon.ico",
        "embeds": [
            {
                "title": f"📢 {title}",
                "url": link,
                "color": color,
                "description": description,
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
        link_tags = soup.find_all("a", href=re.compile(r"Notice_Info\?id=\d+"))
        if not link_tags:
            print("[-] 未在頁面上解析到任何公告連結")
            return

        notices = []
        for tag in link_tags:
            href = tag.get("href", "")
            title = tag.get_text(strip=True)
            if not title:
                continue

            match = re.search(r"id=(\d+)", href)
            if not match:
                continue
            
            notice_id = int(match.group(1))

            # 抓取該筆公告同一列顯示的日期（例如 2026.10.05）
            parent_row = tag.find_parent(["tr", "li", "div"])
            date_str = ""
            if parent_row:
                date_match = re.search(r"(\d{4}[./-]\d{1,2}[./-]\d{1,2})", parent_row.get_text())
                if date_match:
                    date_str = date_match.group(1)

            notices.append({
                "id": notice_id,
                "title": title,
                "link": urljoin(BASE_URL, href),
                "date": date_str
            })

        if not notices:
            print("[-] 未解析到有效的公告項目")
            return

        # 官網 ID 為自動遞增整數，挑出 ID 最大（真正最新發布）的公告，避開置頂舊文
        latest_notice = max(notices, key=lambda x: (x["date"], x["id"]))

        latest_id = str(latest_notice["id"])
        title = latest_notice["title"]
        full_url = latest_notice["link"]
        date_str = latest_notice["date"]

        last_id = load_last_id()

        # 首次初始化
        if not last_id:
            print(f"[+] 首次記錄最新公告 ID：{latest_id}（{title} / {date_str}）")
            save_last_id(latest_id)
            return

        # 比對是否有更新
        if latest_id != last_id:
            print(f"[!] 偵測到新公告：{title} ({date_str}) ID: {latest_id}")
            send_discord_notify(title, full_url, date_str=date_str)
            save_last_id(latest_id)
        else:
            print(f"[*] 無新公告，當前最新：{title} ({date_str}) ID: {latest_id}")

    except Exception as e:
        print(f"[-] 執行出錯: {e}")

if __name__ == "__main__":
    main()
