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

def get_csrf_token() -> str:
    for item in COOKIE.split(";"):
        item = item.strip()
        if item.startswith("ckBahamutCsrfToken="):
            return item.split("=", 1)[1]
    return ""

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

def try_endpoint(method: str, url: str, headers: dict, csrf_token: str):
    if method == "GET":
        resp = requests.get(url, headers=headers, timeout=15)
    else:
        resp = requests.post(url, headers=headers,
                             data={"csrf_token": csrf_token}, timeout=15)

    print(f"[{method}] {url} → {resp.status_code}")

    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}"

    text = resp.text.strip()

    if text.lower().startswith("<!doctype") or "找不到網頁" in text:
        return False, "回傳 HTML 錯誤頁（端點不存在）"

    try:
        data = resp.json()
        print(f"JSON 回應：{data}")
        return True, data
    except Exception:
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

    # 只測試 www.gamer.com.tw 的端點
    endpoints = [
        ("GET",  "https://www.gamer.com.tw/ajax/click_signin.php"),
        ("POST", "https://www.gamer.com.tw/ajax/click_signin.php"),
    ]

    for method, url in endpoints:
        try:
            success, result = try_endpoint(method, url, headers, csrf_token)
            if success:
                return result
        except Exception as e:
            print(f"端點例外：{e}")
            continue

    raise Exception("簽到失敗，請手動從瀏覽器 F12 找出正確的簽到 API")

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
        print(f"簽到成功")
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
