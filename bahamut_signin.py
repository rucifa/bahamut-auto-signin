import os
import sys
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def send_email(subject, body, is_success=True):
    """發送郵件通知"""
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    sender_email = os.getenv('SENDER_EMAIL')
    sender_password = os.getenv('SENDER_PASSWORD')
    recipient_email = os.getenv('RECIPIENT_EMAIL')

    if not all([sender_email, sender_password, recipient_email]):
        print("❌ 缺少郵件設定，跳過發送")
        return False

    try:
        print(f"📧 正在發送郵件到 {recipient_email}...")
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = recipient_email
        message['Subject'] = subject

        status_color = "#28a745" if is_success else "#dc3545"
        status_text = "✅ 成功" if is_success else "❌ 失敗"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: {status_color}; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0;">巴哈姆特自動簽到 {status_text}</h2>
            </div>
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px; border: 1px solid #dee2e6;">
                <p><strong>時間:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)</p>
                <hr style="border: none; border-top: 1px solid #dee2e6;">
                <p><strong>詳情:</strong></p>
                <p style="white-space: pre-wrap;">{body}</p>
            </div>
        </body>
        </html>
        """

        message.attach(MIMEText(html_body, 'html', 'utf-8'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())

        print("✅ 郵件發送成功")
        return True

    except Exception as e:
        print(f"❌ 郵件發送失敗: {e}")
        return False


def create_driver():
    """建立 Chrome WebDriver"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                         'AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/120.0.0.0 Safari/537.36')

    # 優先使用 webdriver-manager 自動管理版本
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("✅ WebDriver 啟動成功 (webdriver-manager)")
        return driver
    except Exception as e:
        print(f"⚠️ webdriver-manager 失敗: {e}，嘗試系統 ChromeDriver...")

    # 備用：使用系統安裝的 chromedriver
    try:
        driver = webdriver.Chrome(options=options)
        print("✅ WebDriver 啟動成功 (系統 chromedriver)")
        return driver
    except Exception as e:
        raise RuntimeError(f"無法啟動 ChromeDriver: {e}")


def signin_bahamut():
    """執行巴哈姆特簽到"""
    username = os.getenv('BAHAMUT_USERNAME')
    password = os.getenv('BAHAMUT_PASSWORD')

    if not username or not password:
        raise ValueError("❌ 未設定 BAHAMUT_USERNAME 或 BAHAMUT_PASSWORD")

    driver = create_driver()
    wait = WebDriverWait(driver, 20)

    try:
        # 前往登入頁面
        print("🌐 前往巴哈姆特登入頁面...")
        driver.get('https://www.gamer.com.tw/')
        time.sleep(2)

        # 點擊登入按鈕
        print("🔍 尋找登入入口...")
        login_link = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href*="login"], a.signin, #sign-in-btn'))
        )
        login_link.click()
        time.sleep(2)

        # 填入帳號密碼
        print("✏️ 填入帳號密碼...")
        username_field = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="userid"], #userid, input[type="text"]'))
        )
        username_field.clear()
        username_field.send_keys(username)

        password_field = driver.find_element(By.CSS_SELECTOR, 'input[name="password"], #password, input[type="password"]')
        password_field.clear()
        password_field.send_keys(password)

        # 提交登入
        print("🔐 提交登入...")
        submit_btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"], .login-btn')
        submit_btn.click()
        time.sleep(3)

        # 確認登入狀態
        current_url = driver.current_url
        page_source = driver.page_source

        if 'logout' in page_source.lower() or username.lower() in page_source.lower():
            print("✅ 登入成功！")
        else:
            raise RuntimeError("登入後無法確認登入狀態，請檢查帳號密碼")

        # 前往簽到頁面
        print("🎯 前往簽到頁面...")
        driver.get('https://www.gamer.com.tw/ajax/signin.php')
        time.sleep(2)

        signin_result = driver.page_source
        print(f"簽到回應: {signin_result[:200]}")

        # 嘗試點擊簽到按鈕（若為頁面形式）
        try:
            signin_btn = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.signin-btn, #signin-btn, button.gg-btn'))
            )
            signin_btn.click()
            time.sleep(2)
            print("✅ 簽到按鈕點擊成功")
        except Exception:
            print("ℹ️ 未找到簽到按鈕，可能已透過 AJAX 完成或今日已簽到")

        return "登入並簽到成功！"

    finally:
        driver.quit()
        print("🔒 瀏覽器已關閉")


def main():
    print(f"🚀 開始執行巴哈姆特自動簽到 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    try:
        result = signin_bahamut()
        print(f"\n✅ 簽到完成: {result}")
        send_email(
            subject="✅ 巴哈姆特自動簽到成功",
            body=result,
            is_success=True
        )
        sys.exit(0)

    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ 簽到失敗: {error_msg}")
        send_email(
            subject="❌ 巴哈姆特自動簽到失敗",
            body=f"錯誤訊息:\n{error_msg}",
            is_success=False
        )
        sys.exit(1)


if __name__ == '__main__':
    main()
