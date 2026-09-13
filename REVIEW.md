# Repository review（Windows-first）

- Review date: 2026-08-27
- Review baseline: `af04f94806e13de49c23c2c662fd1f5a4ea7eceb`
- Remediation: 同日 fork-local overlay（不回貢）
- Upstream reviewed through: `ae229ca894c0b80ad84664afcfdde523b5e87057`
- Primary environment: Windows 11、PowerShell、Python 3.14.7（本機 gate）；產品執行建議 Docker；from-source 需 Python 3.10–3.12
- Status: 維護骨架可用。R-01～R-08、R-10 已在本線修。R-09（已閘門 workflow 的浮動 Action tag）與 R-11（產品 Python `<3.13`）接受。

## 結論

這個 fork 適合作為 Windows 本機、給 Agent 維護的 Khoj 自託管線。產品行為跟隨 `khoj-ai/khoj` `ae229ca`，再加上本線 overlay：Compose 埠綁 `127.0.0.1`、關掉匿名模式與遙測、computer 服務走 `--profile operator`、UI-TARS 用 `ast.literal_eval`、operator 本機指令走 `bash -c`。

預設 `docker compose up` 只聽本機、要登入、不送遙測。檔裡仍有範例管理員密碼與 `KHOJ_DJANGO_SECRET_KEY=secret`；把埠改成對區網或網際網路開放前必須換掉。

不把 fork 當成第二個官方產品 repo。Docker 映像、PyPI `khoj`、docs.khoj.dev 與 Obsidian 外掛仍屬上游。本線 Windows gate **不安裝** torch／Django，因此 **不能** 證明 Khoj 伺服器在這台 Windows 上已可對話。

## 本輪實證

### 審查當下（`af04f948`）

```text
git rev-parse HEAD
→ af04f94806e13de49c23c2c662fd1f5a4ea7eceb

pwsh -NoProfile -File tools\dev_check.ps1（修正前）
→ 20 passed、WINDOWS DEV CHECK GREEN（建置輪）

GitHub Actions（SanHsien/khoj，af04f948）
→ CI success https://github.com/SanHsien/khoj/actions/runs/33086575546
→ CodeQL success https://github.com/SanHsien/khoj/actions/runs/33086575468
→ Dependency freshness success https://github.com/SanHsien/khoj/actions/runs/33086575332
→ 骨架提交的 Upstream check success https://github.com/SanHsien/khoj/actions/runs/33086320233
```

實查（不是只讀 README）：

- 發佈類 workflow 七份都有 `github.repository == 'khoj-ai/khoj'`。
- `src/khoj/app/settings.py:26` 與 `configure.py:406` 預設 secret 為 `!secret`。
- 審查當時 `docker-compose.yml`：`KHOJ_DJANGO_SECRET_KEY=secret`、`KHOJ_ADMIN_PASSWORD=password`、`--anonymous-mode`、遙測註解關著、`42110:42110`、computer `5900:5900`。
- CLI 預設 `--host 127.0.0.1`；Compose 容器內仍 `--host 0.0.0.0`（給 port mapping 用）。
- 遙測端點 `src/khoj/utils/constants.py`：`https://khoj.beta.haletic.com/v1/telemetry`。
- `grounding_agent_uitars.py` 當時對 box 字串用 `eval(`；`operator_environment_computer.py` 本機路徑 `shell=True`。

**沒有**用 Docker 啟動 Khoj，**沒有**跑上游 `uv sync --all-extras`／`pytest`，**沒有**連 Ollama 對話。

### 修正後

```text
pwsh -NoProfile -File tools\dev_check.ps1
→ 25 passed、WINDOWS DEV CHECK GREEN
→ check_links.py：13 份文件、0 斷連結
```

## 已修 findings

| ID | 嚴重度 | 做了什麼 |
|---|---|---|
| R-01 | P2 | 恢復 `.gitignore` 的 `src/interface/android/local.properties` |
| R-02 | P2 | `.gitignore` 加 `notes/`、`vaults/`、`.khoj/`、`conversations.json` |
| R-03 | P2 | `SECURITY.md`／繁中與英文 README 寫明 Compose 預設與殘餘風險 |
| R-04 | P3 | `tools/tests/test_fork_docs.py` 鎖 gitignore、安全文件、Compose overlay、operator、workflow 閘門 |
| R-05 | P2 | Compose **拿掉** `--anonymous-mode`；`42110` 綁 `127.0.0.1`。範例管理員密碼仍在檔裡，只供本機登入 |
| R-06 | P2 | Compose 預設 `KHOJ_TELEMETRY_DISABLE=True` |
| R-07 | P2 | UI-TARS box 解析改 `ast.literal_eval`；operator 本機指令改 `["bash", "-c", command]`，不再設 shell flag |
| R-08 | P3 | `test.yml`、`pre-commit.yml`、`build_khoj_el.yml`、`test_khoj_el.yml` 加上 `github.repository == 'khoj-ai/khoj'` |
| R-10 | P3 | computer 服務加 `profiles: [operator]`；VNC 綁 `127.0.0.1:5900` |

## 接受、不改契約

| ID | 嚴重度 | 處理 |
|---|---|---|
| R-09 | P3 | **不 pin** 上游 workflow 的浮動 Action tag。那些 job 已閘在 `khoj-ai/khoj`，本 fork 不會跑。本線 `ci.yml`／CodeQL／upstream-check／freshness 已 SHA pin |
| R-11 | P3 | 產品 Python `<3.13`；維護 gate 用 3.14。這是執行環境事實，不是 bug |
| R-12 | P3 | Compose 仍寫範例管理員密碼與 `KHOJ_DJANGO_SECRET_KEY=secret`、Postgres `postgres/postgres`（DB 未發佈埠）。本機 loopback 可接受；對網開放前必須改。from-source fallback 仍是 `!secret` |

## 已檢查、不列為 finding

- `LICENSE` 為 GNU AGPL v3 全文；`NOTICE.md` 保留 khoj-ai 作者與 copyleft 網路服務義務。
- `gh api repos/SanHsien/khoj`：`fork=true`，`parent=khoj-ai/khoj`，預設分支 `main`。
- `gh repo set-default --view` → `SanHsien/khoj`。
- Dependabot 只開 PR，不自動合併。新鮮度只看 `requirements-dev.txt`。
- Fork 的 `ci.yml`、CodeQL、upstream-check、dependency-freshness 的 checkout／setup-python／codeql-action 已 pin SHA。
- `docker.sock` 掛載在 Compose 裡仍是註解。
- CLI 未走 Docker 時預設綁 `127.0.0.1`。
- 維護工具無 `os.system`／`shell=True`／`eval(`／`exec(`。
- `tools/pytest.ini` 避開根目錄 Django `pytest.ini` 的 `--reuse-db`。
- 公開入口繁中／英文互指，並點名 `FORK.md`。

## 尚未宣稱範圍

- **沒有**用 Docker 或 from-source 啟動 Khoj，也**沒有**用 Ollama／雲端模型實際對話。因此不宣稱 overlay 後 Compose 已在這台機器跑過一輪登入。
- **沒有**跑上游 Ubuntu `test.yml`（Postgres + `uv sync --all-extras`）。
- **沒有**在未設 `PYTHONUTF8` 的 CP950 主控台證明產品 CLI 可印中文。
- **沒有**評估 RAG 品質、Obsidian 外掛或桌面安裝檔。
- **沒有**獨立確認遙測伺服器現在收到什麼欄位（以原始碼與 `4d7ac85` 為準）。
- `dev_check.ps1` **不含** Bandit、上游 pytest、CodeQL。
- **不宣稱** fork 有自己的 GitHub Release 或獨立版號。
- **不宣稱** 已把 `documentation/` 翻成繁體。
- **不宣稱** 已把 overlay 送回上游。

## 建議下一步

1. 本機當日常第二大腦：`docker compose up -d` 後用管理員帳密登入，改掉範例密碼與 `KHOJ_DJANGO_SECRET_KEY`，再連 Ollama。
2. 要開 operator：`docker compose --profile operator up -d` 並設 `KHOJ_OPERATOR_ENABLED=True`。
3. 上游 PR #1409（SECRET_KEY 警告）、#1408（`ast.literal_eval`）若進 `master`，同步時對 overlay 做三方合併，不要盲目覆蓋本線硬化。
4. 之後維護直接推 `origin/main`。回貢需當次對話明確同意。
