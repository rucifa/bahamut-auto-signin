import requests
import smtplib
import os
import json
import base64
import re
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

def get_fresh_csrf_token(session: requests.Session) -> str:
    """從巴哈首頁動態取得最新 CSRF Token"""
    print("正在從首頁取得最新 CSRF Token...")
    resp = session.get("https://www.gamer.com.tw/", timeout=15)
    
    # 方式1：從回應的 Set-Cookie 找新的 CSRF Token
    new_cookie = resp.headers.get("Set-Cookie", "")
    match = re.search(r"ckBahamutCsrfToken=([^;]+)", new_cookie)
    if match:
        token = match.group(1)
        print(f"從 Set-Cookie 取得 CSRF Token：{token[:8]}...")
        return token

    # 方式2：從 HTML 內容找 CSRF Token
    match = re.search(r'csrfToken["\s:=]+["\']([^"\']+)["\']', resp.text)
    if match:
        token = match.group(1)
        print(f"從 HTML 取得 CSRF Token：{token[:8]}...")
        return token

    # 方式3：從原本 Cookie 取（最後手段）
    for item in COOKIE.split(";"):
        item = item.strip()
        if item.startswith("ckBahamutCsrfToken="):
            token = item.split("=", 1)[1]
            print(f"使用原始 Cookie 的 CSRF Token：{token[:8]}...")
            return token

    print("⚠️ 找不到 CSRF Token")
    return ""

def do_signin():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW,zh;q=0.9",
        "Referer": "https://www.gamer.com.tw/",
        "Origin": "https://www.gamer.com.tw",
        "X-Requested-With": "XMLHttpRequest",
    })

    # 帶入原始 Cookie
    session.headers.update({"Cookie": COOKIE})

    # 動態取得最新 CSRF Token
    csrf_token = get_fresh_csrf_token(session)

    # 更新 Session 的 CSRF Token Header
    session.headers.update({"X-CSRF-Token": csrf_token})

    url = "https://api.gamer.com.tw/user/v1/signin.php"

    # 嘗試 GET 和 POST 兩種方式
    for method in ["GET", "POST"]:
        try:
            print(f"嘗試 [{method}] {url}")
            if method == "GET":
                resp = session.get(url, params={"csrf_token": csrf_token}, timeout=15)
            else:
                resp = session.post(url, data={"csrf_token": csrf_token}, timeout=15)

            print(f"狀態碼：{resp.status_code}")

            if resp.status_code != 200:
                print(f"非 200，跳過")
                continue

            text = resp.text.strip()
            if text.lower().startswith("<!doctype"):
                print("回傳 HTML 錯誤頁，跳過")
                continue

            try:
                data = resp.json()
                print(f"JSON 回應：{data}")

                if "error" in data:
                    code = data["error"].get("status", "")
                    msg = data["error"].get("message", "未知錯誤")
                    print(f"API 錯誤：{code} - {msg}")
                    continue

                print("簽到成功！")
                return data

            except Exception:
                print(f"純文字回應：{text[:100]}")
                print("簽到成功！")
                return text

        except Exception as e:
            print(f"請求例外：{e}")
            continue

    raise Exception(
        "CSRF Token 驗證持續失敗\n"
        "可能原因：Cookie 已失效，請重新從瀏覽器取得並更新 GitHub Secret"
    )

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
