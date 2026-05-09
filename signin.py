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

def do_signin() -> dict:
    """使用網頁版簽到端點"""
    # 先取得 CSRF Token（從 Cookie 中解析）
    csrf_token = ""
    for item in COOKIE.split(";"):
        item = item.strip()
        if item.startswith("ckBahamutCsrfToken="):
            csrf_token = item.split("=", 1)[1]
            break

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

    # 嘗試多個可能的端點，哪個成功就用哪個
    endpoints = [
        ("GET",  "https://www.gamer.com.tw/ajax/click_signin.php"),
        ("POST", "https://www.gamer.com.tw/ajax/click_signin.php"),
        ("GET",  "https://api.gamer.com.tw/user/v1/signin.php"),
        ("POST", "https://api.gamer.com.tw/user/v1/signin.php"),
    ]

    last_error = None
    for method, url in endpoints:
        try:
            print(f"嘗試：{method} {url}")
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=15)
            else:
                resp = requests.post(url, headers=headers,
                                     data={"csrf_token": csrf_token},
                                     timeout=15)

            print(f"狀態碼：{resp.status_code}")
            print(f"回應內容：{resp.text[:200]}")  # 只印前200字

            if resp.status_code == 200:
                # 嘗試解析 JSON
                try:
                    return {"url": url, "method": method, "data": resp.json()}
                except Exception:
                    # 非 JSON 回應也算成功，直接回傳文字
                    return {"url": url, "method": method, "data": resp.text}

        except Exception as e:
            print(f"端點失敗：{e}")
            last_error = e
            continue

    raise Exception(f"所有端點均失敗，最後錯誤：{last_error}")

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        print("正在執行簽到（網頁版 Cookie 方式）...")
        result = do_signin()
        print(f"簽到成功，使用端點：{result['url']}")

        body = (
            f"簽到時間：{now}\n"
            f"使用端點：{result['url']}\n"
            f"請求方式：{result['method']}\n"
            f"回應內容：{result['data']}"
        )
        send_email("✅ 巴哈每日簽到成功", body)

    except Exception as e:
        error_msg = f"錯誤時間：{now}\n錯誤訊息：{str(e)}"
        print(f"發生錯誤：{e}")
        send_email("❌ 巴哈每日簽到失敗", error_msg)
        raise

if __name__ == "__main__":
    main()
