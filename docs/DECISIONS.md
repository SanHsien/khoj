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


## 2026-08-30：上游 PR #1417 採用（本 fork 實測重現），issue #1416 無可引用內容

PR 水位 1412 → 1417；issue 水位 1415 → 1416。

### 採用：`FileFilter.defilter()` 沒有清掉排除型檔案過濾器（上游 PR #1417）

**缺陷**：`defilter()` 只做一次 `re.sub(file_filter_regex, ...)`，而 `file_filter_regex` 帶
`(?<!-)` 前瞻否定，刻意不匹配 `-file:"..."`。結果排除型過濾器**整段留在查詢字串裡**送進搜尋，
過濾語法本身變成查詢詞。

**在本 fork 實測重現**（載入 `src/khoj/search_filter/file_filter.py` 這支真檔，只 stub 掉與本次
無關、會擋住 import 的 `anthropic` 與 `LRU`）：

| 輸入 | 修正前 | 修正後 |
| --- | --- | --- |
| `head -file:"file 1.org" tail` | `head -file:"file 1.org" tail` | `head tail` |
| `head file:"a.org" -file:"b.org" tail` | `head -file:"b.org" tail` | `head tail` |
| `head tail` | `head tail` | `head tail` |

`get_filter_terms()` 不受影響（仍回 `['a.org', '-file 1.org']`）。

**為什麼是真缺陷不是設計**：同一個 repo 的 `WordFilter.defilter` 本來就同時移除 required 與
blocked 兩種詞，`FileFilter` 只做一半是不一致。兩條 substitution 因為 `(?<!-)` 而彼此獨立，
順序無關。

**測試**：`tests/test_file_filter.py` 加一條涵蓋四種輸入。注意那份是**產品測試**，不在
`tools/dev_check.ps1` 的 fork gate（gate 只跑 `tools/tests`），而且本機缺 `anthropic` 跑不起來
——所以另外用上面那個載入真檔的方式實跑驗證過，不是只靠推理。

### 不引用：issue #1416

內容是**設定寫法說明**：自架 Khoj 要建兩筆 admin 資料（AI Model API 的 `api_base_url` 指到
`/v1` 根、Chat Model 的 `model_type` 選 `Openai`），並附一份 YAML 範例。沒有回報缺陷、也沒有
要求程式改動——是上游 admin UI 的使用說明。本 fork 沒有對應可引用的變更。

**觸發條件**：這個 issue 之後若轉成「某某設定組合在程式裡會壞」的缺陷回報，再重評。

## 2026-09-19：移除替上游收費服務廣告與外部付費導流

**決定**：全面清除非必要之上游商業收費服務宣傳與導流連結。

1. **文件層面（`README.md`、`README.en.md`）**：移除頂部「🔥 雲端試用（`app.khoj.dev`）」按鈕、內文推廣上游付費雲端的文案，以及推銷 Enterprise 收費商業方案（`khoj.dev/teams`）的章節，維持純粹的開源與自託管定位。
2. **首頁與介面層面（`src/khoj/interface/web/home/index.html`）**：移除首頁的 `Khoj Cloud` 宣傳橫幅、導覽列的 `Pricing` 連結，以及包含 Stripe 刷卡連結（`buy.stripe.com`）的定價方案區塊（Humanist / Futurist 付費卡片）。
3. **導覽選單（`src/interface/web/app/components/navMenu/navMenu.tsx`）**：移除導向 `https://khoj.dev/teams` 商業版頁面的選單項目與未使用的圖標引用。
4. **限額與客戶端提示（`src/khoj/routers/helpers.py`、`src/interface/desktop/`）**：將 API 請求超限或同步超額時誘導至 `https://app.khoj.dev/settings#subscription` 訂閱升級的文案，替換為中性的本機/伺服器容量與配額提示。

**理由**：本倉庫為純開源自託管的維護型 fork，自架用戶不應在本地或私有環境使用時看到替上游收費服務推廣、促銷定價或外連至 Stripe 付費的廣告內容。

## 2026-09-29：依賴安全升級

**已升級**（除 `esbuild` 為 0.x 破壞性小版升級外，都不跨主版）：

- 網頁：`next`／`eslint-config-next` 15.5.24，`bun run build` 通過。
- Obsidian 外掛：`esbuild` 0.14 → 0.25（`esbuild.config.mjs` 改用 `context().watch()`），
  resolutions 鎖 `undici ^7.29.1`、`dompurify ^3.4.13`、`brace-expansion ^2.1.2`；`yarn build` 通過。
- 桌面：`electron` 39.8.10，resolutions 鎖 `fast-uri ^3.1.6`、`brace-expansion ^1.1.18`、`builder-util-runtime ^9.7.0`、
  `js-yaml ^4.3.2`。只驗過 `electron-updater`、`js-yaml`、`minimatch` 可載入；Electron 本體未在本機實際啟動。
- 文件站：`yarn upgrade` 在既有範圍內刷新鎖檔，另鎖 `uuid ^11.1.1`（`sockjs` 只用 `v4()`）；`docusaurus build` 通過。
- Python：`mcp` 1.30.0、`soupsieve` 2.10（`uv lock --upgrade-package`）。`mcp` 已在隔離環境確認
  `processor/tools/mcp.py` 用到的 API 仍在。

resolutions 一律用 `^` 限在依賴方要求的主版內：`>=` 會把 `undici`、`brace-expansion` 拉到下一個
主版，建置照過，但執行期會壞。

**延後**（被 `pyproject.toml` 的固定版本或依賴上限擋住，上游也一樣）：

| 套件 | 現在 | 修補版 | 延後原因 |
| --- | --- | --- | --- |
| `torch` | 2.6.0（`== 2.6.0`） | 2.13.0；部分漏洞無修補版 | 跨 7 個小版且綁 `sentence-transformers == 3.4.1`，要實跑伺服器與 embedding 才能驗 |
| `transformers` | 4.53.3 | 5.10.0 | 主版升級；`sentence-transformers == 3.4.1` 要求 `transformers <5`，兩者要一起升 |
| `langchain`／`langchain-core`／`langchain-text-splitters` | 0.3.x | 1.x | 主版升級，`langchain-community == 0.3.31` 也要一起動 |
| `langsmith` | 0.8.5 | 0.8.18 | 本身只是小版更新，但要把 `websockets == 13.0` 升到 15；khoj 未直接使用 `langsmith`，漏洞在 `TracingMiddleware` |
| `extract-zip`（桌面） | 2.0.1 | 無修補版 | 只在 `electron` 安裝時使用 |

**觸發條件**：上游升這些版本、或能在本機用 Docker 實跑伺服器與 embedding 測試時，整組一起升。

## 2026-09-30：依賴 PR #18–#23 收尾

**已採用**：GitHub Actions 群組（#23，只改 workflow 版本）、`tzdata` 2026.4（#19，純時區資料）、
`stripe` 7.14、`twilio` 8.13、`pytest-django` 4.14、`email-validator` 2.3（#24、#27，小版，`uv.lock` 同步）、
`django` 5.2.17、`docx2txt` 0.9、`google-auth` 放寬到 `<2.59`（#45、#47、#48）、`pyjson5` 1.6.9、`psycopg2-binary` 2.9.13（#44、#41，補丁）、`beautifulsoup4`／`anyio` 範圍放寬（#38、#35）、`pytest-asyncio` 0.21.2（#34）、`einops` 0.8.2、`pytz` 放寬到 `<2027`（#33、#30）、
`apscheduler` 放寬到 `>=3.10,<3.12`（#20，`uv.lock` 同步到 3.11.3；3.11 不再依賴 `pytz`／`six`，
`pytz` 已在 `pyproject.toml` 直接宣告，並在隔離環境確認 `BackgroundScheduler`＋`CronTrigger` 可用）。
#19、#20 因 Dependabot 只改 `pyproject.toml`，不含 `uv.lock`，改為直接提交含鎖檔的版本。

**延後**：

| 套件 | 提案 | 延後原因 | 觸發條件 |
| --- | --- | --- | --- |
| `pyjson5` | 1.6.7 → 2.0.1（#22） | 主版升級，`processor` 解析 LLM 輸出用到，沒有產品測試覆蓋 | 有產品測試或本機實跑伺服器可驗 JSON5 解析 |
| `magika` | `~=0.5.1` → `<1.1.0`（#21） | 範圍放寬會納入 1.0.x，模型與執行期改版，檔案類型判斷行為可能變動 | 實跑檔案匯入並比對 1.x 偵測結果 |
| `gunicorn`／`stripe`／`twilio`／`pytest-asyncio`（`prod`／`dev` extras） | 22→26、7→15、8→9、0.21→1.4（#18） | 四個都是主版，`stripe`／`twilio` 只在託管服務路徑，`pytest-asyncio` 1.x 改變 event loop 設定；本 fork 不跑產品測試 | 逐一升級並在有產品測試環境驗證 |
| `pytest-asyncio` | 0.21.1 → 0.26.0（#24 內） | 0.23 起改 event loop 管理，上游 async 測試未在此驗證；其餘 #24 小版升級已採用 | 有產品測試環境時升級 |
| `anthropic` | 0.75 → 1.8（#28） | 主版，Anthropic 呼叫路徑無測試覆蓋 | 有產品測試或可實呼叫 API 驗證 |
| `resend` | 1.2 → 2.48（#26） | 主版，只在寄信路徑，無測試覆蓋 | 需要寄信功能時實測 |
| `django-unfold` | 0.42.0 → 0.81.0（#37） | 0.x 跨近 40 個小版，管理後台樣板與設定可能變動，無測試覆蓋 | 可實跑管理後台時 |
| `anthropic` | 0.75 → 0.125（#36） | 同上列，跨版過大且無測試覆蓋 | 同上 |
| `magika` | 0.5.1 → 0.6.x（#42，取代前述 1.x 提案） | 0.x 小版也換模型與輸出，檔案匯入判斷需比對 | 實跑檔案匯入並比對偵測結果 |
| `openai` | `<3` → `<4`（#39） | 範圍放寬納入 3.x 主版，無測試覆蓋 | 有產品測試時 |
| `torch`／`langchain-community` 等 | #43、#40 | 沿用 2026-09-29 延後項（torch、langchain 家族、langsmith），Dependabot 已加 `ignore` | 見 2026-09-29 觸發條件 |
| `markdownify` | `~=0.14.1` → `<1.3`（#50） | 範圍放寬納入 1.x 主版，HTML 轉 Markdown 輸出可能變動，無測試覆蓋 | 有產品測試時 |
| `cron-descriptor` | 1.4.3 → 2.1.0（#49） | 主版，與 `django-apscheduler == 0.7.0` 一起使用，需實跑排程頁 | 實跑排程管理頁時 |
| `websockets` | 13.0 → 16.1.1（#46） | 主版；與 2026-09-29 延後的 `langsmith` 同一組（`websockets == 13.0` 是刻意釘住），需一起驗證 | 隨 langsmith 升級一起處理 |
| `django-phonenumber-field` | 7.3 → 8.5（#25） | 主版，與 Django 模型欄位／遷移有關，需實跑遷移驗證 | 可用 Docker 實跑伺服器與遷移時 |
| `sentence-transformers` | 3.4.1 → 6.1.0（#31） | 主版，與 `torch`／`transformers` 延後項綁在一起 | 隨 torch／transformers 一起升 |
| `markdown-it-py` | `~=3.0.0` → `<4.3`（#32） | 範圍放寬納入 4.x 主版，無測試覆蓋 | 有產品測試時 |
| `pgvector` | 0.2.4 → 0.5.0（#29） | 0.x 多個小版，向量型別與 psycopg2 介面可能變動，需實跑資料庫 | 可用 Docker 實跑 Postgres 時 |

Dependabot 已對上述主版加 `ignore`（`semver-major`），避免重複開 PR。

## 2026-09-30：上游審查（commit 無新增；PR 1417 → 1444；issue 1416 → 1439）

上游 `master` 仍在 `ae229ca`，無新提交。14 筆 PR 與 7 筆 issue 全部未合併（PR 皆 OPEN；issue 1422、1431 已關閉）。本 fork 不跑產品測試，只採用小而自成一體、能在本機驗證的修正。

### 採用（3 筆，皆為本 fork 檔案中實際存在的缺陷）

| PR | 變更 | 本 fork 證據 | 驗證 |
| --- | --- | --- | --- |
| #1443 | `api_chat.py`：`elif event_type == REFERENCES or METADATA or stream` 改為 `in (...)`（1 行） | `src/khoj/routers/api_chat.py` 原為 `== ChatEvent.REFERENCES or ChatEvent.METADATA or stream`，恆為真 | `py_compile` |
| #1444 | `helpers.py` `generate_summary_from_files`：`file_objects or []`、`send_status_func` 判空、例外分支 `yield result` 改 `yield response_log`（+5/-3） | 原檔例外分支 `yield result`，`result` 未綁定即 `UnboundLocalError`；`file_objects=None` 且有 `query_files` 時迭代 `None` | `py_compile` |
| #1441 | `helpers.py` grep 前處理移除 `\b`／`\B`（+4）與一筆測試 | Postgres 把 `\b` 當 backspace，`\bword\b` 永遠不匹配 | 抽出 `re.sub` 表達式實測：`\bsailing\b` → `sailing`、`a\Bb\d` → `ab\d`、`\\b` 不動；`py_compile` |

以 `gh pr diff` 套用（PR 尚未合併，無上游 SHA 可 `cherry-pick -x`）。#1441 的 Postgres 端到端測試在本 fork 不會執行。
觸發條件：上游合併後若內容有異，於下一輪對照。

### 採用待辦（adoption pending）

| 項目 | 原因 | 觸發條件 |
| --- | --- | --- |
| #1424（PDF 暫存檔在 Windows 無法重開，+114/-7） | 動 PDF 索引路徑，需實跑 PDF 匯入才能驗；無產品測試 | 有產品測試環境，或上游合併 |
| #1430（工具選擇 fallback 崩潰，+42/-4） | 動聊天路由，需 agent 設定與資料庫 | 同上 |
| #1432（inline HTML 文字，+191/-7） | 動 HTML／網頁讀取，行為變更範圍大 | 同上 |
| #1440／#1437（markdown 標題無文字時卡住） | 動索引切分，需以長筆記實測 | 同上 |
| #1442／#1439（operator 拿到最近對話輪次） | 行為變更，需 operator 環境 | 同上 |

### 跟隨上游／不適用

| 項目 | 判斷 |
| --- | --- |
| #1418（Gandr TTS）、#1419／#1427（llmman、API Route 提供者命名）、#1425（Ollama 健康檢查）、#1435／#1434（Superfast Decision Gate，預設關閉） | follow-upstream：新功能或第三方服務整合，非缺陷修正 |
| #1426（搜尋查詢清理測試） | follow-upstream：僅新增上游測試 |
| issue #1421、#1422、#1431 | not-applicable：分析文章、新手詢問、社群指南（已關閉） |
| issue #1438 | 已由 #1441 採用 |

PR 水位 1417 → 1444；issue 水位 1416 → 1439。

## 2026-10-01：依賴安全升級與 Dependabot PR #54–#59 採用

PR #54（桌面 `axios` 1.20.0，修復 11 筆 Axios 漏洞）、PR #55（`pyjwt` 2.15.0，修復 11 筆 PyJWT 漏洞）、PR #56（`click <8.5.1`）已直接合併進 `main`。

**本提交採用**：
- Obsidian 外掛：resolutions 鎖定 `moment ^2.31.0`，修復 Alert #206 路徑周遊漏洞；`esbuild` production build 通過。
- Python 鎖檔（`uv.lock`）：
  - `urllib3` 2.7.0 → 2.8.0，修復 3 筆 urllib3 漏洞（Alert #230–#232）。
  - `virtualenv` 20.38.0 → 21.14.2，修復 Alert #242 與 #243。
  - `gitpython` 3.1.59 → 3.1.62，修復 Alert #236、#237、#238、#240。
- Python 生產相依（`pyproject.toml` 與 `uv.lock` 同步）：
  - PR #58（小版與修補版）：`schedule` 1.2.2、`pymupdf` 1.28.2、`authlib` 1.8.0、`itsdangerous` 2.2.0、`pgvector` 0.2.5、`lxml` 6.1.3、`websockets` 13.1、`cron-descriptor` 1.4.5。
  - PR #59：`e2b-code-interpreter` 範圍放寬至 `>=1.0,<2.11`。

**延後**：
- PR #60：`phonenumbers` 8.13.27 → 9.0.40（跨主版，受 `django-phonenumber-field == 7.3.0` 綁定，待後續整體 Django 欄位遷移驗證時一併評估）。

## 2026-10-03：修正 sentence-transformers 本機模型載入風險

PR #61 提議升至 5.6.0，雖符合 Dependabot 警報 #234、#235 標示的首個修補版本，但實測遭竄改的本機模型 `modules.json` 仍可在 `trust_remote_code=False` 下執行自訂 Python 模組。本 fork 因此改採 `sentence-transformers == 6.1.0`，並將 `transformers` 下限設為本輪實測的 5.18.0（排除 GHSA-29pf-2h5f-8g72 所述低於 5.3.0 的版本）；`torch == 2.6.0` 暫不變。

隔離 Python 3.12 環境的完整依賴安裝、Khoj 查詢／文件 embedding 與本機微型 reranker 均通過。Windows 維護 gate 使用系統 Python 3.14 執行，38 個測試通過。6.1.0 對相同惡意 `modules.json` 拋出 `ValueError`，未執行自訂模組。同步改用新版 `CrossEncoder` 的 `model_name_or_path` 與 `activation_fn` 參數。未跑需要 Postgres 與外部模型的完整 `tests/test_text_search.py`；其餘 `torch` 安全負債仍須另外處理。

Dependabot 對這兩個套件改為只延後下一個主版的一般版本 PR，安全更新仍可提出；不再封鎖目前 5.x／6.x 系列的修補版。

## 2026-10-03：採用低風險依賴更新

採用 Dependabot #66 的 `phonenumbers` 8.13.55，仍維持 8.x；#60 的 9.x 主版繼續延後。採用 #68 將 `google-auth` 允許上限從 `<2.59` 放寬到 `<2.60`，並在 `uv.lock` 鎖定 2.59.1。鎖檔檢查、Windows 維護 gate、隔離 Python 3.12 的電話號碼解析與 Google credential transport smoke 已通過；PR CI 另行確認。

## 2026-10-04：採用 google-genai 2.x

採用 Dependabot #67 的 `google-genai == 2.25.0`，並同步 `uv.lock` 所需的 Pydantic 2.13.5。Khoj 使用的 Gemini 對話、串流、圖片與 Vertex client 呼叫面已在隔離 Python 3.12 環境做離線 API smoke；Windows 維護 gate 與鎖檔檢查通過。未用真實 API key 呼叫 Gemini／Vertex，也未跑需要資料庫的完整產品測試。

## 2026-10-04：採用 langchain-core 1.x 安全修補

採用 Dependabot #71 的 `langchain-core 1.3.3`，涵蓋安全警報 #120、#121 的首個修補版；`uv.lock` 同步解析 `langchain 1.2.18` 與相關依賴。Windows 實測發現舊 PDF／DOCX loader 在暫存檔仍開啟時重新讀取會失敗，因此改為先關檔、讀完後刪檔。隔離 Python 3.12 的產品模組匯入、PDF／DOCX 擷取、鎖檔與 Windows gate 通過；未跑需要資料庫的完整產品測試。`langchain`／`langchain-core` 後續小版與修補版恢復 Dependabot 提案，其他 LangChain 家族主版仍逐項評估。

## 2026-10-04：採用 GitPython 3.2 與 google-genai 2.26

採用 Dependabot #75 的 GitPython 3.2 相容範圍及 #76 的 `google-genai == 2.26.0`，同步更新 `uv.lock`。GitPython 仍是開發依賴；google-genai 本輪更新後再次檢查 Khoj 使用的 SDK 呼叫面。兩筆變更合併驗收，以免宣告與鎖檔分離。

## 2026-10-04：採用 Torch 2.13 安全更新

採用 Dependabot #78 的 `torch == 2.13.0`，同步更新 `uv.lock` 的 Linux CUDA 13 相依與 `sympy`／`triton`。Windows Python 3.12 安裝官方 CPU wheel 後，`torch 2.13.0+cpu`、`sentence-transformers 6.1.0`、`transformers 5.18.0` 的相依檢查通過。

Khoj 的 Django 初始化、預設 `thenlper/gte-small` embedding 查詢與文件向量化、預設 `mixedbread-ai/mxbai-rerank-xsmall-v1` reranker 推論均在 CPU 實測通過（384 維向量、兩筆文件與兩筆 rerank 分數）。Windows 維護 gate 38 個測試與鎖檔檢查通過。未跑需要 Postgres 的完整伺服器測試；Linux CUDA 路徑由鎖檔平台標記解析，未在本機 GPU 驗證。

