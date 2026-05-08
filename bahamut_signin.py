# 複製下面的完整內容
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

def send_email(subject, body, is_success=True):
    """發送郵件通知"""
    
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    sender_email = os.getenv('SENDER_EMAIL')
    sender_password = os.getenv('SENDER_PASSWORD')
    recipient_email = os.getenv('RECIPIENT_EMAIL')
    
    if not all([sender_email, sender_password, recipient_email]):
        print("❌ 缺少郵件設定")
        return False
    
    try:
        print(f"📧 正在發送郵件到 {recipient_email}...")
        
        # 建立郵件
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = recipient_email
        message['Subject'] = subject
        
        # 建立郵件內容（HTML格式）
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="background-color: {'#d4edda' if is_success else '#f8d7da'}; 
                            border: 1px solid {'#c3e6cb' if is_success else '#f5c6cb'}; 
                            border-radius: 5px; padding: 15px; margin: 10px 0;">
                    <h2 style="color: {'#155724' if is_success else '#721c24'}; margin-top: 0;">
                        {'✅ 簽到成功' if is_success else '❌ 簽到失敗'}
                    </h2>
                    <p><strong>時間:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>詳情:</strong></p>
                    <p style="background-color: #f5f5f5; padding: 10px; border-radius: 3px;">
                        {body}
                    </p>
                </div>
                <footer style="margin-top: 20px; font-size: 12px; color: #666;">
                    <p>此郵件由巴哈姆特自動簽到機器人發送。</p>
                </footer>
            </body>
        </html>
        """
        
        message.attach(MIMEText(html_body, 'html'))
        
        # 連接到 SMTP 伺服器並發送
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
        
        print(f"✅ 郵件已發送!")
        return True
        
    except Exception as e:
        print(f"❌ 郵件發送失敗: {e}")
        return False

def signin_bahamut():
    """自動簽到巴哈姆特"""
    
    # 獲取認證資訊
    username = os.getenv('BAHAMUT_USERNAME')
    password = os.getenv('BAHAMUT_PASSWORD')
    
    if not username or not password:
        error_msg = "缺少登入資訊 (BAHAMUT_USERNAME 或 BAHAMUT_PASSWORD)"
        print(f"❌ {error_msg}")
        send_email("❌ 巴哈姆特簽到失敗", error_msg, is_success=False)
        sys.exit(1)
    
    # 設定 Chrome 選項
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = None
    try:
        # 初始化瀏覽器
        print("🔄 正在初始化瀏覽器...")
        driver = webdriver.Chrome(options=chrome_options)
        
        # 打開巴哈姆特首頁
        print("🔄 正在打開巴哈姆特...")
        driver.get("https://www.gamer.com.tw/")
        time.sleep(2)
        
        # 點擊登入按鈕
        print("🔄 正在點擊登入按鈕...")
        try:
            login_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '登入')] | //button[contains(text(), '登入')]"))
            )
            login_btn.click()
        except:
            print("⚠️ 未找到登入按鈕，嘗試跳過...")
        
        time.sleep(2)
        
        # 填入帳號
        print("🔄 正在輸入帳號...")
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        username_field.clear()
        username_field.send_keys(username)
        time.sleep(1)
        
        # 填入密碼
        print("🔄 正在輸入密碼...")
        password_field = driver.find_element(By.NAME, "password")
        password_field.clear()
        password_field.send_keys(password)
        time.sleep(1)
        
        # 提交登入表單
        print("🔄 正在提交登入表單...")
        submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), '登入')]")
        submit_btn.click()
        time.sleep(4)
        
        # 檢查是否登入成功
        if "gamer.com.tw" in driver.current_url:
            print("✅ 登入成功!")
            
            # 嘗試點擊簽到按鈕
            try:
                print("🔄 正在尋找簽到按鈕...")
                signin_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '簽到')] | //button[contains(text(), '簽到')] | //*[@class='sign-in'] | //*[contains(@class, 'signin')]"))
                )
                signin_btn.click()
                time.sleep(2)
                
                success_msg = "已成功完成巴哈姆特每日簽到！"
                print(f"✅ {success_msg}")
                send_email("✅ 巴哈姆特簽到成功", success_msg, is_success=True)
                
            except Exception as e:
                success_msg = f"已登入但未找到簽到按鈕。可能已簽到或按鈕位置已變更。\n錯誤: {str(e)}"
                print(f"⚠️ {success_msg}")
                send_email("⚠️ 巴哈姆特登入成功但簽到狀態未知", success_msg, is_success=True)
        else:
            error_msg = f"登入失敗，當前URL: {driver.current_url}"
            print(f"❌ {error_msg}")
            send_email("❌ 巴哈姆特簽到失敗", error_msg, is_success=False)
            sys.exit(1)
            
    except Exception as e:
        error_msg = f"發生錯誤: {str(e)}"
        print(f"❌ {error_msg}")
        send_email("❌ 巴哈姆特簽到出錯", error_msg, is_success=False)
        sys.exit(1)
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    signin_bahamut()
