import os
import requests
from bs4 import BeautifulSoup

# 設定
TARGET_URL = "https://www.mhlw.go.jp/stf/shingi/shingi-chuo_128154.html"
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")
DB_FILE = "last_url.txt"

def send_line(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message}]
    }
    requests.post(url, headers=headers, json=payload)

def main():
    # ページ取得
    response = requests.get(TARGET_URL)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, "html.parser")

    # 中央社会保険医療協議会総会の最新リンクを探す
    link_tag = soup.find("a", string=lambda s: s and "中央社会保険医療協議会総会" in s)
    if not link_tag:
        print("リンクが見つかりませんでした")
        return

    latest_url = "https://www.mhlw.go.jp" + link_tag.get("href")
    title = link_tag.get_text(strip=True)

    # 前回保存したURLと比較
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            last_url = f.read().strip()
    else:
        last_url = ""

    if latest_url != last_url:
        print(f"更新を検知: {latest_url}")
        send_line(f"【中医協更新】\n{title}\n{latest_url}")
        with open(DB_FILE, "w") as f:
            f.write(latest_url)
    else:
        print("更新はありませんでした")

if __name__ == "__main__":
    main()
