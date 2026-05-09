import requests
import smtplib
import os
import json
import base64
import re
from datetime import datetime, timezone, timedelta, date
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
                exp_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc).astimezone()
                now = datetime.now(tz=timezone.utc)
                days_left = (datetime.fromtimestamp(exp_timestamp, tz=timezone.utc) - now).days
                username = payload.get("username", "未知")
                userid = payload.get("userid", payload.get("uid", "未知"))
                return exp_dt.strftime("%Y-%m-%d"), days_left, username, userid
    except Exception as e:
        print(f"解析 JWT 失敗：{e}")
    return "未知", -1, "未知", "未知"


def get_csrf_token() -> str:
    for item in COOKIE.split(";"):
        item = item.strip()
        if item.startswith("ckBahamutCsrfToken="):
            return item.split("=", 1)[1]
    return ""


def build_headers(referer: str = "https://www.gamer.com.tw/", origin: str = "https://www.gamer.com.tw") -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        "Cookie": COOKIE,
        "Referer": referer,
        "Origin": origin,
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW,zh;q=0.9",
        "X-CSRF-Token": get_csrf_token(),
    }


def get_signin_status() -> dict:
    url = "https://www.gamer.com.tw/ajax/signin.php"
    print(f"[DEBUG] 查詢簽到狀態 → POST {url}")
    resp = requests.post(url, headers=build_headers(), data={"action": "2"}, timeout=15)
    print(f"[DEBUG] 回應 HTTP {resp.status_code}")
    resp.raise_for_status()
    result = resp.json()
    print(f"[DEBUG] 簽到狀態 JSON：{json.dumps(result, ensure_ascii=False)}")
    if "error" in result:
        raise Exception(result["error"].get("message", "未知錯誤"))
    return result.get("data", {})


def do_signin() -> dict:
    url = "https://www.gamer.com.tw/ajax/signin.php"
    print(f"[DEBUG] 執行簽到 → POST {url}")
    resp = requests.post(url, headers=build_headers(), data={"action": "1"}, timeout=15)
    print(f"[DEBUG] 回應 HTTP {resp.status_code}")
    resp.raise_for_status()
    result = resp.json()
    print(f"[DEBUG] 簽到結果 JSON：{json.dumps(result, ensure_ascii=False)}")
    if "error" in result:
        raise Exception(result["error"].get("message", "未知錯誤"))
    return result.get("data", result)


def extract_title(content: str) -> str:
    """從 HTML 中抓出文章標題，供 debug 使用"""
    m = re.search(r'<title>(.*?)</title>', content)
    return m.group(1).strip() if m else "（無標題）"


def try_parse_answer(content: str) -> str | None:
    """從文章內容嘗試解析出答案（A/B/C/D）"""
    patterns = [
        r'答[案:]\s*([A-D])',
        r'\b([1-4ABCD])\b',
        r'([1-4ABCD])',
        r'A(?:nswer)?[:\s]*([1-4ABCD])',
        r'([ABCD])?',
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            val = match.group(1).upper()
            return "ABCD"[int(val) - 1] if val in "1234" else val
    return None


def fetch_answer_from_blackxblue() -> tuple[str, str]:
    """
    回傳 (answer, note)
    - answer: 給 Email 顯示的簡潔答案，例如 "C"
    - note:   給 DEBUG print 的詳細資訊，例如 "精確比對，sn=6331391"
    """
    headers = build_headers("https://home.gamer.com.tw/", "https://home.gamer.com.tw")
    headers.pop("X-Requested-With", None)
    headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"

    BASE_DATE = date(2026, 5, 9)
    BASE_SN = 6331391

    today = datetime.now(tz=timezone.utc + timedelta(hours=8)).date()
    delta = (today - BASE_DATE).days
    estimated_sn = BASE_SN + delta
    print(f"[DEBUG] 今日={today} 估算sn={estimated_sn}（BASE_SN={BASE_SN} + delta={delta}）")

    today_str_formats = [
        today.strftime("%m/%d"),
        today.strftime("-%m-%d"),
        today.strftime("%m%d"),
        today.strftime("%Y-%m-%d"),
    ]

    tried_sns = []
    for offset in range(-7, 8):
        sn = estimated_sn + offset
        tried_sns.append(sn)
        article_url = f"https://home.gamer.com.tw/artwork.php?sn={sn}"
        print(f"[DEBUG] 嘗試 sn={sn}")
        try:
            resp = requests.get(article_url, headers=headers, timeout=15)
        except Exception as e:
            print(f"[DEBUG] sn={sn} 請求失敗：{e}")
            continue
        if resp.status_code != 200:
            print(f"[DEBUG] sn={sn} HTTP {resp.status_code}")
            continue
        content = resp.text
        is_today = any(s in content for s in today_str_formats)
        is_blackxblue = "blackxblue" in content
        print(f"[DEBUG] sn={sn} is_today={is_today} is_blackxblue={is_blackxblue}")
        if not is_today or not is_blackxblue:
            continue
        title = extract_title(content)
        parsed = try_parse_answer(content)
        print(f"[DEBUG] sn={sn} 標題={title} 解析答案={parsed}")
        if parsed:
            note = f"精確比對，sn={sn}"
            print(f"[DEBUG] 答案={parsed}，{note}")
            return parsed, note
        print(f"[DEBUG] sn={sn} 找到 blackxblue 文章但無法解析，前800字：{content[:800]}")
        raise Exception(f"sn={sn} 標題《{title}》找到 blackxblue 文章但 regex 無法解析答案")

    # 精確比對失敗，放寬只找 blackxblue
    print(f"[DEBUG] 精確比對失敗，嘗試過：{tried_sns}，改為放寬搜尋...")
    for offset in range(-5, 6):
        sn = estimated_sn + offset
        article_url = f"https://home.gamer.com.tw/artwork.php?sn={sn}"
        try:
            resp = requests.get(article_url, headers=headers, timeout=15)
        except Exception:
            continue
        if resp.status_code != 200:
            continue
        content = resp.text
        if "blackxblue" not in content:
            continue
        title = extract_title(content)
        parsed = try_parse_answer(content)
        print(f"[DEBUG] 放寬搜尋 sn={sn} 標題={title} 解析答案={parsed}")
        if parsed:
            note = f"放寬比對，sn={sn}"
            print(f"[DEBUG] 答案={parsed}，{note}")
            return parsed, note

    raise Exception(
        f"搜尋範圍 sn={estimated_sn - 7}～{estimated_sn + 7} 均未找到符合的 blackxblue 文章 "
        f"（嘗試過：{tried_sns}，BASE_DATE={BASE_DATE}，今日={today}，BASE_SN 可能需要更新）"
    )


def main():
    now = datetime.now(tz=timezone.utc + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    log_url = get_log_url()
    exp_date, days_left, username, userid = get_cookie_expiry()
    print(f"帳號：{username}（ID：{userid}）")
    print(f"Cookie 到期：{exp_date}，剩餘 {days_left} 天")

    if days_left <= 0:
        expiry_warning = f"⚠️ Cookie 已於 {exp_date} 過期，請立即更新！"
    elif days_left <= 7:
        expiry_warning = f"⚠️ Cookie 將於 {exp_date} 到期（剩 {days_left} 天），請盡快更新！"
    else:
        expiry_warning = f"✅ Cookie 有效期至 {exp_date}（剩 {days_left} 天）"

    signin_result = ""
    streak_info = ""
    answer_result = ""
    has_error = False

    # --- 簽到 ---
    print("=" * 40)
    try:
        status_data = get_signin_status()
        days = status_data.get("days", "?")
        already_signed = status_data.get("signin", False)
        streak_info = f"連續簽到 {days} 天"
        print(f"簽到狀態：{streak_info}，已簽到={already_signed}")
        if already_signed:
            signin_result = f"✅ 今日已簽到（{streak_info}）"
            print(signin_result)
        else:
            do_signin()
            status_data2 = get_signin_status()
            days = status_data2.get("days", days)
            streak_info = f"連續簽到 {days} 天"
            signin_result = f"✅ 簽到成功（{streak_info}）"
            print(signin_result)
    except Exception as e:
        signin_result = f"❌ 簽到失敗：{e}"
        has_error = True
        print(f"[ERROR] {signin_result}")

    # --- 答題解析 ---
    print("=" * 40)
    try:
        answer, note = fetch_answer_from_blackxblue()
        print(f"[DEBUG] 答題解析完成：答案={answer}，{note}")
        answer_result = f"📋 動畫瘋答題：今日答案為 {answer}"
    except Exception as e:
        answer_result = f"⚠️ 動畫瘋答題解析失敗：{e}"
        print(f"[ERROR] {answer_result}")

    # --- 寄出 Email ---
    print("=" * 40)
    subject = f"【巴哈】{now} 簽到通知" if not has_error else f"【巴哈】{now} ❌ 簽到異常"
    body = (
        f"帳號：{username}（ID：{userid}）\n"
        f"執行時間：{now}\n"
        f"\n"
        f"【簽到結果】\n{signin_result}\n"
        f"\n"
        f"【答題】\n{answer_result}\n"
        f"\n"
        f"【Cookie 狀態】\n{expiry_warning}\n"
        f"\n"
        f"【執行紀錄】\n{log_url}"
    )
    send_email(subject, body)

    if has_error:
        raise Exception(signin_result)


if __name__ == "__main__":
    main()
