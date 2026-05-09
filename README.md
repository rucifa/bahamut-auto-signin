# 巴哈姆特每日自動簽到 / Bahamut Auto Sign-in

自動執行巴哈姆特每日任務的 GitHub Actions 專案，支援 Cookie 到期提醒與 Email 通知。

***

## 🚀 快速開始

### 步驟一：Fork 此專案

點擊右上角 **Fork**，複製到你自己的 GitHub 帳號底下。

***

### 步驟二：取得 Cookie

1. 在 Chrome / Edge 登入 [巴哈姆特](https://www.gamer.com.tw/)
2. 按 `F12` → **Application** → **Cookies** → `www.gamer.com.tw`
3. 全選複製所有 Cookie 內容

**用解析工具確認內容：**

- 開啟 🔍 [Bahamut Cookie 解析工具](https://htmlpreview.github.io/?https://github.com/rucifa/bahamut-auto-signin/blob/main/Bahamut-cookie-parser.html)
- 將複製的 Cookie 字串貼入，按「解析 Cookie」
- 確認顯示正確帳號暱稱、會員 ID 與到期日後再繼續

> ⚠️ 解析工具完全在本機瀏覽器執行，不會傳送任何資料到外部。

***

### 步驟三：設定 GitHub Secrets

前往你的 Repo → **Settings → Secrets and variables → Actions → New repository secret**，依序新增以下 4 個 Secret：

| Secret 名稱 | 說明 |
|---|---|
| `BAHAMUT_COOKIE` | 完整 Cookie 字串（由 Cookie 解析工具複製取得） |
| `EMAIL_USER` | 寄信用的 Gmail 地址（例：`yourmail@gmail.com`） |
| `EMAIL_PASS` | Gmail 應用程式密碼（16 碼，非帳號密碼，需開啟兩步驟驗證後產生） |
| `EMAIL_TO` | 要收到通知信的 Email 地址 |

> 💡 Gmail 應用程式密碼產生方式：Google 帳戶 → 安全性 → 兩步驟驗證 → 應用程式密碼

***

### 步驟四：確認排程

Actions 設定完成後即會依排程自動執行。預設時間為每天 **台灣時間 00:00（UTC 16:00）**。

你也可以在 Actions 頁面手動點 **Run workflow** 來測試是否正常運作。

***

## ⏱ 修改排程時間

排程定義在 `.github/workflows/signin.yml`：

```yaml
on:
  schedule:
    - cron: '0 16 * * *'   # UTC 16:00 = 台灣時間 00:00
  workflow_dispatch:         # 保留手動觸發功能
```

如需更改時間，修改 cron 語法即可。可參考 [crontab.guru](https://crontab.guru/) 換算時區。

***

## 📧 Email 通知說明

| 情境 | 通知行為 |
|---|---|
| Cookie 剩餘 ≤ 7 天 | ⚠️ 寄出「請更新 Cookie」提醒信 |
| Cookie 已過期 | ❌ 寄出「Cookie 已失效」緊急通知 |
| 正常簽到成功 | 預設不寄信（可在 `signin.py` 自行開啟） |

***

## 🔧 Cookie 解析工具（Bahamut-cookie-parser.html）

這是一個純前端工具，用於解析 Cookie 並輸出可直接貼到 GitHub Secrets 的字串。

> 🔗 **直接開啟：**[Bahamut Cookie 解析工具](https://htmlpreview.github.io/?https://github.com/rucifa/bahamut-auto-signin/blob/main/Bahamut-cookie-parser.html)

**功能：**
- 從 `BAHARUNE` JWT 解析帳號資訊，包含：
  - `username`：帳號暱稱
  - `userid`：文字型帳號 ID
  - `mid`：數字型會員 ID
- 顯示 Cookie 到期日與剩餘天數
- 一鍵複製完整 Cookie 字串
- 支援多種複製格式（分號格式 / DevTools Tab 格式）

**重要 Cookie 欄位：**

| 欄位名稱 | 重要性 | 說明 |
|---|---|---|
| `BAHARUNE` | ⭐ 必要 | JWT 格式身份驗證 Token，包含帳號資訊與到期時間 |
| `ckBahamutCsrfToken` | ⭐ 必要 | CSRF 防護 Token，POST 請求必要 |
| `BAHAID` | 🔷 參考 | 文字型帳號 ID（與 JWT 內 `userid` 相同） |
| `BAHANICK` | 🔷 參考 | URL encode 格式暱稱 |

> ❌ `ckMd5`、`B_GAME_ID`、`cookie_login_new` 為舊版遺留欄位，目前登入後不一定會產生，不影響正常功能。

***

## 🔄 Cookie 到期後更新方式

Cookie 有效期通常約 **30 天**，收到提醒信後請依以下步驟更新：

1. 重新登入巴哈姆特
2. 重新複製 Cookie（參考「步驟二」）
3. 用解析工具確認新 Cookie 帳號資訊正確
4. 前往 GitHub Repo → **Settings → Secrets and variables → Actions**
5. 找到 `BAHAMUT_COOKIE`，點 **Update**，貼入新的 Cookie 字串

***

## ⚠️ 注意事項

- 此工具僅供個人學習與自動化使用，請勿用於大量帳號或商業目的
- Cookie 字串包含帳號敏感資訊，**絕對不要公開分享你的 Cookie**
- GitHub Secrets 已加密儲存，不會在 Actions 執行紀錄中顯示

***

## 📝 更新紀錄

| 日期 | 說明 |
|---|---|
| 2026-05-09 | 修正 Cookie 解析工具連結為 htmlpreview 直接開啟網址 |
| 2026-05-09 | 修正 BAHARUNE JWT 欄位解析（`userid` / `username` / `mid`），移除廢棄欄位警示 |
| 2026-05-09 | Cookie 解析工具新增帳號資訊卡（暱稱 + 會員 ID + 帳號 + 到期日） |
| 2026-05-09 | 初始版本建立，完成每日自動簽到與 Email 通知功能 |

***

*本工具與巴哈姆特官方無關。*
