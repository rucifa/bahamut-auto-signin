
## 設定步驟

### 1. 取得巴哈姆特 Cookie

1. 用 Chrome / Edge 登入 [巴哈姆特](https://www.gamer.com.tw/)
2. 按 `F12` 開啟開發者工具 → **Application** → **Cookies** → `https://www.gamer.com.tw`
3. 全選所有 Cookie 並複製整段字串

> 💡 **建議使用附帶的 `bahamut-cookie-parser.html`**：用瀏覽器開啟此檔案，貼入 Cookie 字串後可一鍵複製完整內容，並自動顯示到期日與剩餘天數。

### 2. 設定 GitHub Secrets

進入倉庫 → **Settings → Secrets and variables → Actions**，新增以下 4 個密鑰：

| 密鑰名稱 | 說明 | 範例 |
|---------|------|------|
| `BAHAMUT_COOKIE` | 完整 Cookie 字串 | `uid=xxx; BAHARUNE=eyJ...` |
| `EMAIL_USER` | 寄件 Gmail 帳號 | `your.email@gmail.com` |
| `EMAIL_PASS` | Gmail 應用程式密碼（非登入密碼） | `xxxx xxxx xxxx xxxx` |
| `EMAIL_TO` | 收件信箱 | `your.email@gmail.com` |

### 3. 設定 Gmail 應用程式密碼

1. 前往 [Google 帳號安全性](https://myaccount.google.com/security)
2. 啟用「**兩步驟驗證**」
3. 前往 [應用程式密碼](https://myaccount.google.com/apppasswords)
4. 選擇 App：**郵件**、Device：**Windows 電腦**（或其他）
5. 複製產生的 16 位密碼，填入 `EMAIL_PASS` Secret

### 4. 啟用 GitHub Actions

首次使用若 Actions 未啟用，請進入倉庫 → **Actions** → 點擊「**I understand my workflows, go ahead and enable them**」。

## 執行時間

| 項目 | 內容 |
|------|------|
| 排程時間 | 每天台灣時間 **08:10**（UTC 00:10） |
| Cron 表達式 | `10 0 * * *` |
| 手動觸發 | Actions 頁面 → 選擇 Workflow → **Run workflow** |

## Cookie 更新方式

Cookie 有效期約 **30 天**，到期後簽到會失敗，程式會在郵件中提醒剩餘天數。

更新步驟：
1. 重新至巴哈姆特登入，複製新的 Cookie
2. 使用 `bahamut-cookie-parser.html` 確認有效期
3. 至 GitHub → **Settings → Secrets** → 更新 `BAHAMUT_COOKIE`

## 手動測試

1. 進入倉庫 → **Actions** → 選擇「巴哈姆特自動簽到」
2. 點擊 **Run workflow** → **Run workflow**
3. 等待約 1 分鐘完成
4. 確認收到郵件通知

## 故障排除

| 問題 | 解決方式 |
|------|---------|
| 未收到郵件 | 確認 `EMAIL_PASS` 為應用程式密碼；檢查垃圾郵件匣 |
| 簽到失敗 | Cookie 可能已過期，請重新取得並更新 Secret |
| Actions 未執行 | 確認 Actions 已啟用；確認 cron 時間設定正確 |

## 安全提示

⚠️ 請將此倉庫設為**私有（Private）**，避免 Cookie 洩漏  
⚠️ 絕不在程式碼中直接寫入任何帳號資訊，一律使用 Secrets  
⚠️ Cookie 到期時請盡速更新，避免長期失效  

## 授權

MIT
