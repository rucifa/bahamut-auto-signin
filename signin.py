import requests
import smtplib
import os
import json
import base64
import re
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText


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
    return "https://github.com/rucifa/bahamut-auto-signin/actions"



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
                now = datetime.now(tz=timezone.utc)
                days_left = (datetime.fromtimestamp(exp_timestamp, tz=timezone.utc) - now).days
                exp_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                username = payload.get("username", "未知")
                userid = payload.get("userid", payload.get("uid", "未知"))
                return exp_dt.strftime("%Y-%m-%d"), days_left, username, userid
    except Exception as e:
        print(f"解析 JWT 失敗：{e}")
    return "未知", -1, "未知", "未知"



def get_baharune() -> str:
    for item in COOKIE.split(";"):
        item = item.strip()
        if item.startswith("BAHARUNE="):
            return item.split("=", 1)[1]
    return ""



def fetch_fresh_csrf_token(baharune: str) -> str:
    """
    用 requests.Session + BAHARUNE 訪問巴哈首頁
    從 session.cookies 取得最新的 ckBahamutCsrfToken
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9",
    })
    session.cookies.set("BAHARUNE", baharune, domain="www.gamer.com.tw")

    try:
        resp = session.get("https://www.gamer.com.tw/", timeout=15, allow_redirects=True)
        print(f"[DEBUG] 首頁回應 HTTP {resp.status_code}")
        print(f"[DEBUG] Session cookies：{dict(session.cookies)}")

        # 從 session cookie jar 取得
        token = session.cookies.get("ckBahamutCsrfToken")
        if token:
            print(f"[DEBUG] 從 session cookies 取得新 CSRF Token：{token[:10]}...")
            return token

        # 備援：從 HTML 找
        m = re.search(r'ckBahamutCsrfToken["\s:=\']+([a-zA-Z0-9_\-]{10,})', resp.text)
        if m:
            token = m.group(1).strip()
            print(f"[DEBUG] 從 HTML 取得 CSRF Token：{token[:10]}...")
            return token

        print(f"[DEBUG] HTML 片段（前 500 字）：{resp.text[:500]}")

    except Exception as e:
        print(f"[DEBUG] 取得 CSRF Token 失敗：{e}")
    return ""



def build_headers(csrf_token: str,
                  referer: str = "https://www.gamer.com.tw/",
                  origin: str = "https://www.gamer.com.tw") -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        "Cookie": COOKIE,
        "Referer": referer,
        "Origin": origin,
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW,zh;q=0.9",
        "X-CSRF-Token": csrf_token,
    }



def get_signin_status(csrf_token: str) -> dict:
    url = "https://www.gamer.com.tw/ajax/signin.php"
    print(f"[DEBUG] 查詢簽到狀態 → POST {url}")
    resp = requests.post(url, headers=build_headers(csrf_token), data={"action": "2"}, timeout=15)
    print(f"[DEBUG] 回應 HTTP {resp.status_code}")
    resp.raise_for_status()
    result = resp.json()
    print(f"[DEBUG] 簽到狀態 JSON：{json.dumps(result, ensure_ascii=False)}")
    if "error" in result:
        raise Exception(result["error"].get("message", "未知錯誤"))
    return result.get("data", {})



def do_signin(csrf_token: str) -> dict:
    url = "https://www.gamer.com.tw/ajax/signin.php"
    print(f"[DEBUG] 執行簽到 → POST {url}")
    resp = requests.post(url, headers=build_headers(csrf_token), data={"action": "1"}, timeout=15)
    print(f"[DEBUG] 回應 HTTP {resp.status_code}")
    resp.raise_for_status()
    result = resp.json()
    print(f"[DEBUG] 簽到結果 JSON：{json.dumps(result, ensure_ascii=False)}")
    if "error" in result:
        raise Exception(result["error"].get("message", "未知錯誤"))
    return result.get("data", result)



def try_parse_answer(content: str) -> str | None:
    patterns = [
        r'A[:：]([1-4ABCD])',
        r'答案[：:是為]\s*([1-4ABCD])',
        r'正確答案[：:]\s*([1-4ABCD])',
        r'[Aa]nswer[：:\s]+([1-4ABCD])',
        r'選\s*([ABCD])\s*(?:是正確|為正確|答)',
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            val = match.group(1).upper()
            return ['A', 'B', 'C', 'D'][int(val) - 1] if val in ['1', '2', '3', '4'] else val
    return None



def fetch_answer_from_blackxblue() -> tuple[str, str]:
    api_url = "https://api.gamer.com.tw/home/v2/creation_list.php?owner=blackxblue&row=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        "Cookie": COOKIE,
        "Referer": "https://home.gamer.com.tw/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW,zh;q=0.9",
    }

    today = (datetime.now(tz=timezone.utc) + timedelta(hours=8)).date()
    today_str_formats = [
        today.strftime("%m/%d"),
        today.strftime("%-m/%-d"),
        today.strftime("%Y/%m/%d"),
        today.strftime("%Y-%m-%d"),
    ]
    print(f"[DEBUG] 今日台灣日期：{today}，比對格式：{today_str_formats}")
    print(f"[DEBUG] 抓取 API：{api_url}")

    try:
        resp = requests.get(api_url, headers=headers, timeout=15)
    except Exception as e:
        raise Exception(f"無法抓取創作列表 API：{e}")
    if resp.status_code != 200:
        raise Exception(f"創作列表 API 回應 HTTP {resp.status_code}")

    data = resp.json()
    items = data.get("data", {}).get("list", [])
    print(f"[DEBUG] API 回傳文章數：{len(items)}")
    if not items:
        raise Exception("API 回傳列表為空")

    item = items[0]
    csn     = item.get("csn", "未知")
    title   = item.get("title", "")
    content = item.get("content", "")
    ctime   = item.get("ctime", "")
    print(f"[DEBUG] 最新文章 sn={csn}，標題={title}，時間={ctime}")
    print(f"[DEBUG] content 內容：{content[:300]}")

    is_today = any(s in title or s in content for s in today_str_formats)
    print(f"[DEBUG] 是今天的文章：{is_today}")
    if not is_today:
        raise Exception(
            f"最新文章不是今天（{today}）的，sn={csn}，標題={title}，時間={ctime}\n"
            f"blackxblue 可能今天尚未發文"
        )

    answer = try_parse_answer(content)
    if answer:
        note = f"API 直接取得，sn={csn}"
        print(f"解析到答案：{answer}，{note}")
        return answer, note

    print(f"[DEBUG] API content 無法解析，改進文章頁 sn={csn}")
    article_url = f"https://home.gamer.com.tw/artwork.php?sn={csn}"
    try:
        resp2 = requests.get(article_url, headers=headers, timeout=15)
    except Exception as e:
        raise Exception(f"無法抓取文章頁（sn={csn}）：{e}")

    article_text = re.sub(r'<[^>]+>', ' ', resp2.text)
    answer2 = try_parse_an
