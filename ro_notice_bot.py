import os
import re
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
BASE_URL = "https://roz.gnjoy.com.tw"
NOTICE_LIST_URL = "https://roz.gnjoy.com.tw/Notice"
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

def get_latest_notice():
    # 抓取公告清單頁原始碼
    res = requests.get(NOTICE_LIST_URL, headers=HEADERS, timeout=15)
    res.encoding = "utf-8"
    if res.status_code != 200:
        print(f"[-] 無法載入公告頁面，HTTP 狀態碼: {res.status_code}")
        return None, None, None

    # 1. 直接用正則表達式掃描整份 HTML，找出所有 Notice_Info 的文章編號（不管放在 href 還是 onclick）
    all_ids = re.findall(r"Notice_Info\?id=(\d+)", res.text, re.IGNORECASE)
    if not all_ids:
        print("[-] 未在網頁原始碼中比對到任何公告編號")
        return None, None, None

    # 轉成整數並排序，取最大值（數字最大的就是最新發布的公告）
    int_ids = sorted(list(set(int(i) for i in all_ids)), reverse=True)
    latest_id = int_ids[0]
    notice_url = f"{BASE_URL}/Notice/Notice_Info?id={latest_id}"
    print(f"[*] 成功掃描到最新文章 ID: {latest_id}")

    # 2. 請求該篇最新公告的內頁，取得真實公告標題
    title = f"最新公告 #{latest_id}"
    try:
        info_res = requests.get(notice_url, headers=HEADERS, timeout=10)
        info_res.encoding = "utf-8"
        soup = BeautifulSoup(info_res.text, "html.parser")
        
        # 尋找內頁帶有【】的標題文字
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "div", "span"]):
            text = tag.get_text(strip=True)
            if "【" in text and "】" in text and len(text) < 60:
                title = text
                break
                
        # 備用方案：抓網頁標題
        if title.startswith("最新公告 #") and soup.title:
            raw_title = soup.title.get_text(strip=True)
            title = re.sub(r"[-–|].*", "", raw_title).strip() or title
    except Exception as e:
        print(f"[-] 擷取標題時出錯: {e}")

    return str(latest_id), title, notice_url

def main():
    latest_id, title, full_url = get_latest_notice()
    if not latest_id:
        return

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
