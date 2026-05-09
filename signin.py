import requests
import smtplib
import os
from email.mime.text import MIMEText
from datetime import datetime

USERNAME = os.environ["BAHAMUT_USERNAME"]
PASSWORD = os.environ["BAHAMUT_PASSWORD"]
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

def get_session_token() -> str:
    url = "https://api.gamer.com.tw/mobile_app/user/v3/do_login.php"
    payload = {
        "uid": USERNAME,
        "passwd": PASSWORD,
        "appVersion": "3.3.1"
    }
    headers = {
        "User-Agent": "BahamutApp/3.3.1 (Android)",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    resp = requests.post(url, data=payload, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != 1:
        raise Exception(f"登入失敗：{data.get('message', '未知錯誤')}")
    return data["data"]["session_token"]

def do_signin(session_token: str) -> dict:
    url = "https://api.gamer.com.tw/mobile_app/bahamut/v1/signin.php"
    headers = {
        "User-Agent": "BahamutApp/3.3.1 (Android)",
        "Cookie": f"session={session_token}"
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        print("正在登入巴哈姆特...")
        token = get_session_token()
        print(f"登入成功，Token: {token[:8]}...")

        print("正在執行簽到...")
        result = do_signin(token)
        print(f"簽到結果：{result}")

        msg = f"簽到時間：{now}\n回應內容：{result}"
        send_email("✅ 巴哈每日簽到成功", msg)

    except Exception as e:
        error_msg = f"錯誤時間：{now}\n錯誤訊息：{str(e)}"
        print(f"發生錯誤：{e}")
        send_email("❌ 巴哈每日簽到失敗", error_msg)
        raise

if __name__ == "__main__":
    main()
