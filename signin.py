import requests
import smtplib
import os
import json
import base64
import re
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

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
        print(f"[ERROR] 解析 JWT 失敗：{e}")
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


def get_signin_status() -> dict:
    url = "https://www.gamer.com.tw/ajax/signin.php"
    print(f"[DEBUG] 查詢簽到狀態 → POST {url}")
    resp = requests.post(url, headers=build_headers(), data="action=2", timeout=15)
    print(f"[DEBUG] 回應 HTTP {resp.status_code}")
    resp.raise_for_status()
    result = resp.json()
    print(f"[DEBUG] 簽到狀態 JSON：{json.dumps(result, ensure_ascii=False)}")
    return result.get("data", {})


def do_signin() -> dict:
    url = "https://www.gamer.com.tw/ajax/signin.php"
    print(f"[DEBUG] 執行簽到 → POST {url}")
    resp = requests.post(url, headers=build_headers(), data="action=1", timeout=15)
    print(f"[DEBUG] 回應 HTTP {resp.status_code}")
    resp.raise_for_status()
    result = resp.json()
    print(f"[DEBUG] 簽到結果 JSON：{json.dumps(result, ensure_ascii=False)}")
    if isinstance(result, dict) and "error" in result:
        err_msg = result["error"].get("message", "未知錯誤")
        raise Exception(f"簽到 API 錯誤：{err_msg}")
    return result.get("data", result)


def fetch_answer_from_blackxblue() -> str:
    list_url = "https://home.gamer.com.tw/ajax/getCreationArticleList.php?owner=blackxblue&c=370818&page=1"
    print(f"[DEBUG] 抓取 blackxblue 文章列表...")
    r1 = requests.get(list_url, headers=build_headers("https://home.gamer.com.tw/"), timeout=15)
    print(f"[DEBUG] 文章列表 HTTP {r1.status_code}")
    print(f"[DEBUG] 文章列表回應內容：{r1.text[:300]}")
    r1.raise_for_status()
    articles = r1.json().get("data", [])
    if not articles:
        raise Exception("blackXblue 小屋沒有找到文章")

    latest_sn = articles[0].get("sn", "")
    print(f"[DEBUG] 最新文章 sn：{latest_sn}")

    r2 = requests.get(
        f"https://home.gamer.com.tw/creationDetail.php?sn={latest_sn}",
        headers=build_headers("https://home.gamer.com.tw/"), timeout=15
    )
    print(f"[DEBUG] 文章內容 HTTP {r2.status_code}")
    r2.raise_for_status()
    content = r2.text

    answer = None
    for pattern in [r'答案[：:是為]\s*([ABCD])', r'正確答案[：:]\s*([ABCD])', r'[Aa]nswer[：:\s]+([ABCD])']:
        m = re.search(pattern, content)
        if m:
            answer = m.group(1).upper()
            break

    if not answer:
        # 印出文章前 500 字幫助 debug
        print(f"[DEBUG] 文章內容前 500 字：{content[:500]}")
        raise Exception("無法從 blackXblue 文章解析答案，格式可能已變更")

    print(f"[DEBUG] 解析到答案：{answer}")
    return answer


def cookie_str_to_list(cookie_str: str) -> list:
    cookies = []
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            name, value = item.split("=", 1)
            # ani.gamer.com.tw 和 gamer.com.tw 都要有
            for domain in [".gamer.com.tw", ".ani.gamer.com.tw"]:
                cookies.append({
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": domain,
                    "path": "/",
                })
    return cookies


def do_anime_answer_playwright() -> str:
    print("[PLAYWRIGHT] 開始初始化瀏覽器...")

    # 先取得答案（requests，不需要瀏覽器）
    try:
        answer = fetch_answer_from_blackxblue()
    except Exception as e:
        print(f"[ERROR] 無法取得答案：{e}")
        return f"⏭️ 跳過（無法取得答案：{e}）"

    try:
        with sync_playwright() as p:
            print("[PLAYWRIGHT] 啟動 Chromium...")
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="zh-TW",
                timezone_id="Asia/Taipei",
            )

            # 注入 Cookie
            all_cookies = cookie_str_to_list(COOKIE)
            context.add_cookies(all_cookies)
            print(f"[PLAYWRIGHT] 注入 {len(all_cookies)} 個 Cookie")

            page = context.new_page()

            # 先訪問動畫瘋首頁，讓 Cloudflare 驗證通過
            print("[PLAYWRIGHT] 訪問動畫瘋首頁...")
            page.goto("https://ani.gamer.com.tw/", timeout=30000)
            page.wait_for_timeout(2000)
            print(f"[PLAYWRIGHT] 首頁標題：{page.title()}")

            # 檢查是否有登入
            current_url = page.url
            print(f"[PLAYWRIGHT] 當前 URL：{current_url}")

            # 先用 GET 查詢今日答題狀態
            print("[PLAYWRIGHT] 查詢答題狀態...")
            status_result = page.evaluate("""
                async () => {
                    const resp = await fetch('https://ani.gamer.com.tw/ajax/questionnaire.php', {
                        method: 'GET',
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest',
                            'Referer': 'https://ani.gamer.com.tw/',
                        },
                    });
                    return { status: resp.status, body: await resp.text() };
                }
            """)
            print(f"[PLAYWRIGHT] 查詢狀態：HTTP {status_result['status']}, body={status_result['body'][:300]}")

            # 判斷是否已答題
            if status_result['status'] == 200:
                try:
                    status_data = json.loads(status_result['body'])
                    if status_data.get("status") == 0:
                        msg = status_data.get("message", "")
                        if "已作答" in msg or "already" in msg.lower():
                            browser.close()
                            return "今日已答題（略過）"
                        if "沒有" in msg or "無題" in msg:
                            browser.close()
                            return "今日無題目"
                except Exception:
                    pass

            # 提交答案
            print(f"[PLAYWRIGHT] 提交答案：{answer}")
            result = page.evaluate(f"""
                async () => {{
                    const resp = await fetch('https://ani.gamer.com.tw/ajax/questionnaire.php', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'X-Requested-With': 'XMLHttpRequest',
                            'Referer': 'https://ani.gamer.com.tw/',
                        }},
                        body: 'answer={answer}',
                    }});
                    return {{ status: resp.status, body: await resp.text() }};
                }}
            """)

            print(f"[PLAYWRIGHT] 答題回應：HTTP {result['status']}, body={result['body'][:300]}")
            browser.close()

            if result['status'] == 200:
                try:
                    data = json.loads(result['body'])
                    msg = data.get("message", "無回應訊息")
                    return f"✅ 答題完成（答案：{answer}），回應：{msg}"
                except Exception:
                    return f"✅ 答題完成（答案：{answer}）"
            elif result['status'] == 403:
                body = result['body']
                if "系統異常" in body or "<!DOCTYPE" in body:
                    return "⏭️ 跳過（Cloudflare 仍然攔截，即使使用瀏覽器）"
                return f"⏭️ 跳過（HTTP 403）"
            else:
                return f"⏭️ 跳過（HTTP {result['status']}）"

    except Exception as e:
        print(f"[ERROR] Playwright 執行失敗：{e}")
        import traceback
        traceback.print_exc()
        return f"⏭️ 跳過（Playwright 錯誤：{e}）"


# ────────────────────────────────────────────

def main():
    now = (datetime.now(tz=timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S (台灣時間)")
    log_url = get_log_url()

    # ── 帳號資訊 ──
    jwt_info = parse_baharune_jwt()
    username = jwt_info["username"]
    userid = jwt_info["userid"]
    exp_date = jwt_info["exp_date"]
    days_left = jwt_info["days_left"]
    print(f"帳號：{username}（ID：{userid}）")
    print(f"Cookie 到期日：{exp_date}，剩餘 {days_left} 天")

    # ── Cookie 欄位驗證 ──
    missing = validate_cookie()
    if missing:
        warn_msg = f"⚠️ Cookie 缺少必要欄位：{', '.join(missing)}，請重新設定 GitHub Secrets！"
        print(f"[ERROR] {warn_msg}")
        send_email("⚠️ 巴哈 Cookie 格式異常", warn_msg)
        raise Exception(warn_msg)
    print(f"[DEBUG] Cookie 欄位驗證通過，CSRF Token：{get_csrf_token()[:8]}...")

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
        finished_ad = status_data.get("finishedAd", False)
        streak_info = f"✨ 已連續簽到 {days} 天"
        print(f"{streak_info}，今日已簽到：{already_signed}，雙倍獎勵：{finished_ad}")

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

    # ── 動畫瘋答題 ──
    print("\n========== 動畫瘋答題 ==========")
    answer_result = do_anime_answer_playwright()
    print(f"答題結果：{answer_result}")

    # ── Email 通知 ──
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
