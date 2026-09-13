# AGENTS.md

給 Codex、Claude Code、Cursor 與其他自動化代理在本專案工作時的指引。產品與使用方式先讀 [`README.md`](README.md)；開發與驗收細節見 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)。

## 專案定位

這是 [`khoj-ai/khoj`](https://github.com/khoj-ai/khoj) 的 GNU AGPL v3.0 fork。
核心價值是可自託管的個人 AI 第二大腦：讀本機筆記與文件、可離線用 Ollama、也可切雲端模型，並提供網頁、桌面與 Obsidian 外掛。

`origin` 是 `SanHsien/khoj`（預設分支 `main`），`upstream` 是原作者 repo（預設分支 `master`）。
保留上游作者、AGPL-3.0 與產品程式。本 fork 的維護差異記在 [`FORK.md`](FORK.md) 與 [`docs/DECISIONS.md`](docs/DECISIONS.md)。

主要開發與完整驗收環境是 **Windows 11 + PowerShell**。上游 Ubuntu `test.yml` 補產品測試；本線 `ci.yml` 只驗維護骨架。

## 硬性邊界

- 不提交筆記、Obsidian vault、PDF、聊天紀錄、API key、cookie、`.env` 或 Docker volume 資料。
- 不推送到 `upstream`。上游同步先跑 `python tools/check_upstream_updates.py`，逐筆審查後再 merge / cherry-pick；不盲目覆蓋 fork 文件與 Windows gate。
- 不發佈到 PyPI、GHCR、docs.khoj.dev、Obsidian 商店或桌面發行管道。那些 workflow 已加 `khoj-ai/khoj` 閘門，不要拿掉。
- 不要把維護 gate 改成 `uv sync --all-extras`。產品依賴含 torch／whisper，不屬於本線一鍵驗收。
- 產品 Python 是 `>=3.10, <3.13`。Windows gate 用 3.14 只跑維護工具，不代表 Khoj 伺服器能在 3.14 執行。
- 不把 fork 包裝成原創產品，不移除上游作者、贊助或官方連結。

## 技術與資料流

- 伺服器：`src/khoj`（FastAPI + Django、RAG、pgvector）。
- 客戶端：`src/interface/web`（Next.js）、`obsidian`、`emacs`、`desktop`、`android`。
- 自託管：`docker-compose.yml`（Postgres／pgvector、SearxNG、 Terrarium sandbox、Khoj server）。
- `tools/`：fork 維護工具（Windows gate、上游檢查、相對連結檢查、依賴新鮮度）。
- `tools/tests/`：維護契約測試。不要放進上游 `tests/`，那裡的 `pytest.ini` 綁 Django。

## 開發原則

- 一般變更直接推 `origin/main`，不開功能分支、不開維護 PR（2026-08-22 起）。只有在需要他人審查、或改動風險高到值得先讓 CI 在 PR 上跑一輪時，才退回 **branch → PR → CI → merge**。
- 修 bug 先補可重現失敗測試，再做最小修正。
- 上游公開 CLI、Obsidian 外掛與 docs.khoj.dev 的安裝步驟視為相容性契約。本 fork 的 `docker-compose.yml` 另做本機硬化（見 `REVIEW.md`）；同步上游時保留 overlay。
- 不為了套格式而大改上游程式；Ruff 只閘維護工具的 E9（語法）與 F（pyflakes）。
- 使用繁體中文回覆；使用者文件以繁中為主，公開入口同步維護 `README.en.md`。
- 上游更新英文 `README.md` 時：把新內容併進 `README.en.md`，再翻進繁中 `README.md`。
- 提交訊息用 Conventional Commit。Dependabot 或外部 fork 的變更也走 PR，讀 diff 並通過 CI 後再合併。
- `REVIEW.md` 是風險快照，不是每個一般 bug 的流水帳。
- 不 force-push `main`，不刪 `upstream` remote。

## 上游處理

1. `git fetch upstream master`
2. `python tools/check_upstream_updates.py --strict`
3. 逐筆判斷是否與繁中 README、Windows gate、發佈閘門或測試衝突。
4. 可同步的提交用 merge；只需要部分修正時 cherry-pick 或最小重做。
5. 跑 `pwsh -NoProfile -File tools\dev_check.ps1`
6. 採用／略過寫進 `docs/DECISIONS.md`，驗證後才推進 `tools/upstream_baseline.json`

Baseline 代表「已審查」，不代表「全部已合併」。

## 依賴新鮮度

每月的 `Dependency freshness` workflow 跑 `tools/check_dependency_freshness.py`，
只比對 `requirements-dev.txt` 的宣告與 PyPI 現行版。產品依賴在 `pyproject.toml`，由 Dependabot 開 PR，不走這條每月地板檢查——那些 pin 太多，會讓報告變成噪音。

紅燈只有兩種正當出口，兩種都要留下理由：

- **維持宣告**：在宣告那一行加 `# freshness-hold: <理由>`。
- **已延後**：在 `.github/dependency-deferrals.json` 加一筆
  `{"deferredLatest": "<當時看到的版本>", "reason": "<為什麼這次不升>"}`。

不要用調高下限的方式讓紅燈消失：宣告是相容性承諾，不是消音鍵。

## 驗證

```powershell
pwsh -NoProfile -File tools\bootstrap_dev.ps1
```

沒有實際跑過 Windows gate，不要宣稱本機開發環境已可用。沒有實際用 Docker 或 from-source 啟動伺服器，不要宣稱 Khoj 本機已可對話。

## 文件責任

- `README.md` / `README.en.md`：公開產品與 fork 入口。
- `FORK.md`：與上游的關係、差異、同步方式。
- `NOTICE.md`：授權與 attribution。
- `docs/UPSTREAM.md`：upstream remote 與審查清冊。
- `docs/DEVELOPMENT.md`：本機開發與驗收指令。
- `docs/DECISIONS.md`：長期取捨。
- `REVIEW.md`：全庫風險快照，不是每個一般 bug 的流水帳。
- `documentation/`：上游 Docusaurus 產品文件，行為變更才動。
- `CONTRIBUTING.md` / `SECURITY.md`：本 fork 的貢獻與安全回報流程。

## 對外邊界：PR 只打本 fork

- **PR、push、release 一律指向 `SanHsien/khoj`。** 對上游 `khoj-ai/khoj` 開 PR、push 或發 release
  需要維護者在當次對話明確同意回貢；「fork 一份」「建開發環境」「比照其他 repo」都不是同意。
- 根因是機制不是粗心：`gh` 在 fork clone 的**預設 repo 就是上游**（`gh repo set-default --view` 會回
  `khoj-ai/khoj`），裸跑 `gh pr create` 必然打上去。每個 clone 先跑一次
  `gh repo set-default SanHsien/khoj`。
- 開 PR 仍明寫 `gh pr create --repo SanHsien/khoj --base <分支> --head <分支>`，並**讀輸出的 URL**，
  owner 必須是 `SanHsien`。不是就立刻 `gh pr close` 留言道歉說明，再對 origin 重開。
- 2026-08-22 一天內兩個工作階段各誤開一個上游 PR（`lidge-jun/opencodex#2373`、
  `hamanpaul/paulsha-cortex#787`）。批次跑多個 repo 時最容易略過確認，而那正是兩次出事的場合。
