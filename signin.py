import requests
import smtplib
import os
import json
import base64
from email.mime.text import MIMEText
from datetime import datetime, timezone

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

def get_log_url() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if repo and run_id:
        return f"https://github.com/{repo}/actions/runs/{run_id}"
    return "https://github.com/你的帳號/你的Repo/actions"

def get_cookie_expiry() -> tuple:
    try:
        for item in COOKIE.split(";"):
            item = item.strip()
            if item.startswith("BAHARUNE="):
                jwt = item.split("=", 1)[1]
                payload_b64 = jwt.split(".")[1]
                payload_b64 += "=" * (4 - len(payload_b64) % 4)
                payload = json.loads(base64.b64decode(payload_b64))
                exp_timestamp = payload.get("exp", 0)
                exp_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc).astimezone()
                now = datetime.now(tz=timezone.utc)
                days_left = (datetime.fromtimestamp(exp_timestamp, tz=timezone.utc) - now).days
                return exp_dt.strftime("%Y-%m-%d"), days_left
    except Exception as e:
        print(f"解析 JWT 失敗：{e}")
    return "未知", -1

def do_signin():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        "Cookie": COOKIE,
        "Referer": "https://www.gamer.com.tw/",
        "Origin": "https://www.gamer.com.tw",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW,zh;q=0.9",
    }

    endpoints = [
        ("GET",  "https://www.gamer.com.tw/ajax/click_signin.php"),
        ("POST", "https://www.gamer.com.tw/ajax/click_signin.php"),
    ]

    for method, url in endpoints:
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=15)
            else:
                resp = requests.post(url, headers=headers, timeout=15)

            print(f"[{method}] {url} → {resp.status_code}")

            if resp.status_code != 200:
                print(f"非 200，跳過")
                continue

            text = resp.text.strip()

            # 回傳 HTML 錯誤頁代表端點不存在
            if text.lower().startswith("<!doctype") or "找不到網頁" in text:
                print(f"回傳 HTML 錯誤頁，跳過")
                continue

            # 非 HTML → 視為簽到成功（click_signin.php 正常回應）
            print(f"回應內容：{text[:100]}")
            print(f"簽到成功，端點：[{method}] {url}")
            return

        except Exception as e:
            print(f"端點例外：{e}")
            continue

    raise Exception("簽到失敗，請重新從瀏覽器取得 Cookie 更新 GitHub Secret")

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_url = get_log_url()

    exp_date, days_left = get_cookie_expiry()
    print(f"Cookie 到期日：{exp_date}，剩餘 {days_left} 天")

    if days_left < 0:
        expiry_warning = f"\n\n⚠️ Cookie 已過期（{exp_date}），請立即更新！"
    elif days_left <= 7:
        expiry_warning = f"\n\n⚠️ Cookie 將於 {exp_date} 到期（剩餘 {days_left} 天），請盡快更新！"
    else:
        expiry_warning = f"\n\nCookie 到期日：{exp_date}（剩餘 {days_left} 天）"

    try:
        print("正在執行簽到...")
        do_signin()

        body = (
            f"簽到時間：{now}"
            f"{expiry_warning}\n\n"
            f"完整 Log：{log_url}"
        )
        print("簽到成功")
        send_email("✅ 巴哈每日簽到成功", body)

    except Exception as e:
        error_msg = (
            f"簽到時間：{now}\n"
            f"錯誤訊息：{str(e)}"
            f"{expiry_warning}\n\n"
            f"完整 Log：{log_url}"
        )
        print(f"發生錯誤：{e}")
        send_email("❌ 巴哈每日簽到失敗", error_msg)
        raise

if __name__ == "__main__":
    main()
