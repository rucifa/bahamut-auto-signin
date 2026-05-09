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
    url = "https://api.gamer.com.tw/mobile_app/bahamut/v1/signin.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        "Cookie": COOKIE,
        "Referer": "https://www.gamer.com.tw/",
        "Origin": "https://www.gamer.com.tw",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW,zh;q=0.9"
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        print("正在執行簽到（使用現有 Cookie）...")
        result = do_signin()
        print(f"簽到結果：{result}")

        if result.get("data", {}).get("signin"):
            days = result.get("data", {}).get("days", "未知")
            msg = f"簽到時間：{now}\n連續簽到天數：{days} 天"
            send_email("✅ 巴哈每日簽到成功", msg)
        else:
            send_email("⚠️ 巴哈簽到回應異常，請手動確認", f"時間：{now}\n完整回應：{result}")

    except Exception as e:
        error_msg = f"錯誤時間：{now}\n錯誤訊息：{str(e)}"
        print(f"發生錯誤：{e}")
        send_email("❌ 巴哈每日簽到失敗", error_msg)
        raise

if __name__ == "__main__":
    main()
