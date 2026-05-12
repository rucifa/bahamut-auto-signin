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
        print(f"[DIAG] JWT 解析失敗：{e}")
    return "未知", -1, "未知", "未知"

def get_baharune() -> str:
    for item in COOKIE.split(";"):
        item = item.strip()
        if item.startswith("BAHARUNE="):
            return item.split("=", 1)[1]
    return ""

def get_csrf_from_home_meta(headers: dict) -> str:
    try:
        resp = requests.get("https://www.gamer.com.tw/", headers=headers, timeout=10)
        print(f"[DEBUG] 首頁回應：HTTP {resp.status_code}, 長度 {len(resp.text)}")
        m = re.search(r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']', resp.text, re.I)
        if m:
            token = m.group(1)
            print(f"[DIAG] ✅ 首頁 meta CSRF：{token[:10]}...")
            return token
        print("[DIAG] ❌ 首頁無 csrf-token meta")
        return ""
    except Exception as e:
        print(f"[DIAG] 首頁 CSRF 失敗：{e}")
        return ""

def fetch_csrf_token_from_api(baharune: str) -> tuple[str, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        "Cookie": COOKIE,
        "Referer": "https://www.gamer.com.tw/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW,zh;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
    }

    # 第1層：API 端點
    urls_to_try = [
        "https://api.gamer.com.tw/ajax/csrf_token.php",
        "https://www.gamer.com.tw/ajax/csrf_token.php",
    ]
    for url in urls_to_try:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            print(f"[DEBUG] CSRF API ({url})：HTTP {resp.status_code}")
            print(f"[DEBUG] CSRF 內容前300：{resp.text[:300]}")
            if resp.status_code == 200 and len(resp.text) < 500:
                try:
                    data = resp.json()
                    token = (
                        data.get("data", {}).get("token", "")
                        or data.get("token", "")
                        or data.get("csrf_token", "")
                    )
                    if token:
                        print(f"[DIAG] ✅ API CSRF：{token[:10]}...")
                        return token, "API"
                except Exception:
                    pass
                m = re.search(r'["\']?token["\']?\s*[=:]\s*["\']([a-zA-Z0-9_\-]{10,})["\']', resp.text)
                if m:
                    token = m.group(1)
                    print(f"[DIAG] ✅ API 正則：{token[:10]}...")
                    return token, "API_REGEX"
        except Exception as e:
            print(f"[DEBUG] API {url} 異常：{e}")

    # 第2層：首頁 meta
    token = get_csrf_from_home_meta(headers)
    if token:
        return token, "HOME_META"

    # 第3層：Cookie 備援
    for item in COOKIE.split(";"):
        item = item.strip()
        if item.startswith("ckBahamutCsrfToken="):
            token = item.split("=", 1)[1]
            print(f"[DIAG] 🔄 Cookie CSRF：{token[:10]}...（備援）")
            return token, "COOKIE_BACKUP"

    return "", "FAILED"

def test_bahamut_session(csrf_token: str, headers: dict) -> str:
    try:
        resp = requests.get("https://home.gamer.com.tw/", headers=headers, timeout=10)
        print(f"[DEBUG] SESSION 檢查 HTTP：{resp.status_code}, 長度：{len(resp.text)}")
        if resp.status_code == 302 or "請先登入" in resp.text or "登入巴哈姆特" in resp.text:
            return "❌ SESSION失效（被登出）"
        if "rucifa" in resp.text:
            return "✅ SESSION正常"
        return "⚠️ SESSION未知（無法確認）"
    except Exception as e:
        return f"❌ SESSION測試失敗：{e}"

def build_cookie_header(csrf_token: str) -> str:
    parts = []
    for item in COOKIE.split(";"):
        item = item.strip()
        if item.startswith("ckBahamutCsrfToken="):
            continue
        if item:
            parts.append(item)
    if csrf_token:
        parts.append(f"ckBahamutCsrfToken={csrf_token}")
    return "; ".join(parts)

def build_headers(csrf_token: str) -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        "Cookie": build_cookie_header(csrf_token),
        "Referer": "https://www.gamer.com.tw/",
        "Origin": "https://www.gamer.com.tw",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW,zh;q=0.9",
        "X-CSRF-Token": csrf_token,
    }

def get_signin_status(csrf_token: str) -> dict:
    url = "https://www.gamer.com.tw/ajax/signin.php"
    print(f"[DEBUG] 簽到狀態 → POST {url}")
    resp = requests.post(
        url, headers=build_headers(csrf_token),
        data={"action": "2", "bahamutCsrfToken": csrf_token}, timeout=10
    )
    print(f"[DEBUG] 簽到HTTP：{resp.status_code}")
    resp.raise_for_status()
    result = resp.json()
    print(f"[DEBUG] 簽到JSON：{json.dumps(result, ensure_ascii=False)}")
    if "error" in result:
        raise Exception(f"簽到錯誤：{result['error'].get('message', '未知')}")
    return result.get("data", {})

def do_signin(csrf_token: str) -> dict:
    url = "https://www.gamer.com.tw/ajax/signin.php"
    print(f"[DEBUG] 執行簽到 → POST {url}")
    resp = requests.post(
        url, headers=build_headers(csrf_token),
        data={"action": "1", "bahamutCsrfToken": csrf_token}, timeout=10
    )
    print(f"[DEBUG] 簽到HTTP：{resp.status_code}")
    resp.raise_for_status()
    result = resp.json()
    print(f"[DEBUG] 簽到結果：{json.dumps(result, ensure_ascii=False)}")
    if "error" in result:
        raise Exception(f"簽到錯誤：{result['error'].get('message', '未知')}")
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
    api_url = "https://api.gamer.com.tw/home/v2/creation_list.php?owner=blackxblue&row=3"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cookie": COOKIE,
        "Referer": "https://home.gamer.com.tw/",
        "Accept": "application/json, text/plain, */*",
    }
    today = (datetime.now(tz=timezone.utc) + timedelta(hours=8)).date()
    today_str_formats = [
        today.strftime("%m/%d"),
        today.strftime("%-m/%-d"),
        today.strftime("%Y/%m/%d"),
        today.strftime("%Y-%m-%d"),
    ]
    print(f"[DEBUG] 今日：{today}，格式：{today_str_formats}")
    print(f"[DEBUG] 抓取 API：{api_url}")

    resp = requests.get(api_url, headers=headers, timeout=10)
    if resp.status_code != 200:
        raise Exception(f"API HTTP {resp.status_code}")
    data = resp.json()
    items = data.get("data", {}).get("list", [])
    print(f"[DEBUG] API 回傳文章數：{len(items)}")

    for item in items:
        title = item.get("title", "")
        content = item.get("content", "")
        csn = item.get("csn", "未知")
        ctime = item.get("ctime", "")
        print(f"[DEBUG] 檢查文章 sn={csn}，標題={title}，時間={ctime}")
        if any(s in title or s in content for s in today_str_formats):
            print(f"[DEBUG] 找到今天文章：sn={csn}")
            answer = try_parse_answer(content)
            if answer:
                return answer, f"API sn={csn}"
            article_url = f"https://home.gamer.com.tw/artwork.php?sn={csn}"
            resp2 = requests.get(article_url, headers=headers, timeout=10)
            article_text = re.sub(r'<[^>]+>', ' ', resp2.text)
            answer2 = try_parse_answer(article_text)
            if answer2:
                return answer2, f"文章頁 sn={csn}"
            raise Exception(f"找到文章 sn={csn} 但無法解析答案")

    latest = items[0] if items else {}
    raise Exception(
        f"無今日文章（{today}），最新：sn={latest.get('csn')} "
        f"{latest.get('title')}，時間={latest.get('ctime')}\n"
        f"blackxblue 可能今天尚未發文"
    )

def main():
    now = (datetime.now(tz=timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S (台灣時間)")
    log_url = get_log_url()

    # ===== Cookie 診斷 =====
    exp_date, days_left, username, userid = get_cookie_expiry()
    print(f"帳號：{username}（ID：{userid}）")
    print(f"Cookie 到期：{exp_date}，剩餘 {days_left} 天")

    baharune = get_baharune()
    if not baharune:
        send_email("❌ BAHARUNE缺失", f"帳號：{username}\n時間：{now}\n\nCookie 缺少 BAHARUNE，請重新複製。\n\nLog：{log_url}")
        raise Exception("BAHARUNE缺失")

    # ===== CSRF 全面診斷 =====
    csrf_token, csrf_source = fetch_csrf_token_from_api(baharune)
    print(f"[DIAG] CSRF Token：{'✅ 有值' if csrf_token else '❌ 失敗'} (來源：{csrf_source})")

    if not csrf_token:
        send_email("❌ CSRF完全失敗", f"帳號：{username}\n時間：{now}\n\nCSRF Token 無法取得，請更新 Cookie。\n\nLog：{log_url}")
        raise Exception("CSRF完全失敗，請更新 Cookie")

    # ===== SESSION 健康檢查 =====
    session_health = test_bahamut_session(csrf_token, build_headers(csrf_token))
    print(f"[DIAG] 巴哈SESSION：{session_health}")

    # ===== 健康分數 =====
    health_score = 100
    if days_left <= 3:
        health_score = 30
    elif days_left <= 7:
        health_score = 60
    if "失效" in session_health:
        health_score -= 40
    elif csrf_source == "COOKIE_BACKUP":
        health_score -= 10
    health_icon = "🟢" if health_score >= 80 else "🟡" if health_score >= 50 else "🔴"
    print(f"[DIAG] 系統健康：{health_score}/100 {health_icon}")

    if days_left <= 3:
        print("🚨 Cookie 極危，立即更新！")

    signin_result = "未執行"
    streak_info = ""
    answer_result = "未執行"
    has_error = False

    # ===== 簽到 =====
    try:
        print("\n========== 簽到 ==========")
        status_data = get_signin_status(csrf_token)
        days = status_data.get("days", "?")
        already_signed = status_data.get("signin", False)
        streak_info = f"✨ 連續 {days} 天"
        print(f"{streak_info}，今日已簽到：{already_signed}")

        if already_signed:
            signin_result = "✅ 已簽到（執行前完成，非自動觸發）"
            print(signin_result)
        else:
            print("執行自動簽到...")
            do_signin(csrf_token)
            status_data2 = get_signin_status(csrf_token)
            days = status_data2.get("days", days)
            streak_info = f"✨ 連續 {days} 天"
            signin_result = "✅ 本次自動簽到成功！"
            print(f"{signin_result} {streak_info}")

    except Exception as e:
        signin_result = f"❌ 簽到失敗：{e}"
        has_error = True
        print(f"[ERROR] {e}")

    # ===== 動畫瘋 =====
    print("\n========== 動畫瘋 ==========")
    try:
        answer, note = fetch_answer_from_blackxblue()
        print(f"今日答案：{answer}（{note}）")
        answer_result = (
            f"📋 答案：{answer}（{note}）\n"
            f"請前往作答：https://ani.gamer.com.tw/"
        )
    except Exception as e:
        answer_result = f"❌ 答案失敗：{e}"
        print(f"[ERROR] {answer_result}")

    # ===== Email 報告 =====
    if days_left < 0:
        expiry_warning = f"⚠️ Cookie 已過期（{exp_date}），請立即更新！"
    elif days_left <= 7:
        expiry_warning = f"⚠️ Cookie 將於 {exp_date} 到期（剩 {days_left} 天），請盡快更新！"
    else:
        expiry_warning = f"Cookie：{exp_date}（剩 {days_left} 天）"

    subject = f"巴哈任務 {'✅完成' if not has_error else '⚠️異常'} | 健康{health_score}{health_icon}"

    body = (
        f"帳號：{username}（ID：{userid}）\n"
        f"時間：{now}\n"
        f"簽到：{signin_result}\n"
        + (f"{streak_info}\n" if streak_info else "")
        + f"動畫瘋：{answer_result}\n"
        f"{expiry_warning}\n\n"
        f"=== 診斷報告 ===\n"
        f"健康分數：{health_score}/100 {health_icon}\n"
        f"CSRF來源：{csrf_source}\n"
        f"SESSION：{session_health}\n\n"
        f"完整 Log：{log_url}"
    )

    send_email(subject, body)
    print(f"[DIAG] 任務完成，健康分數：{health_score}/100 {health_icon}")

    if has_error:
        raise Exception(f"任務異常：{signin_result}")

if __name__ == "__main__":
    main()
