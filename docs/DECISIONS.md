# 維護決策

## 2026-08-27：建立 Windows-first 維護型 fork

**決定**：fork `khoj-ai/khoj`，保留 GNU AGPL v3.0 與完整歷史。本線預設分支用 `main`；上游仍是 `master`。本線聚焦繁中文件、Windows 開發 gate、Windows CI，以及逐筆審查的上游追蹤。

**理由**：Khoj 已是可用的自託管第二大腦（本機文件、Ollama、Obsidian、Docker 一行啟動），符合重視隱私的筆記工作流。缺的是 Windows 11 上可重現的開發／驗收骨架，以及繁中入口。直接用上游 repo 難以長期記錄 fork 取捨。

**限制**：

- 不把 fork 包裝成原創專案，不移除原作者與官方連結。
- 不發佈 PyPI、GHCR、docs.khoj.dev、Obsidian 外掛或桌面安裝檔。
- 維護 gate 不安裝產品 ML 依賴。
- 上游更新必須逐筆審查。

## 2026-08-27：發佈 workflow 加上游 repo 閘門

**決定**：在 `pypi.yml`、`dockerize.yml`、`github_pages_deploy.yml`、`release.yml`、`desktop.yml`、`dockerize_telemetry_server.yml`、`run_evals.yml` 加上 `if: github.repository == 'khoj-ai/khoj'`。

**理由**：這些 workflow 聽 `master` 或 tag。本線雖改用 `main`，tag 或誤推 `master` 仍可能把套件發到 PyPI、把文件推到 `docs.khoj.dev`，或用本 fork 的 token 推 GHCR。閘門讓那些工作在本 fork 直接跳過。同步上游時若衝突，保留閘門。

## 2026-08-27：依賴新鮮度只看維護工具

**決定**：`tools/check_dependency_freshness.py` 只讀 `requirements-dev.txt`。`pyproject.toml` 的產品 pin 交給 Dependabot。

**理由**：上游有數十個精確 pin（torch、Django、transformers…）。每月拿它們對 PyPI 會永遠紅燈，報告會被忽略。Dependabot 已能對產品依賴開 PR；維護工具的地板檢查保持可讀。

## 2026-08-27：不啟用 Dependabot 自動合併

**決定**：Dependabot 只開 PR；CI 與人工讀 diff 通過後才合併。

**理由**：產品依賴會改 RAG 品質、Windows 安裝體積與授權面，不適合自動合併。

## 2026-08-27：維護工具宣告 pytest 9

**決定**：`requirements-dev.txt` 寫 `pytest>=9`。本機 gate 已在 Python 3.14 用 9.1.1 跑過 20 個測試。CI 矩陣最低 3.10，符合 pytest 9 的下限。

**理由**：第一次每月檢查對 `pytest>=8.3.0` 報 9.1.1 待審。這不是消音，是把已驗證的執行環境寫進相容性承諾。

## 2026-08-27：審查後只修 overlay 契約，不改產品預設

**決定**：全庫審查（`REVIEW.md`）修 gitignore、安全文件與契約測試。不改 `docker-compose.yml` 預設密碼／匿名模式／遙測，不改 `src/khoj` 的 `eval(`／`shell=True`。

**理由**：那些是上游 quickstart 與產品行為。本線改了會在每次 `upstream/master` 同步衝突，也會讓 docs.khoj.dev 的 Docker 步驟對不上。殘餘風險寫進 `SECURITY.md` 與 `REVIEW.md`。

## 2026-08-27：審查可修項改在本線 overlay，不回貢

**決定**：推翻上一則「不改 Compose／operator」的限制。本線硬化 `docker-compose.yml`（loopback、關匿名、關遙測、computer 走 profile）、UI-TARS 改 `ast.literal_eval`、operator 本機指令改 `bash -c`、產品 CI workflow 加上游 repo 閘門。不 pin 已閘門 workflow 的浮動 Action tag。不把產品 Python 上限改成 3.14。不回貢上游。

**理由**：維護者要求審查裡可修的都修，且先不考慮回貢。Compose 與 `src/khoj` 的 overlay 會在上游同步時衝突，合併時以本線硬化為準。

## 2026-08-27：日常直接推 main

**決定**：日常修改在本機跑 `tools\dev_check.ps1` 後直接推 `origin/main`。Dependabot 與外部貢獻仍走 PR，合併前讀 diff。

**理由**：對齊其他 SanHsien 維護 fork。產品測試仍在上游 `test.yml`；本線 gate 是維護骨架。

## 2026-08-29：上游檢查補上 PR 與 issue 兩個面向

**決定**：`check_upstream_updates.py` 補上以 `--state all` 收集上游 PR／issue 的邏輯，
`upstream-check.yml` 補 `GH_TOKEN: ${{ github.token }}`，新增 `tests/test_upstream_updates.py`。
Baseline 既有的水位不動。

**理由**：`docs/UPSTREAM.md` 早就寫著「四個面向都要看」，`upstream_baseline.json` 也記著
`reviewed_pr_through` 與 `reviewed_issue_through`——但**沒有任何程式讀那兩個欄位**，檢查器只比對
commit 水位。那兩個面向不是「查過沒發現」，是根本沒查，而每週的排程報告長得跟查過一樣綠。
這是艦隊層級的問題：24 個 fork 裡 21 個都這樣（`SanHsien/repo-fleet-ops` 的 `docs/INCIDENTS.md`
第十條）。參考實作是 `SanHsien/harness-guard`。

三個性質，缺一不可：

- **`--state all`**：只查 `open` 看不到「開了又關、沒有合併」的 PR，而那正是「上游拒收、但可能對
  本 fork 有價值」的一類——已合併的遲早會經由 commit 抵達，被關掉的永遠不會。
- **`gh` 失敗時回 `None` 不回 `[]`**，報告寫 `Not checked` 並 **fail closed**（exit 2）。
  「沒查到」和「沒有」在綠色報告裡長得一樣，只有一個是真的。
- **`GH_TOKEN`**：`gh` 在 Actions 裡沒有憑證就列舉不到，配上 fail closed 會讓紅燈的意思變成
  「檢查器壞了」而不是「上游有東西」。

**證據**：落地後實跑 `python tools/check_upstream_updates.py`，三個面向都印出水位與待辦數；
本 repo 的 gate 全綠。

**已知代價**：水位以上真的有東西時，每週的 upstream-check 會回 exit 1。那是它該做的事——先前的
綠燈不是「沒有待辦」，是沒有人看。

**觸發條件**：報告列出項目時逐筆讀 diff、把採用／略過理由寫進本檔，然後才推進 baseline 的水位。
