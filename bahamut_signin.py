import os
import sys
import re
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


# ── 共用 Headers ──────────────────────────────────────────────
BASE_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/136.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
}


# ── 發送郵件通知 ──────────────────────────────────────────────
def send_email(subject, body, is_success=True):
    smtp_server  = os.getenv('SMTP_SERVER') or 'smtp.gmail.com'
    smtp_port    = int(os.getenv('SMTP_PORT') or '587')
    sender_email = os.getenv('SENDER_EMAIL')
    sender_pass  = os.getenv('SENDER_PASSWORD')
    recipient    = os.getenv('RECIPIENT_EMAIL')

    if not all([sender_email, sender_pass, recipient]):
        print('⚠️  缺少郵件設定，略過發送')
        return False

    try:
        status_color = '#28a745' if is_success else '#dc3545'
        status_text  = '✅ 成功' if is_success else '❌ 失敗'

        html = f"""
        <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
          <div style="background:{status_color};color:white;padding:20px;border-radius:8px 8px 0 0">
            <h2 style="margin:0">巴哈姆特自動簽到 {status_text}</h2>
          </div>
          <div style="background:#f8f9fa;padding:20px;border-radius:0 0 8px 8px;border:1px solid #dee2e6">
            <p><strong>時間：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)</p>
            <hr style="border:none;border-top:1px solid #dee2e6">
            <p><strong>詳情：</strong></p>
            <p style="white-space:pre-wrap">{body}</p>
          </div>
        </body></html>
        """

        msg = MIMEMultipart()
        msg['From']    = sender_email
        msg['To']      = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(html, 'html', 'utf-8'))

        with smtplib.SMTP(smtp_server, smtp_port) as srv:
            srv.starttls()
            srv.login(sender_email, sender_pass)
            srv.sendmail(sender_email, recipient, msg.as_string())

        print('✅ 郵件發送成功')
        return True
    except Exception as e:
        print(f'❌ 郵件發送失敗: {e}')
        return False


# ── 取得 CSRF Token ───────────────────────────────────────────
def get_csrf_token(session: requests.Session) -> str:
    resp = session.get(
        'https://www.gamer.com.tw/',
        headers={**BASE_HEADERS, 'Accept': 'text/html,application/xhtml+xml,*/*'},
        timeout=15
    )
    resp.raise_for_status()

    match = re.search(r'csrfToken\s*=\s*["\']([^"\']+)["\']', resp.text)
    if match:
        token = match.group(1)
        print(f'✅ 取得 CSRF Token: {token[:10]}...')
        return token

    match = re.search(
        r'<meta[^>]+name=["\']csrf-token["\'][^>]+content=["\']([^"\']+)["\']',
        resp.text
    )
    if match:
        token = match.group(1)
        print(f'✅ 取得 CSRF Token (meta): {token[:10]}...')
        return token

    raise RuntimeError('找不到 CSRF Token，頁面結構可能已變更')


# ── 登入 ──────────────────────────────────────────────────────
def login(session: requests.Session, username: str, password: str):
    # 先訪問登入頁取得初始 cookie
    session.get(
        'https://user.gamer.com.tw/login.php',
        headers={**BASE_HEADERS, 'Accept': 'text/html,application/xhtml+xml,*/*'},
        timeout=15
    )

    payload = {
        'userid':   username,
        'password': password,
    }
    headers = {
        **BASE_HEADERS,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin':  'https://user.gamer.com.tw',
        'Referer': 'https://user.gamer.com.tw/login.php',
        'Accept':  'text/html,application/xhtml+xml,*/*;q=0.9',
    }

    resp = session.post(
        'https://user.gamer.com.tw/login.php',
        data=payload,
        headers=headers,
        allow_redirects=True,
        timeout=15
    )
    resp.raise_for_status()

    cookies = {c.name: c.value for c in session.cookies}
    print(f'📋 目前 Cookies: {list(cookies.keys())}')

    if not any(k in cookies for k in ('BAHSESS', 'userid', 'nologin')):
        if 'logout' not in resp.text.lower() and username.lower() not in resp.text.lower():
            raise RuntimeError(
                '登入後未找到有效 session cookie，可能是帳密錯誤'
                '或巴哈要求額外驗證'
            )

    print('✅ 登入成功，已取得 Session')


# ── 每日簽到 ──────────────────────────────────────────────────
def daily_signin(session: requests.Session, csrf_token: str) -> str:
    url = 'https://api.gamer.com.tw/user/v1/signin.php'
    headers = {
        **BASE_HEADERS,
        'Origin':  'https://www.gamer.com.tw',
        'Referer': 'https://www.gamer.com.tw/',
        'X-Requested-With': 'XMLHttpRequest',
    }
    data = {
        'action': '1',
        'token':  csrf_token,
    }

    resp = session.post(url, data=data, headers=headers, timeout=15)
    resp.raise_for_status()

    try:
        result = resp.json()
        print(f'📦 簽到 API 回應: {result}')
    except Exception:
        result = resp.text
        print(f'📦 簽到原始回應: {result[:300]}')

    if isinstance(result, dict):
        msg = result.get('msg', '') or result.get('message', '') or str(result)
        if result.get('status') in (1, '1', True) or '成功' in msg or '巴幣' in msg or 'GP' in msg:
            return f'簽到成功！{msg}'
        if '已經簽到' in msg or 'already' in msg.lower():
            return f'今日已簽到過了（{msg}）'
        return f'簽到完成，伺服器回應：{msg}'

    text = str(result)
    if '成功' in text or '巴幣' in text:
        return f'簽到成功！{text[:100]}'
    if '已經簽到' in text:
        return '今日已簽到過了'
    return f'簽到請求完成，回應：{text[:200]}'


# ── 主流程 ────────────────────────────────────────────────────
def signin_bahamut() -> str:
    username = os.getenv('BAHAMUT_USERNAME', '').strip()
    password = os.getenv('BAHAMUT_PASSWORD', '').strip()

    if not username or not password:
        raise ValueError('未設定 BAHAMUT_USERNAME 或 BAHAMUT_PASSWORD')

    session = requests.Session()
    session.headers.update(BASE_HEADERS)

    print('🔐 正在登入巴哈姆特...')
    login(session, username, password)

    print('🔑 取得 CSRF Token...')
    csrf_token = get_csrf_token(session)

    print('🎯 執行每日簽到...')
    result = daily_signin(session, csrf_token)

    return result


def main():
    print(f'🚀 開始執行巴哈姆特自動簽到 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 50)

    try:
        result = signin_bahamut()
        print(f'\n✅ 完成: {result}')
        send_email('✅ 巴哈姆特自動簽到成功', result, is_success=True)
        sys.exit(0)

    except Exception as e:
        error_msg = str(e)
        print(f'\n❌ 失敗: {error_msg}')
        send_email('❌ 巴哈姆特自動簽到失敗', f'錯誤訊息:\n{error_msg}', is_success=False)
        sys.exit(1)


if __name__ == '__main__':
    main()
