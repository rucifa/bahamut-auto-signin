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

def is_success(data) -> tuple:
    """
    判斷 JSON 回應是否真正成功
    回傳 (成功與否, 訊息)
    """
    if not isinstance(data, dict):
        return False, f"非預期回應格式：{str(data)[:100]}"

    # 有 error 欄位代表失敗
    if "error" in data:
        code = data["error"].get("code", "")
        msg = data["error"].get("message", "未知錯誤")
        status = data["error"].get("status", "")
        return False, f"API 錯誤 [{code}] {status}：{msg}"

    # 有 data 欄位代表成功
    if "data" in data:
        days = data["data"].get("days", "")
        return True, f"連續簽到 {days} 天" if days else "簽到成功"

    # 其他情況視為不明
    return False, f"不明回應：{data}"

def do_signin():
    csrf_token = get_csrf_token()
    print(f"CSRF Token：{csrf_token[:8]}..." if csrf_token else "⚠️ 找不到 CSRF Token！")

    base_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        "Cookie": COOKIE,
        "Referer": "https://www.gamer.com.tw/",
        "Origin": "https://www.gamer.com.tw",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW,zh;q=0.9",
    }

    url = "https://api.gamer.com.tw/user/v1/signin.php"

    # 嘗試多種帶入 CSRF Token 的方式
    attempts = [
        # 方式1：放在 Header（標準做法）
        {**base_headers, "X-CSRF-Token": csrf_token, "X-Requested-With": "XMLHttpRequest"},
        # 方式2：放在 Header 換個名稱
        {**base_headers, "csrf-token": csrf_token, "X-Requested-With": "XMLHttpRequest"},
        # 方式3：放在 Header 用巴哈自定義格式
        {**base_headers, "x-bahamut-csrf": csrf_token, "X-Requested-With": "XMLHttpRequest"},
    ]

    for i, headers in enumerate(attempts, 1):
        try:
            # GET 帶 csrf_token 作為 query string
            resp = requests.get(
                url,
                params={"csrf_token": csrf_token},
                headers=headers,
                timeout=15
            )
            print(f"嘗試方式 {i}：狀態碼 {resp.status_code}")

            if resp.status_code != 200:
                print(f"非 200，跳過")
                continue

            text = resp.text.strip()
            if text.lower().startswith("<!doctype"):
                print(f"回傳 HTML 錯誤頁，跳過")
                continue

            try:
                data = resp.json()
                print(f"JSON 回應：{data}")
            except Exception:
                print(f"非 JSON 回應：{text[:100]}")
                continue

            success, msg = is_success(data)
            if success:
                return msg
            else:
                print(f"API 回報失敗：{msg}")
                # CSRF 錯誤才繼續嘗試其他方式，其他錯誤直接拋出
                if "CSRF" not in str(data):
                    raise Exception(msg)

        except requests.RequestException as e:
            print(f"請求例外：{e}")
            continue

    raise Exception(
        "CSRF Token 驗證持續失敗。\n"
        "請重新從瀏覽器取得最新 Cookie 更新 GitHub Secret，\n"
        "或從 F12 Network 找出實際簽到 API。"
    )

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        print("正在執行簽到...")
        result_msg = do_signin()

        body = f"簽到時間：{now}\n{result_msg}"
        print(f"簽到成功：{body}")
        send_email("✅ 巴哈每日簽到成功", body)

    except Exception as e:
        repo = os.environ.get("GITHUB_REPOSITORY", "你的帳號/你的Repo")
        run_id = os.environ.get("GITHUB_RUN_ID", "")
        log_url = f"https://github.com/{repo}/actions/runs/{run_id}"

        error_msg = (
            f"簽到時間：{now}\n"
            f"錯誤訊息：{str(e)}\n\n"
            f"完整 Log：{log_url}"
        )
        print(f"發生錯誤：{e}")
        send_email("❌ 巴哈每日簽到失敗", error_msg)
        raise

if __name__ == "__main__":
    main()
