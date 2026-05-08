# 巴哈姆特自動簽到機器人 🤖

自動化每日登入巴哈姆特並簽到，結果透過郵件通知。

## 功能特性

✅ 每日凌晨 12:05 自動簽到  
✅ 成功/失敗郵件通知  
✅ 使用 GitHub Actions 完全自動化  
✅ 無需本地運行  
✅ 支援任何 SMTP 郵件服務  

## 設定步驟

### 1. 倉庫已建立

此倉庫已完成配置，所有程式碼已準備好。

### 2. 添加 Secrets

進入倉庫 → Settings → Secrets and variables → Actions，添加以下密鑰：

| 密鑰名稱 | 說明 | 範例 |
|---------|------|------|
| `BAHAMUT_USERNAME` | 巴哈姆特帳號 | `yourUsername` |
| `BAHAMUT_PASSWORD` | 巴哈姆特密碼 | `yourPassword` |
| `SENDER_EMAIL` | 寄件者郵箱（Gmail） | `your.email@gmail.com` |
| `SENDER_PASSWORD` | Gmail 應用程式密碼 | `xxxx xxxx xxxx xxxx` |
| `RECIPIENT_EMAIL` | 收件人郵箱 | `your.email@gmail.com` |

### 3. 使用 Gmail 的特殊設定

1. 進入 https://myaccount.google.com/security
2. 啟用「兩步驟驗證」
3. 進入 https://myaccount.google.com/apppasswords
4. 選擇 App：**Mail**，Device：**Windows 電腦**（或其他）
5. 複製生成的 16 位應用程式密碼

### 執行時間

- **排程時間**: 每天凌晨 12:05 台灣時間
- **Cron 表達式**: `5 20 * * *` (UTC 時間)
- 支援手動觸發：Actions 頁面點擊「Run workflow」

## 手動測試

1. 進入倉庫 → Actions → Bahamut 自動簽到
2. 點擊 "Run workflow" → "Run workflow"
3. 等待 2-3 分鐘完成
4. 檢查郵箱是否收到通知

## 程式碼結構

```
bahamut-auto-signin/
├── bahamut_signin.py              # 主要簽到腳本
├── requirements.txt                # Python 依賴
├── .github/workflows/
│   └── bahamut-signin.yml         # GitHub Actions 工作流程
└── README.md                       # 此說明文件
```

## 程式特點

### 🔐 安全性
- 使用 GitHub Secrets 存儲敏感信息，絕不在代碼中暴露
- SMTP 連接使用 TLS 加密

### 🤖 自動化
- 使用 webdriver-manager 自動管理 ChromeDriver
- 具有主備方案，確保 Chrome 初始化成功
- 完整的錯誤捕捉和日誌記錄

### 📧 通知系統
- HTML 格式美觀郵件設計
- 成功和失敗都會發送通知
- 包含時間戳和詳細的錯誤信息

### 🔄 容錯機制
- 如果找不到簽到按鈕會嘗試替代方案
- 登入失敗時會立即通知
- ChromeDriver 安裝失敗時自動回退

## 故障排除

### 未收到郵件
- 檢查 SENDER_PASSWORD 是否為 Gmail 應用程式密碼
- 檢查垃圾郵件資料夾
- 檢查 Actions 運行日誌

### 登入失敗
- 確認帳號密碼正確
- 檢查是否啟用了帳戶安全檢查
- 查看 Actions 運行日誌中的詳細錯誤

### Chrome/ChromeDriver 錯誤
- webdriver-manager 會自動下載最新版本
- 如果失敗會自動使用系統 Chrome

## 安全提示

⚠️ 絕不要在代碼中寫入帳密，只使用 Secrets  
⚠️ 保持倉庫為私有狀態  
⚠️ 定期檢查 Actions 執行日誌  

## 許可證

MIT
