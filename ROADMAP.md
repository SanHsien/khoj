# 路線圖

> 本 repo 後續工作的單一真相源。做完一項，就在同一個 commit 刪掉那一列；新工作只加在這裡。
> 安全警報與其他 workflow 數字保留 2026-10-29 `main` `40b788545e92` 的歷史快照；Dependabot PR、alert 與 Dependency freshness 於 2026-11-07 重查，Compose smoke 於 2026-11-02 重查。

## 現況
`khoj-ai/khoj` 的 Windows-first 維護線：產品程式跟隨上游 `ae229ca`，加上 [`FORK.md`](FORK.md) 列的 overlay（Compose 硬化、日誌注入防護、寄信 autoescape 等），本線不發佈套件或映像。2026-10-29 查 `main`：Dependabot open alert 1 筆（low，`deepmerge`，文件站建置期依賴，無修補版）、code scanning 0；CI／CodeQL／Upstream check 最近一次 success（Dependency freshness、open PR 與 open alert 見下行 2026-11-07 更新）；issues 已停用，open issue 數「未查到」（查法：`gh api repos/SanHsien/khoj/dependabot/alerts?state=open`、`gh run list -R SanHsien/khoj -b main`）。
2026-11-07 更新：Dependabot open PR 0 筆（#111–#116 已於 2026-11-03 全數合併）；Dependabot open alert 只剩 #367（`deepmerge`，low，無修補版，已延後）；Dependency freshness [run 42062536705](https://github.com/SanHsien/khoj/actions/runs/42062536705)（2026-11-05）success。`docker-compose-smoke.yml` [run 41187490343](https://github.com/SanHsien/khoj/actions/runs/41187490343) 已在 `4d9cf94495f8246656f5ad733d759a2c76f8c181` 成功驗證伺服器啟動、health 200 與管理員登入 200；上游修正仍是 adoption pending，需逐筆驗證對應路徑，不能由通用 smoke 推定已驗收。
2026-11-08 更新：維護者已授權決策，Dependabot 告警 #367（`deepmerge`）決定以 `tolerable_risk` dismiss（無修補版且僅為文件站建置期依賴，見 `docs/DECISIONS.md` 2026-10-28 條目最終決定；待外部執行 patch 指令）；open Dependabot alert 0 筆（待 patch 落地），code scanning 0 筆。近期項目已全數清空。

## 近期：可以直接動手
| 項目 | 為什麼 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| 讓 `uv.lock` 與 `pyproject.toml` 重新同步 | `uv lock --check` 在 `944454b3` 失敗：Dependabot 合併（2026-11-03）後 `pyproject.toml` 已要求 `tzdata == 2026.6`、`stripe 7.14.1`，鎖檔仍是 2026.5／7.14.0；`uv lock --dry-run` 還會連動 `torch`、`google-genai` 與 CUDA 套件（鎖檔解析 `google-genai` 2.32.0，`pyproject.toml` 釘 2.34.0；`tools/tests/test_google_genai_contract.py` 以 `pyproject.toml` 為準）。2026-11-08 的伺服器實測因此用 `uv sync --frozen`，沒測到新版 | `uv lock` 後 `uv lock --check` 通過；`uv sync --frozen --python 3.11 --extra dev` 後照 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)「用內嵌 Postgres 在 Windows 跑伺服器」啟動，PDF 匯入、聊天、研究模式各跑一次成功 | Claude Sonnet | [`docs/DECISIONS.md`](docs/DECISIONS.md) 2026-11-08 條目 |

## 中期：等條件成立再做
| 項目 | 觸發條件 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| Google 圖片預設模型 `gemini-2.5-flash-image` 停用前換新 | 2027-03-15（Google 停用表的 shutdown date，建議換 `gemini-3.1-flash-lite-image`）；或 Vertex 用戶需要圖片生成走 `ai_model_api` 服務帳戶 | `src/khoj/utils/initialization.py` 預設值與 `src/khoj/processor/image/generate.py` 的 `is_multimodal_model` 對新模型名實跑一次產圖（需真實金鑰）；`tools/tests/test_google_genai_contract.py` 加入新名稱並通過；Vertex 路徑改用 `get_gemini_client` 後契約測試補 `ai_model_api` 案例 | Claude Sonnet | [`docs/DECISIONS.md`](docs/DECISIONS.md) 2026-11-09；<https://ai.google.dev/gemini-api/docs/deprecations> |
| 審上游新變更 | `Upstream check` workflow 失敗（`--strict` exit 1＝有未審 commit／PR／issue；exit 2＝檢查本身沒跑成） | 照 [`docs/UPSTREAM.md`](docs/UPSTREAM.md)「審查清冊」逐筆讀 diff，`docs/DECISIONS.md` 記結論，推進 `tools/upstream_baseline.json` 的 `reviewed_through`／`reviewed_pr_through`／`reviewed_issue_through`；下一次 `Upstream check` success | Claude Sonnet | `tools/upstream_baseline.json`（審到 `ae229ca`、PR #1460、issue #1461）；`.github/workflows/upstream-check.yml` |
| `pymupdf` 升 2.x | pymupdf 補齊 macOS x86_64 wheel，或維護者決定不再支援 Intel macOS | `pyproject.toml`、`uv.lock` 改版後 `uv lock --check` 通過；同一份含繁中的 PDF 用 `PyMuPDFLoader` 新舊版輸出相同；刪掉 `.github/dependency-deferrals.json` 的 `pymupdf` 條目 | Codex | [`docs/DECISIONS.md`](docs/DECISIONS.md) 2026-10-28 Dependabot #105–#108；`.github/dependency-deferrals.json` |
| 支援 Python 3.13（magika 移到 ≥ 0.6） | 上游移植 magika，或維護者決定支援 Python 3.13 | `requires-python` 放寬到 `<3.14`；`src/khoj/utils/helpers.py:58,138`、`src/khoj/processor/content/github/github_to_entries.py:18,160` 改用新 API；CI 矩陣加 3.13，Docker smoke 綠 | Claude Opus | [`docs/DECISIONS.md`](docs/DECISIONS.md) 2026-10-28 上游審查（issue #1461）；`pyproject.toml:10`、`:47` |
| 文件站依賴的三個已知例外：`deepmerge`、`picomatch` 的 `>=2.3.2` 覆寫、mermaid 內建舊 katex | `deepmerge` > 4.3.1 或 `@svgr/plugin-svgo` 不再依賴它；文件站建置壞掉或下次動 resolutions；mermaid 升級其 katex | `documentation/` 下 `yarn build` 綠；`grep -c deepmerge documentation/yarn.lock` 為 0 或版本 > 4.3.1；`picomatch` 覆寫改成 `^4` | Codex | [`docs/DECISIONS.md`](docs/DECISIONS.md) 2026-10-28 #367、2026-10-27 深掃「刻意不修」 |

## 刻意不做
| 不做什麼 | 理由 | 什麼情況下重新考慮 |
| --- | --- | --- |
| 發佈本線自己的 PyPI 套件、Docker 映像、文件站、Obsidian／桌面 release | 產品發佈屬上游；發佈 workflow 都閘在 `khoj-ai/khoj`（[`docs/DECISIONS.md`](docs/DECISIONS.md) 2026-08-27「發佈 workflow 加上游 repo 閘門」） | 上游停止維護且本線決定接手發佈 |
| 不經同意回貢上游；把 Windows 維護骨架或文件送回上游 | [`FORK.md`](FORK.md)「回貢判準」：只有修上游 bug 才考慮，且必須在當次對話取得維護者明確同意 | 維護者在當次對話明確同意某一筆修正回貢 |
| 採用上游的新功能或第三方服務整合（#1418、#1419／#1427、#1425、#1435、#1459 SMTP、Emacs 顯示 #1457／#1458）與只影響計費託管的 #1453 | 本線只採用能在本機驗證的缺陷修正，不擴大產品面（[`docs/DECISIONS.md`](docs/DECISIONS.md) 2026-09-30、2026-10-25） | 本線開始對外多人使用或開啟 billing（#1453、#1455）；上游把功能合併進 `master` 後隨同步進來 |
| 用 `resolutions` 硬改版本號讓沒有修補版的 Dependabot 警報消失 | 只會掩蓋問題（[`docs/DECISIONS.md`](docs/DECISIONS.md) 2026-10-26 `http-cache-semantics`） | 出現真正的修補版或可以移除整條依賴鏈 |

## 維護方式
上游：`Upstream check` 每週跑，紅了才依 [`docs/UPSTREAM.md`](docs/UPSTREAM.md) 批次審查；同步時 [`FORK.md`](FORK.md) 列的 overlay 以本線為準。依賴：Dependabot 只開 PR、不自動合併；產品依賴 PR 的 CI 綠燈不代表產品行為沒事，合併前要對產品實際用到的 API 做新舊版對照並寫進 `docs/DECISIONS.md`。每次改動先跑 `pwsh -NoProfile -File tools\dev_check.ps1`。
