import requests
import smtplib
import os
import json
import base64
import re
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta

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


def get_csrf_token() -> str:
    for item in COOKIE.split(";"):
        item = item.strip()
        if item.startswith("ckBahamutCsrfToken="):
            return item.split("=", 1)[1]
    return ""


def build_headers(referer: str = "https://www.gamer.com.tw/") -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        "Cookie": COOKIE,
        "Referer": referer,
        "Origin": "https://www.gamer.com.tw",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW,zh;q=0.9",
        "X-CSRF-Token": get_csrf_token(),
    }


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

    if text.lower().startswith("<!"):
        return False, "回應為 HTML（可能未登入）"

    try:
        data = json.loads(text)
        print(f"[DEBUG] 簽到回應 JSON：{json.dumps(data, ensure_ascii=False)}")
        return True, data
    except Exception:
        print(f"[DEBUG] 簽到回應（非 JSON）：{text[:300]}")
        return True, text


def do_signin():
    csrf_token = get_csrf_token()
    headers = build_headers("https://home.gamer.com.tw/")

    endpoints = [
        ("POST", "https://home.gamer.com.tw/ajax/signin.php"),
        ("GET",  "https://home.gamer.com.tw/ajax/signin.php"),
        ("POST", "https://www.gamer.com.tw/ajax/signin.php"),
    ]

    for method, url in endpoints:
        try:
            success, result = try_endpoint(method, url, headers, csrf_token)
            if success:
                return result
        except Exception as e:
            print(f"端點 {url} 失敗：{e}")

    raise Exception("所有簽到端點均失敗")


def fetch_answer_from_blackxblue() -> str:
    list_url = "https://home.gamer.com.tw/ajax/getCreationArticleList.php?owner=blackxblue&c=370818&page=1"
    headers = build_headers("https://home.gamer.com.tw/")

    resp = requests.get(list_url, headers=headers, timeout=15)
    resp.raise_for_status()

    data = resp.json()
    articles = data.get("data", [])
    if not articles:
        raise Exception("blackXblue 小屋沒有找到文章列表")

    latest_sn = articles[0].get("sn", "")
    if not latest_sn:
        raise Exception("無法取得最新文章 sn")

    print(f"最新文章 sn：{latest_sn}")

    article_url = f"https://home.gamer.com.tw/creationDetail.php?sn={latest_sn}"
    resp2 = requests.get(article_url, headers=headers, timeout=15)
    resp2.raise_for_status()

    content = resp2.text

    patterns = [
        r'答案[：:是為]\s*([ABCD])',
        r'[Aa]nswer[：:\s]+([ABCD])',
        r'正確答案[：:]\s*([ABCD])',
        r'選\s*([ABCD])\s*(?:是正確|為正確|答)',
    ]

    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            answer = match.group(1).upper()
            print(f"解析到答案：{answer}")
            return answer

    raise Exception("無法從 blackXblue 文章中解析出答案，格式可能已變更")


def get_anime_question() -> dict:
    url = "https://api.gamer.com.tw/anime/v1/questionnaire.php"
    headers = build_headers("https://ani.gamer.com.tw/")
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    print(f"問題取得狀態：{data.get('status', '未知')}")
    return data


def submit_anime_answer(answer: str) -> dict:
    url = "https://api.gamer.com.tw/anime/v1/questionnaire.php"
    headers = build_headers("https://ani.gamer.com.tw/")
    resp = requests.post(url, headers=headers,
                         data={"answer": answer}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        print(f"答題回應：{data.get('status', '未知')} / {data.get('message', '無')}")
    else:
        print("答題回應非 JSON")
    return data


def do_anime_answer() -> str:
    try:
        question_data = get_anime_question()

        status = question_data.get("status", 0)
        if status == 0:
            msg = question_data.get("message", "")
            if "已作答" in msg or "already" in msg.lower():
                print("今日動畫瘋已答題，略過")
                return "今日已答題（略過）"
            if "沒有" in msg or "無題" in msg:
                print("今日動畫瘋無題目")
                return "今日無題目"

        answer = fetch_answer_from_blackxblue()
        result = submit_anime_answer(answer)
        result_msg = result.get("message", "無回應訊息") if isinstance(result, dict) else str(result)
        return f"答題完成（答案：{answer}），回應：{result_msg}"

    except requests.exceptions.HTTPError as e:
        print(f"動畫瘋答題 API 不可用（{e}），略過")
        return "⏭️ 跳過（API 暫不可用）"
    except Exception as e:
        print(f"動畫瘋答題失敗：{e}")
        return f"⏭️ 跳過（{e}）"


# ────────────────────────────────────────────

def main():
    now = (datetime.now(tz=timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S (台灣時間)")
    log_url = get_log_url()

    exp_date, days_left = get_cookie_expiry()
    print(f"Cookie 到期日：{exp_date}，剩餘 {days_left} 天")

    if days_left < 0:
        expiry_warning = "\n\n⚠️ Cookie 已過期（" + exp_date + "），請立即更新！"
    elif days_left <= 7:
        expiry_warning = "\n\n⚠️ Cookie 將於 " + exp_date + " 到期（剩餘 " + str(days_left) + " 天），請盡快更新！"
    else:
        expiry_warning = "\n\nCookie 到期日：" + exp_date + "（剩餘 " + str(days_left) + " 天）"

    signin_result = "未執行"
    answer_result = "未執行"
    has_error = False

    # ── 簽到 ──
    try:
        print("正在執行簽到...")
        do_signin()
        signin_result = "✅ 成功"
        print("簽到完成")
    except Exception as e:
        signin_result = f"❌ 失敗：{e}"
        has_error = True
        print(f"簽到失敗：{e}")

    # ── 動畫瘋答題 ──
    print("正在執行動畫瘋答題...")
    answer_result = do_anime_answer()

    # ── 發送 Email 通知 ──
    subject = "✅ 巴哈每日任務完成" if not has_error else "⚠️ 巴哈每日任務部分失敗"
    body = (
        f"執行時間：{now}\n"
        f"每日簽到：{signin_result}\n"
        f"動畫瘋答題：{answer_result}"
        + expiry_warning + "\n\n"
        + f"完整 Log：{log_url}"
    )

    send_email(subject, body)

    if has_error:
        raise Exception(f"簽到失敗：{signin_result}")


if __name__ == "__main__":
    main()
