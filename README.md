# 巴哈姆特每日自動任務

自動執行每日簽到，並透過 Email 通知動畫瘋答題答案。

---

## 功能

- ✅ 每日自動簽到（台灣時間 05:00 執行）
- 📋 自動抓取動畫瘋每日答題答案，Email 通知
- ⚠️ Cookie 到期前 7 天自動發信提醒
- 🔑 CSRF Token 每次自動生成，無需手動維護

---

## 運作原理

1. GitHub Actions 依排程自動執行 `signin.py`
2. 程式讀取 Secrets 中的 `BAHAMUT_COOKIE`（只需包含 `BAHARUNE`）
3. 自動生成 CSRF Token，不依賴 Cookie 中的舊值
4. 執行簽到，並從 blackxblue 的創作列表 API 抓取今日答題答案
5. 寄送 Email 通知結果

---

## 設定步驟

### 步驟一：Fork 此 Repo

點擊右上角 **Fork**，複製到自己的帳號。

### 步驟二：設定 GitHub Secrets

前往 Repo → **Settings → Secrets and variables → Actions → New repository secret**，新增以下四個 Secrets：

| Secret 名稱 | 說明 |
|---|---|
| `BAHAMUT_COOKIE` | 巴哈姆特登入 Cookie（見下方說明） |
| `EMAIL_USER` | 寄件 Gmail 帳號（例：`yourmail@gmail.com`） |
| `EMAIL_PASS` | Gmail 應用程式密碼（非登入密碼） |
| `EMAIL_TO` | 收件 Email |

#### 如何取得 BAHAMUT_COOKIE

1. 使用 **Edge 或 Chrome** 登入 [https://www.gamer.com.tw/](https://www.gamer.com.tw/)
2. F12 → **Application → Cookies → www.gamer.com.tw**
3. 複製所有 Cookie 字串
4. 確認包含 `BAHARUNE` 欄位（有效期約 30 天）
5. **複製完後立刻關閉巴哈分頁，不要繼續操作**
6. 貼入 `BAHAMUT_COOKIE` Secret

> ⚠️ 請使用固定的瀏覽器複製 Cookie，下次更新也要用同一個瀏覽器。

### 步驟三：啟用 GitHub Actions

前往 Repo → **Actions** 頁面，點擊 **I understand my workflows, go ahead and enable them**。

### 步驟四：確認排程

Actions 設定完成後即會依排程自動執行。  
預設時間為每天**台灣時間 05:00（UTC 21:00）**。

你也可以在 Actions 頁面手動點 **Run workflow** 來測試是否正常運作。

---

## Cookie 更新方式

Cookie（`BAHARUNE`）有效期約 **30 天**。  
到期前 7 天，程式會自動寄出提醒信。

收到提醒信後：

1. 用原本的瀏覽器進入巴哈，確認已登入
2. F12 → Application → Cookies → 複製整串 Cookie
3. **複製後立刻關閉巴哈分頁**
4. 前往 GitHub Secrets → 更新 `BAHAMUT_COOKIE`
5. 手動 Run workflow 確認正常

> `ckBahamutCsrfToken` 不需要特別維護，程式每次執行時自動生成。

---

## Email 通知範例
