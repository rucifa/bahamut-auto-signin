import requests
import smtplib
import os
from email.mime.text import MIMEText
from datetime import datetime

COOKIE = os.environ["BAHAMUT_COOKIE"]
EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
EMAIL_TO = os.environ["EMAIL_TO"]

def send_email(subject: str, body: str):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)
    print(f"Email 已發送：{subject}")

def get_csrf_token() -> str:
    for item in COOKIE.split(";"):
        item = item.strip()
        if item.startswith("ckBahamutCsrfToken="):
            return item.split("=", 1)[1]
    return ""

def try_endpoint(method: str, url: str, headers: dict, csrf_token: str):
    """
    嘗試一個端點，回傳 (成功與否, 訊息)
    判斷標準：
      - 必須是 JSON 回應
      - 不能包含 '找不到網頁' 或 '<!doctype' 等 HTML 錯誤頁
    """
    if method == "GET":
        resp = requests.get(url, headers=headers, timeout=15)
    else:
        resp = requests.post(url, headers=headers,
                             data={"csrf_token": csrf_token}, timeout=15)

    print(f"[{method}] {url} → {resp.status_code}")

    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}"

    text = resp.text.strip()

    # 回傳 HTML 代表是錯誤頁，不是真正的 API 回應
    if text.lower().startswith("<!doctype") or "找不到網頁" in text:
        return False, "回傳 HTML 錯誤頁（端點不存在）"

    # 嘗試解析 JSON
    try:
        data = resp.json()
        print(f"JSON 回應：{data}")
        return True, data
    except Exception:
        # 非 JSON 但也不是 HTML 錯誤頁，可能是純文字成功回應
        print(f"純文字回應：{text[:100]}")
        return True, text

def do_signin():
    csrf_token = get_csrf_token()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        "Cookie": COOKIE,
        "Referer": "https://www.gamer.com.tw/",
        "Origin": "https://www.gamer.com.tw",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW,zh;q=0.9",
        "X-CSRF-Token": csrf_token
    }

    endpoints = [
        ("GET",  "https://www.gamer.com.tw/ajax/click_signin.php"),
        ("POST", "https://www.gamer.com.tw/ajax/click_signin.php"),
        ("GET",  "https://api.gamer.com.tw/user/v1/signin.php"),
        ("POST", "https://api.gamer.com.tw/user/v1/signin.php"),
        ("GET",  "https://api.gamer.com.tw/bahamut/v1/signin.php"),
    ]

    for method, url in endpoints:
        try:
            success, result = try_endpoint(method, url, headers, csrf_token)
            if success:
                return url, method, result
        except Exception as e:
            print(f"端點例外：{e}")
            continue

    raise Exception("所有端點均失敗，請手動從瀏覽器 F12 找出正確的簽到 API")

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        print("正在執行簽到...")
        url, method, data = do_signin()

        # 精簡成功通知
        if isinstance(data, dict):
            days = data.get("data", {}).get("days", "")
            days_msg = f"\n連續簽到：{days} 天" if days else ""
        else:
            days_msg = ""

        body = f"簽到時間：{now}{days_msg}"
        print(f"簽到成功：{body}")
        send_email("✅ 巴哈每日簽到成功", body)

    except Exception as e:
        # 失敗時才附上詳細資訊
        error_msg = (
            f"簽到時間：{now}\n"
            f"錯誤訊息：{str(e)}\n\n"
            f"請至 GitHub Actions 查看完整 Log：\n"
            f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', '你的帳號/你的Repo')}/actions"
        )
        print(f"發生錯誤：{e}")
        send_email("❌ 巴哈每日簽到失敗", error_msg)
        raise

if __name__ == "__main__":
    main()
