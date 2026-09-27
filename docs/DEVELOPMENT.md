# 開發環境

維護者與 AI 接手用的開發文件。產品使用方式在 [`README.md`](../README.md)；上游同步在 [`UPSTREAM.md`](UPSTREAM.md)；決策在 [`DECISIONS.md`](DECISIONS.md)。上游英文開發步驟在 <https://docs.khoj.dev/contributing/development>。

## 架構

```text
客戶端（Web / Obsidian / Emacs / Desktop / Android / WhatsApp）
        │
        ▼
 src/khoj          FastAPI + Django
        ├── routers / processor     對話、RAG、搜尋、Agent
        ├── database                pgvector
        └── interface               組進去的網頁資產
        │
        ▼
 Postgres (pgvector)  +  本機 Ollama 或雲端 LLM
        │
 docker-compose.yml 還可帶 SearxNG、Terrarium sandbox、khoj-computer
```

`src/khoj` 與 `src/interface/` 是產品。根目錄 `tools/`、`docs/`、`AGENTS.md` 是本 fork 的開發與治理骨架。

## 本機開發（Windows）

### 維護骨架（必跑）

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements-dev.txt
$env:PYTHONUTF8 = "1"
pwsh -NoProfile -File tools\dev_check.ps1
```

等價一鍵：

```powershell
pwsh -NoProfile -File tools\bootstrap_dev.ps1
```

這套 gate **不安裝** torch、Django、sentence-transformers。它只證明維護文件、工具與契約測試能跑。

### 實際跑 Khoj（建議 Docker）

```powershell
docker compose up -d
```

瀏覽器開 <http://127.0.0.1:42110>，用 Compose 裡的管理員帳密登入（本 fork 已關匿名模式）。連本機 Ollama 見 [`README.md`](../README.md)。operator／VNC 要 `docker compose --profile operator up -d`。資料在 Docker named volume，不要複製進 git。

### 從原始碼跑（選配，重）

上游要求 Python **3.10–3.12**（`pyproject.toml` 寫 `>=3.10, <3.13`），以及 Postgres + pgvector、前端 bun 建置：

```powershell
# 另開一個 3.12 venv，不要跟維護用的 .venv 混在一起
uv python install 3.12
uv sync --all-extras
cd src\interface\web
bun install
bun export
cd ..\..\..
khoj -vv
```

Windows 上 pgvector 仍屬實驗性，上游建議 Docker。細節與常見錯誤見 <https://docs.khoj.dev/contributing/development> 的 Windows 段。

Obsidian 外掛開發在 `src/interface/obsidian`：`yarn install` 後 `yarn dev`，把產出的 `main.js` 換進 Obsidian 已安裝的 Khoj 外掛目錄。

## Canonical gate

`tools\dev_check.ps1` 會依序：

1. `python -m compileall`（`tools`）
2. `ruff check`（E9 + F，僅 `tools`）
3. `pytest tools/tests`（覆寫根目錄 `pytest.ini` 的 Django `addopts`）
4. `python tools/check_links.py`

CI 在 Ubuntu 跑 3.10–3.14，並加一個 Windows Python 3.14 job 跑同一套 gate。推 `main` 前先跑本機 gate。

上游 `test.yml` 仍聽 `master`，在完整 Khoj 依賴 + Postgres 上跑產品測試。本線日常不重跑那套。

## 依賴新鮮度

`tools/check_dependency_freshness.py` 只比對 `requirements-dev.txt`。產品 pin 在 `pyproject.toml`，由 Dependabot 開 PR；合併前讀 diff。

紅燈只有兩條誠實的出口：

| 出口 | 寫在哪 | 什麼時候用 |
| --- | --- | --- |
| `# freshness-hold: <理由>` | `requirements-dev.txt` 行末 | 這個下限就是我們要的 |
| `.github/dependency-deferrals.json` 的 `deferredLatest` + `reason` | 獨立檔案 | 已看過、這個月不升；PyPI 超過該版本會恢復提醒 |

不要用調高下限讓報告變綠。

## 不要做的事

- 不要拿掉發佈 workflow 上的 `github.repository == 'khoj-ai/khoj'` 閘門。
- 不要從本 fork 跑 `uv build` 後上傳 PyPI，或 `docker push` 到 `ghcr.io/khoj-ai/*`。
- 不要提交 `~/.khoj/`、Docker volume、模型快取或使用者文件。
- 不要把 `documentation/` 部署到 `docs.khoj.dev`。
- 測試必須是人造樣本與靜態規格檢查，不能拿真實筆記當 fixture。
