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


def build_headers(referer: str = "https://www.gamer.com.tw/",
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


def fetch_answer_from_blackxblue() -> str:
    headers = build_headers("https://home.gamer.com.tw/", "https://home.gamer.com.tw")
    headers.pop("X-Requested-With", None)
    headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"

    # 以 2026-05-09 的 sn=6331391 為基準，每天約加 1
    BASE_DATE = date(2026, 5, 9)
    BASE_SN = 6331391
    # 使用台灣時間（UTC+8）
    today = (datetime.now(tz=timezone.utc) + timedelta(hours=8)).date()
    delta = (today - BASE_DATE).days
    estimated_sn = BASE_SN + delta
    print(f"[DEBUG] 今日台灣日期：{today}，估算 sn：{estimated_sn}")

    today_str_formats = [
        today.strftime("%m/%d"),
        today.strftime("%-m/%-d"),
        today.strftime("%Y/%m/%d"),
        today.strftime("%Y-%m-%d"),
    ]

    for offset in [0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5]:
        sn = estimated_sn + offset
        article_url = f"https://home.gamer.com.tw/artwork.php?sn={sn}"
        print(f"[DEBUG] 嘗試 sn={sn}")
        try:
            resp = requests.get(article_url, headers=headers, timeout=15)
        except Exception as e:
            print(f"[DEBUG] sn={sn} 請求失敗：{e}")
            continue
        if resp.status_code != 200:
            print(f"[DEBUG] sn={sn} HTTP {resp.status_code}，跳過")
            continue
        content = resp.text

        is_today = any(s in content for s in today_str_formats)
        print(f"[DEBUG] sn={sn} 是今天的文章：{is_today}")
        if not is_today:
            continue

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
                answer = ['A', 'B', 'C', 'D'][int(val) - 1] if val in ['1', '2', '3', '4'] else val
                print(f"解析到答案：{answer}")
                return answer

        print(f"[DEBUG] sn={sn} 找到今日文章但解析不到答案，內容前 500 字：{content[:500]}")
        raise Exception("找到今日文章但無法解析答案")

    raise Exception(f"在 sn {estimated_sn-5}~{estimated_sn+5} 範圍內找不到今天的 blackxblue 文章")


# ────────────────────────────────────────────

def main():
    now = (datetime.now(tz=timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S (台灣時間)")
    log_url = get_log_url()

    exp_date, days_left, username, userid = get_cookie_expiry()
    print(f"帳號：{username}（ID：{userid}）")
    print(f"Cookie 到期日：{exp_date}，剩餘 {days_left} 天")

    if days_left < 0:
        expiry_warning = "\n\n⚠️ Cookie 已過期（" + exp_date + "），請立即更新！"
    elif days_left <= 7:
        expiry_warning = "\n\n⚠️ Cookie 將於 " + exp_date + " 到期（剩餘 " + str(days_left) + " 天），請盡快更新！"
    else:
        expiry_warning = "\n\nCookie 到期日：" + exp_date + "（剩餘 " + str(days_left) + " 天）"

    signin_result = "未執行"
    streak_info = ""
    answer_result = "未執行"
    has_error = False

    # ── 簽到 ──
    try:
        print("\n========== 簽到 ==========")
        status_data = get_signin_status()
        days = status_data.get("days", "?")
        already_signed = status_data.get("signin", False)
        streak_info = f"✨ 已連續簽到 {days} 天"
        print(f"{streak_info}，今日已簽到：{already_signed}")

        if already_signed:
            print("今日已簽到，略過簽到步驟")
            signin_result = "✅ 今日已簽到"
        else:
            print("正在執行簽到...")
            do_signin()
            status_data2 = get_signin_status()
            days = status_data2.get("days", days)
            streak_info = f"✨ 已連續簽到 {days} 天"
            signin_result = "✅ 成功"
            print(f"簽到完成，{streak_info}")

    except Exception as e:
        signin_result = f"❌ 失敗：{e}"
        has_error = True
        print(f"[ERROR] 簽到失敗：{e}")

    # ── 動畫瘋答題：抓答案後通知手動作答 ──
    print("\n========== 動畫瘋答題 ==========")
    try:
        answer = fetch_answer_from_blackxblue()
        answer_result = f"📋 今日答案：{answer}（請手動前往動畫瘋作答）\nhttps://ani.gamer.com.tw/"
        print(f"今日答案：{answer}")
    except Exception as e:
        answer_result = f"❌ 抓取答案失敗：{e}"
        print(f"[ERROR] {answer_result}")

    # ── 發送 Email 通知 ──
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
