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


def parse_baharune_jwt() -> dict:
    result = {"username": "未知", "userid": "未知", "exp_date": "未知", "days_left": -1}
    try:
        for item in COOKIE.split(";"):
            item = item.strip()
            if item.startswith("BAHARUNE="):
                jwt = item.split("=", 1)[1]
                payload_b64 = jwt.split(".")[1]
                payload_b64 += "=" * (4 - len(payload_b64) % 4)
                payload = json.loads(base64.b64decode(payload_b64))
                result["username"] = payload.get("username", "未知")
                result["userid"] = payload.get("userid", payload.get("uid", "未知"))
                exp_timestamp = payload.get("exp", 0)
                exp_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                now = datetime.now(tz=timezone.utc)
                result["exp_date"] = (exp_dt.astimezone()).strftime("%Y-%m-%d")
                result["days_left"] = (exp_dt - now).days
                break
    except Exception as e:
        print(f"解析 JWT 失敗：{e}")
    return result


def validate_cookie() -> list:
    required = ["BAHARUNE", "ckBahamutCsrfToken"]
    missing = []
    cookie_keys = [item.strip().split("=")[0] for item in COOKIE.split(";")]
    for key in required:
        if key not in cookie_keys:
            missing.append(key)
    return missing


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
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW,zh;q=0.9",
        "X-CSRF-Token": get_csrf_token(),
    }


def build_ani_headers() -> dict:
    # ★ Origin 和 Referer 都指向動畫瘋，避免 403
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        "Cookie": COOKIE,
        "Referer": "https://ani.gamer.com.tw/",
        "Origin": "https://ani.gamer.com.tw",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW,zh;q=0.9",
        "X-CSRF-Token": get_csrf_token(),
    }


def get_signin_status() -> dict:
    url = "https://www.gamer.com.tw/ajax/signin.php"
    resp = requests.post(url, headers=build_headers(), data="action=2", timeout=15)
    resp.raise_for_status()
    result = resp.json()
    print(f"[DEBUG] 簽到狀態 JSON：{json.dumps(result, ensure_ascii=False)}")
    return result.get("data", {})


def do_signin() -> dict:
    url = "https://www.gamer.com.tw/ajax/signin.php"
    resp = requests.post(url, headers=build_headers(), data="action=1", timeout=15)
    resp.raise_for_status()
    result = resp.json()
    print(f"[DEBUG] 簽到結果 JSON：{json.dumps(result, ensure_ascii=False)}")
    if isinstance(result, dict) and "error" in result:
        err_msg = result["error"].get("message", "未知錯誤")
        raise Exception(f"簽到 API 錯誤：{err_msg}")
    return result.get("data", result)


def do_anime_answer() -> str:
    try:
        url = "https://ani.gamer.com.tw/ajax/questionnaire.php"
        headers = build_ani_headers()  # ★ 使用動畫瘋專用 headers

        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        question_data = resp.json()
        print(f"[DEBUG] 問題資料：{json.dumps(question_data, ensure_ascii=False)}")

        status = question_data.get("status", 0)
        if status == 0:
            msg = question_data.get("message", "")
            if "已作答" in msg or "already" in msg.lower():
                print("今日動畫瘋已答題，略過")
                return "今日已答題（略過）"
            if "沒有" in msg or "無題" in msg:
                print("今日動畫瘋無題目")
                return "今日無題目"

        # 從 blackxblue 取得答案
        list_url = "https://home.gamer.com.tw/ajax/getCreationArticleList.php?owner=blackxblue&c=370818&page=1"
        r1 = requests.get(list_url, headers=build_headers("https://home.gamer.com.tw/"), timeout=15)
        r1.raise_for_status()
        articles = r1.json().get("data", [])
        if not articles:
            raise Exception("blackXblue 小屋沒有找到文章")

        latest_sn = articles[0].get("sn", "")
        r2 = requests.get(
            f"https://home.gamer.com.tw/creationDetail.php?sn={latest_sn}",
            headers=build_headers("https://home.gamer.com.tw/"), timeout=15
        )
        r2.raise_for_status()
        content = r2.text

        answer = None
        for pattern in [r'答案[：:是為]\s*([ABCD])', r'正確答案[：:]\s*([ABCD])', r'[Aa]nswer[：:\s]+([ABCD])']:
            m = re.search(pattern, content)
            if m:
                answer = m.group(1).upper()
                break
        if not answer:
            raise Exception("無法從 blackXblue 文章解析答案")
        print(f"解析到答案：{answer}")

        resp2 = requests.post(url, headers=headers, data={"answer": answer}, timeout=15)
        resp2.raise_for_status()
        result = resp2.json()
        result_msg = result.get("message", "無回應") if isinstance(result, dict) else str(result)
        return f"答題完成（答案：{answer}），回應：{result_msg}"

    except requests.exceptions.HTTPError as e:
        print(f"動畫瘋答題 API 不可用（{e}），略過")
        return f"⏭️ 跳過（{e}）"
    except Exception as e:
        print(f"動畫瘋答題失敗：{e}")
        return f"⏭️ 跳過（{e}）"


# ────────────────────────────────────────────

def main():
    now = (datetime.now(tz=timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S (台灣時間)")
    log_url = get_log_url()

    jwt_info = parse_baharune_jwt()
    username = jwt_info["username"]
    userid = jwt_info["userid"]
    exp_date = jwt_info["exp_date"]
    days_left = jwt_info["days_left"]
    print(f"帳號：{username}（ID：{userid}）")
    print(f"Cookie 到期日：{exp_date}，剩餘 {days_left} 天")

    missing = validate_cookie()
    if missing:
        warn_msg = f"⚠️ Cookie 缺少必要欄位：{', '.join(missing)}，請重新設定 GitHub Secrets！"
        print(warn_msg)
        send_email("⚠️ 巴哈 Cookie 格式異常", warn_msg)
        raise Exception(warn_msg)

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

    try:
        print("正在查詢簽到狀態...")
        status_data = get_signin_status()
        days = status_data.get("days", "?")
        already_signed = status_data.get("signin", False)
        streak_info = f"✨ 已連續簽到 {days} 天"
        print(streak_info)

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
        print(f"簽到失敗：{e}")

    print("正在執行動畫瘋答題...")
    answer_result = do_anime_answer()

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
