# 貢獻指南

歡迎能保住自託管邊界、隱私預設與審查成本的小改動。

## 開始前

1. 先讀 [`AGENTS.md`](AGENTS.md)、[`FORK.md`](FORK.md) 與 [`README.md`](README.md)。
2. 確認問題在最新 `main` 仍可重現，並查過既有 Issues。
3. 產品行為的實質變更，優先考慮回報或回貢 [`khoj-ai/khoj`](https://github.com/khoj-ai/khoj)。上游開發步驟在 <https://docs.khoj.dev/contributing/development>。
4. 不要附上筆記、vault、聊天紀錄或任何憑證。

## 本機開發

```powershell
pwsh -NoProfile -File tools\bootstrap_dev.ps1
```

這只驗證維護骨架。要跑 Khoj 伺服器見 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)。

## 提交方式

本 fork 由維護者直接推 `main`，不開短期分支。改完先跑上面的 Windows gate。

- 一次提交聚焦一個問題。
- Bug 修正先附失敗測試；新行為需涵蓋成功、邊界與錯誤路徑。
- 修改使用方式時同步更新 `README.md` 與 `README.en.md`。
- 說明是否來自 upstream、是否改動 `src/khoj`／Docker／客戶端，以及實際跑過哪些指令。
- 提交訊息建議使用 `fix:`、`feat:`、`docs:`、`test:`、`chore:`。
- Dependabot 與外部 fork 仍可能開 Pull Request；合併前讀 diff，不要自動合併。
