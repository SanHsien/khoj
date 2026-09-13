# 上游維護

## Remote

- Fork：`origin` → `https://github.com/SanHsien/khoj.git`（預設分支 `main`）
- 原作者：`upstream` → `https://github.com/khoj-ai/khoj.git`（預設分支 `master`）
- 追蹤分支：`master`

## 檢查新提交

```powershell
git fetch upstream master
python tools\check_upstream_updates.py --strict
```

工具以 `tools/upstream_baseline.json` 的 `reviewed_through` 為起點，列出所有未審查提交。
有新提交或檢查失敗時，`--strict` 回傳非零；排程 workflow 也會因此明確失敗。

CI 沒有 `upstream` remote，所以 baseline 的 `repo` 寫完整 clone URL，不要寫遠端短名。

## 審查清冊

每次只做一次批次審查：

1. 讀 commit 主旨與變更檔案（open PR 必須讀 diff，禁止只憑標題結案）。
2. 判斷是否與繁中 README、Windows gate、發佈閘門或測試衝突。
3. 可直接同步的提交用 merge；只需要部分修正時 cherry-pick 或最小重做。
4. 跑 `pwsh -NoProfile -File tools\dev_check.ps1`。
5. 在 `docs/DECISIONS.md` 記錄採用／略過理由。
6. 驗證完成後才把 baseline 推進到已審查的完整 40 字元 SHA。

Baseline 代表「已審查」，不代表「全部已合併」。

README 衝突的解法：上游新英文內容併進 `README.en.md`，再翻進 `README.md`。
`docker-compose.yml` 衝突時保留本線 overlay：埠綁 `127.0.0.1`、無 `--anonymous-mode`、`KHOJ_TELEMETRY_DISABLE=True`、computer 走 `--profile operator`。operator 的 `ast.literal_eval` 與本機 `bash -c` 同樣保留，除非上游已等效修正。

## 2026-08-27：fork 起點

本 fork 自上游 `master` `ae229ca894c0b80ad84664afcfdde523b5e87057`
（`Make chat export robust and fix export truncation (#1314)`）建立。此 SHA 設為第一個 `reviewed_through`。
之後的上游 commit 才需要進入審查清冊。

## 2026-08-27：上游 PR、issue、分支盤點

建立 fork 時**不引用**任何尚未進入 `master` 的 PR。本線第一個提交只加維護骨架。

當時 GitHub 上最新 issue 編號為 **#1415**，最新 PR 編號為 **#1412**。之後只看更大的編號，以及 baseline 之後的 commit。

未合併 PR 仍屬上游產品線（搜尋／PDF／Agent／文件連結等）。要採用時必須讀完整 diff，不能只看標題。部分開著的例子：

| 項目 | 本輪結論 |
| --- | --- |
| PR #1412、#1403 文件連結 | 不引用：未進 `master`；文件站由上游部署 |
| PR #1409 Django SECRET_KEY 警告 | 不引用：產品行為，下輪若仍開著再讀 diff |
| PR #1400 sandbox 安全 | 不引用：產品安全契約，需完整 diff |
| 其餘 open PR（#1385–#1411 等） | 不引用 |

### 分支

`gh repo fork` 會把上游其他分支收成 `upstream/*`。本線只維護 `origin/main`，對齊 `upstream/master`。`release/1.x` 與功能分支不追，除非審查清冊明確採用。

### 水位

- PR：已看到 **#1412**
- issue：已看到 **#1415**
- 記在 `tools/upstream_baseline.json`
