# 巴哈姆特每日自動簽到 + 動畫瘋答題

透過 GitHub Actions 每天自動完成巴哈姆特每日簽到與動畫瘋答題，並以 Email 通知執行結果。

***

## 功能說明

| 功能 | 說明 |
|------|------|
| 每日簽到 | 自動嘗試多個 API 端點，任一成功即完成 |
| 動畫瘋答題 | 自動從 [blackXblue 小屋](https://home.gamer.com.tw/blackxblue) 抓取當日答案並送出 |
| Email 通知 | 任務完成或失敗皆發信通知，附帶 Actions Log 連結 |
| Cookie 到期提醒 | 自動解析 JWT 到期日，剩餘 7 天內於通知信中提示更新 |

***

## 檔案結構

```
.
├── signin.py                        # 主程式（簽到 + 答題 + Email 通知）
├── Bahamut-cookie-parser.html       # Cookie 解析工具（本機瀏覽器開啟）
└── .github/
    └── workflows/
        └── auto-signin.yml          # GitHub Actions 排程設定
```

***

## 快速開始

### 步驟一：Fork 此 Repo

點擊右上角 **Fork**，建立屬於你自己的副本。

### 步驟二：取得 Cookie 並解析

巴哈姆特登入後 Cookie 包含驗證所需的完整資訊，需要將整串 Cookie 存為 GitHub Secret。

**使用 Cookie 解析工具（推薦）：**

👉 [開啟 Cookie 解析工具](https://htmlpreview.github.io/?https://github.com/rucifa/bahamut-auto-signin/blob/main/Bahamut-cookie-parser.html)

> 此工具**完全在本機瀏覽器執行**，不傳送任何資料到外部伺服器。

操作流程：
1. 在 Chrome / Edge 登入巴哈姆特
2. 按 `F12` 開啟 DevTools → **Application** → **Cookies** → `https://www.gamer.com.tw`
3. 全選所有 Cookie 項目並複製（或從 Network 欄位複製 `Cookie:` 標頭內容）
4. 貼入工具的文字框，按「**解析 Cookie**」
5. 工具會自動：
   - 顯示 Cookie **到期日與剩餘天數**
   - 警示缺少的重要欄位（`BAHARUNE`、`ckBahamutCsrfToken` 等）
   - 產生格式化的 `BAHAMUT_COOKIE` 完整值，提供**一鍵複製**按鈕
6. 點擊複製，準備貼入下一步的 Secret

### 步驟三：設定 GitHub Secrets

前往你 Fork 的 Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**，依序新增以下 4 個 Secret：

| Secret 名稱 | 填入內容 |
|-------------|----------|
| `BAHAMUT_COOKIE` | 由 Cookie 解析工具產生的完整 Cookie 字串 |
| `EMAIL_USER` | 寄信用的 Gmail 地址（例：`yourname@gmail.com`） |
| `EMAIL_PASS` | Gmail **應用程式密碼**（16 碼，見下方說明） |
| `EMAIL_TO` | 接收通知信的 Email 地址 |

#### 取得 Gmail 應用程式密碼

1. 前往 [Google 帳號安全性](https://myaccount.google.com/security)
2. 確認已開啟「兩步驟驗證」
3. 搜尋並進入「**應用程式密碼**」
4. 選擇「郵件 / Windows 電腦」→ 產生 → 複製 16 碼密碼
5. 將此密碼填入 `EMAIL_PASS`（**非** Google 帳號登入密碼）

### 步驟四：確認排程

預設每天 **台灣時間 08:10**（UTC 00:10）自動執行。

如需修改時間，編輯 `.github/workflows/auto-signin.yml` 中的 cron 表達式：

```yaml
- cron: "10 0 * * *"  # UTC 時間，台灣時間 = UTC + 8
```

也可前往 **Actions** 頁面手動點擊 **Run workflow** 立即測試。

***

## Email 通知範例

**成功時：**
```
主旨：✅ 巴哈每日任務完成

執行時間：2026-05-09 08:10:05 (台灣時間)
每日簽到：✅ 成功
動畫瘋答題：答題完成（答案：B），回應：答題成功

Cookie 到期日：2026-06-08（剩餘 30 天）

完整 Log：https://github.com/你的帳號/你的Repo/actions/runs/xxxxx
```

**失敗或 Cookie 即將到期時：**
```
主旨：⚠️ 巴哈每日任務部分失敗

執行時間：2026-05-09 08:10:05 (台灣時間)
每日簽到：❌ 失敗：所有端點均失敗，請重新從瀏覽器取得 Cookie 更新 GitHub Secret
動畫瘋答題：答題失敗：blackXblue 小屋沒有找到文章列表

⚠️ Cookie 將於 2026-05-12 到期（剩餘 3 天），請盡快更新！

完整 Log：https://github.com/你的帳號/你的Repo/actions/runs/xxxxx
```

***

## 更新 Cookie

Cookie 有效期通常為 **30 天**，到期前 7 天工具會在通知信中提醒你。

更新方式：
1. 重新開啟 [Cookie 解析工具](https://htmlpreview.github.io/?https://github.com/rucifa/bahamut-auto-signin/blob/main/Bahamut-cookie-parser.html)
2. 重複步驟二的流程，取得新的 Cookie 字串
3. 前往 Repo → **Settings** → **Secrets** → 點擊 `BAHAMUT_COOKIE` → **Update** → 貼上新值

***

## 注意事項

- **動畫瘋答題答案**來源為 blackXblue 小屋，若對方停止更新或改變文章格式，答題功能可能失效，但不影響簽到功能
- **巴哈 API 端點**可能隨時調整，若連續多日簽到失敗，請確認 Cookie 是否已過期
- 請遵守巴哈姆特服務條款，本工具僅供個人學習使用
- 本專案完全開源，不儲存任何帳號或 Cookie 資訊

***

## License

MIT
