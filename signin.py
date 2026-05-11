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
    answer2 = try_parse_answer(article_text) or try_parse_answer(resp2.text)
    if answer2:
        note = f"文章頁取得，sn={csn}"
        print(f"解析到答案：{answer2}，{note}")
        return answer2, note

    print(f"[DEBUG] 文章頁內容前 800 字：{resp2.text[:800]}")
    raise Exception(f"找到文章（sn={csn}，標題：{title}）但無法解析答案，格式可能已變更")



def main():
    now = (datetime.now(tz=timezone.utc) + timedelta(hours=8)).strftime(
        "%Y-%m-%d %H:%M:%S (台灣時間)"
    )
    log_url = get_log_url()

    exp_date, days_left, username, userid = get_cookie_expiry()
    print(f"帳號：{username}（ID：{userid}）")
    print(f"Cookie 到期日：{exp_date}，剩餘 {days_left} 天")

    # ── 自動取得最新 CSRF Token ──────────────────────────────────
    baharune = get_baharune()
    if not baharune:
        body = (
            f"帳號：{username}（ID：{userid}）\n"
            f"執行時間：{now}\n\n"
            f"❌ Cookie 中缺少 BAHARUNE，請重新複製 Cookie 並更新 GitHub Secrets。\n\n"
            f"完整 Log：{log_url}"
        )
        send_email("❌ 巴哈簽到失敗：BAHARUNE 缺失", body)
        raise Exception("BAHARUNE 缺失，請更新 Cookie")

    csrf_token = fetch_fresh_csrf_token(baharune)
    print(f"[DEBUG] CSRF Token：{'有值' if csrf_token else '❌ 無法取得'}")

    if not csrf_token:
        body = (
            f"帳號：{username}（ID：{userid}）\n"
            f"執行時間：{now}\n\n"
            f"❌ 無法從巴哈首頁取得 CSRF Token，可能是 BAHARUNE 已失效。\n\n"
            f"請重新複製 Cookie 並更新 GitHub Secrets 的 BAHAMUT_COOKIE。\n\n"
            f"完整 Log：{log_url}"
        )
        send_email("❌ 巴哈簽到失敗：CSRF Token 無法取得", body)
        raise Exception("無法取得 CSRF Token，請更新 Cookie")

    if days_left < 0:
        expiry_warning = f"\n\n⚠️ Cookie 已過期（{exp_date}），請立即更新！"
    elif days_left <= 7:
        expiry_warning = f"\n\n⚠️ Cookie 將於 {exp_date} 到期（剩餘 {days_left} 天），請盡快更新！"
    else:
        expiry_warning = f"\n\nCookie 到期日：{exp_date}（剩餘 {days_left} 天）"

    signin_result = "未執行"
    streak_info   = ""
    answer_result = "未執行"
    has_error     = False

    # ── 簽到 ──────────────────────────────────────────────────────
    try:
        print("\n========== 簽到 ==========")
        status_data    = get_signin_status(csrf_token)
        days           = status_data.get("days", "?")
        already_signed = status_data.get("signin", False)
        streak_info    = f"✨ 已連續簽到 {days} 天"
        print(f"{streak_info}，今日已簽到：{already_signed}")

        if already_signed:
            print("今日已簽到，略過簽到步驟")
            signin_result = "✅ 今日已簽到"
        else:
            print("正在執行簽到...")
            do_signin(csrf_token)
            status_data2  = get_signin_status(csrf_token)
            days          = status_data2.get("days", days)
            streak_info   = f"✨ 已連續簽到 {days} 天"
            signin_result = "✅ 成功"
            print(f"簽到完成，{streak_info}")

    except Exception as e:
        signin_result = f"❌ 失敗：{e}"
        has_error = True
        print(f"[ERROR] 簽到失敗：{e}")

    # ── 動畫瘋答題 ────────────────────────────────────────────────
    print("\n========== 動畫瘋答題 ==========")
    try:
        answer, note = fetch_answer_from_blackxblue()
        print(f"今日答案：{answer}（{note}）")
        answer_result = (
            f"📋 今日答案：{answer}\n"
            f"請手動前往動畫瘋作答：https://ani.gamer.com.tw/"
        )
    except Exception as e:
        answer_result = f"❌ 抓取答案失敗：{e}"
        print(f"[ERROR] {answer_result}")

    # ── 發送 Email ────────────────────────────────────────────────
    print("\n========== 發送 Email ==========")
    subject = "✅ 巴哈每日任務完成" if not has_error else "⚠️ 巴哈每日任務部分失敗"
    body = (
        f"帳號：{username}（ID：{userid}）\n"
        f"執行時間：{now}\n"
        f"每日簽到：{signin_result}\n"
        + (f"{streak_info}\n" if streak_info else "")
        + f"動畫瘋答題：{answer_result}"
        + expiry_warning + "\n\n"
        + f"完整 Log：{log_url}"
    )
    send_email(subject, body)

    if has_error:
        raise Exception(f"簽到失敗：{signin_result}")



if __name__ == "__main__":
    main()
