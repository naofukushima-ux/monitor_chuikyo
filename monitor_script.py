import os
import requests
from bs4 import BeautifulSoup

# --- 設定 ---
TARGET_URL = "https://www.mhlw.go.jp/stf/shingi/shingi-chuo_128154.html"
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")
KEYWORDS = ["在宅", "遠隔医療", "オンライン診療", "外来"]
STATUS_FILE = "last_url.txt"

def send_line_message(message):
    if not LINE_TOKEN or not LINE_USER_ID:
        return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, json=payload)

def get_latest_material_info():
    """
    最新の1件目のURLを取得しつつ、
    もしそれが資料ページでなければ、一番近い『資料』ページのURLも探す
    """
    try:
        res = requests.get(TARGET_URL, timeout=10)
        soup = BeautifulSoup(res.content, "html.parser")
        links = soup.select(".m-listLink a")
        
        if not links:
            return None, None, False, ""

        # 1件目（最新）の情報
        latest_link = links[0]
        latest_url = latest_link.get("href")
        if not latest_url.startswith("http"):
            latest_url = "https://www.mhlw.go.jp" + latest_url
        latest_text = latest_link.get_text()
        
        # 「資料」ページを特定する（最新5件の中から探す）
        material_url = None
        for l in links[:5]:
            if "資料" in l.get_text():
                m_href = l.get("href")
                material_url = m_href if m_href.startswith("http") else "https://www.mhlw.go.jp" + m_href
                break
        
        # 1件目が資料ページかどうか
        is_material_now = "資料" in latest_text
        
        # 【変更点】判定用に最新のリンク文字（latest_text）も一緒に返します
        return latest_url, material_url, is_material_now, latest_text
    except Exception as e:
        print(f"Error: {e}")
        return None, None, False, ""

def main():
    print("更新チェック開始...")
    # 【変更点】latest_text を受け取るようにしました
    latest_url, material_url, is_material_now, latest_text = get_latest_material_info()
    
    if not latest_url:
        return

    # --- 差分チェック ---
    last_url = ""
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            last_url = f.read().strip()

    if latest_url == last_url:
        print("更新がないため終了します。")
        return

    # --- 新着あり ---
    # 資料一覧URLが取得できていればそれを使う、なければ最新URLを使う
    display_url = material_url if material_url else latest_url

    # 【変更点】「議事録」という文字が含まれていた場合の処理を最優先で追加
    if "議事録" in latest_text:
        msg = f"今日、中医協総会のページに【議事録】の追加がありました！\n\n追加されたページ：\n{latest_url}"
        send_line_message(msg)
        
    elif not is_material_now:
        # ② 更新はあったが、まだ開催案内の場合
        msg = f"今日、中医協総会の資料の更新（開催案内等）がありましたが、配布資料はまだ公開されていません。\n資料が公開されたらこちらに並びます：\n{display_url}"
        send_line_message(msg)
    else:
        # ③ 資料ページが公開された場合
        res = requests.get(latest_url)
        soup = BeautifulSoup(res.content, "html.parser")
        matched_items = []
        found_keywords = set()
        
        for link in soup.find_all("a"):
            text = link.get_text()
            href = link.get("href", "")
            if href.endswith(".pdf"):
                for k in KEYWORDS:
                    if k in text:
                        found_keywords.add(k)
                        pdf_url = href if href.startswith("http") else "https://www.mhlw.go.jp" + href
                        matched_items.append({"title": text, "url": pdf_url})

        if matched_items:
            kw_str = "・".join(found_keywords)
            msg = f"今日、中医協総会の資料が更新され、（{kw_str}）の資料が更新されています。\n"
            msg += f"資料一覧ページ：\n{latest_url}\n"
            for item in matched_items:
                msg += f"\n・{item['title']}\n{item['url']}"
            send_line_message(msg)
        else:
            msg = f"今日、中医協総会の資料の更新がありましたが、対象キーワードの資料は含まれていませんでした。\n資料一覧ページ：\n{latest_url}"
            send_line_message(msg)

    # 履歴更新
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        f.write(latest_url)

if __name__ == "__main__":
    main()
