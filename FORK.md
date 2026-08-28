# Fork 維護說明

本 repo fork 自 [`khoj-ai/khoj`](https://github.com/khoj-ai/khoj)，
沿用 GNU Affero General Public License v3.0 與完整 Git 歷史。

## 為什麼維護 fork

- 保留原作者持續更新的自託管個人 AI 知識庫、RAG、Agent、Obsidian／Emacs／桌面客戶端。
- 採 Windows-first 維護：Windows 11 + PowerShell 是主要開發、除錯與完整驗收環境。
- 公開入口改以繁體中文為主，英文鏡像放 `README.en.md`。
- 建立可重現的 Windows 開發 gate、Windows CI job，以及逐筆審查的上游追蹤。
- 產品執行路徑以上游 Docker／官方映像為準；本線不發佈套件、映像或文件站。

**回貢判準：修的是上游的 bug 就送回去；這裡獨創的文件／Windows 維護骨架留在這裡。**
回貢前必須在當次對話取得維護者明確同意；「fork」「建開發環境」「開 PR」都不是同意。

## 與上游的差異

| 項目 | 說明 |
|---|---|
| `README.md` | 繁中主檔；上游英文移到 `README.en.md` |
| `AGENTS.md` / `CLAUDE.md` | 本 fork 的 AI 維護單一真相源 |
| `NOTICE.md` / `FORK.md` | 來源、授權與同步說明 |
| `tools/dev_check.ps1` | Windows 本機一鍵 gate（維護工具，不安裝產品依賴） |
| `.github/workflows/ci.yml` | Ubuntu 3.10–3.14 + Windows Python 3.14：compile / ruff / 維護測試 / 連結檢查 |
| `.github/workflows/upstream-check.yml` | 每週對 `upstream/master` 做未審查 commit 檢查 |
| 發佈與產品 CI workflow 閘門 | PyPI、GHCR、GitHub Pages、桌面、Obsidian release、eval、上游 `test.yml`／pre-commit／Emacs 只允許 `khoj-ai/khoj` |
| `docker-compose.yml` | fork overlay：埠綁 `127.0.0.1`、關匿名模式與遙測、computer 走 `--profile operator` |
| `docs/DECISIONS.md`、`docs/UPSTREAM.md`、`docs/DEVELOPMENT.md` | fork 維護文件 |
| `REVIEW.md` | 全庫風險快照；Compose／operator overlay 已記錄 |

產品程式（`src/khoj`、客戶端、上游 `test.yml`）以上游為準，除非 `REVIEW.md`／`docs/DECISIONS.md` 已記錄 fork overlay。目前 overlay：Compose 硬化、UI-TARS `ast.literal_eval`、operator 本機指令不走 shell flag。

## 分支與 remote

- `origin/main`：SanHsien 維護線，也是唯一長期分支。
- 日常修改在本機跑 gate 後直接推 `origin/main`。
- `upstream/master`：khoj-ai 原始專案，只追蹤、不推送。
- Dependabot 或外部 fork 的變更走 PR，讀 diff 並通過 CI 後再合併。

不要 `git push upstream`。同步方式見 [`docs/UPSTREAM.md`](docs/UPSTREAM.md)。

上游更新英文 `README.md` 時，把新內容併進 `README.en.md`，再把對應段落翻進本 fork 的繁中 `README.md`。

## 換一台電腦怎麼開發

```powershell
git clone https://github.com/SanHsien/khoj.git
cd khoj
# `gh repo clone` 已會加上 `upstream` remote；若沒有：
# git remote add upstream https://github.com/khoj-ai/khoj.git
pwsh -NoProfile -File tools\bootstrap_dev.ps1
```

要實際跑 Khoj 伺服器，再用 Docker（見 [`README.md`](README.md)）或上游的 from-source 步驟（見 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)）。
