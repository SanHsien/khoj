# 路線圖

> 本 repo 後續工作的單一真相源。做完一項，就在同一個 commit 刪掉那一列；新工作只加在這裡。
> 現況段的數字是 2026-10-29 依 `main` `40b788545e92` 查的快照，開工前先重查 GitHub。

## 現況
`khoj-ai/khoj` 的 Windows-first 維護線：產品程式跟隨上游 `ae229ca`，加上 [`FORK.md`](FORK.md) 列的 overlay（Compose 硬化、日誌注入防護、寄信 autoescape 等），本線不發佈套件或映像。2026-10-29 查 `main`：open PR 0、Dependabot open alert 1 筆（low，`deepmerge`，文件站建置期依賴，無修補版）、code scanning 0；CI／CodeQL／Dependency freshness／Upstream check 最近一次 success；issues 已停用，open issue 數「未查到」（查法：`gh api repos/SanHsien/khoj/dependabot/alerts?state=open`、`gh run list -R SanHsien/khoj -b main`）。
卡點：`ci.yml` 只測維護工具，`docker-build-check.yml` 只在映像內 import 套件；`docker-compose-smoke.yml`（手動或 `verify/*` 觸發，驗伺服器啟動與管理員登入）已新增、尚未實跑；沒有 run 連結前，五批上游修正仍卡在「adoption pending」。

## 近期：可以直接動手
| 項目 | 為什麼 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| 加一個會真的啟動伺服器的 Compose smoke workflow（手動或 `verify/*` 觸發，沿用 `docker-build-check.yml` 的觸發方式） | 產品依賴升級、Python 3.10 → 3.11、`ubuntu:noble` 基底與 overlay 目前都只有「能 import」的證據；有了伺服器 smoke，下方 adoption pending 的上游 PR 才有地方驗 | workflow 在 GitHub 上跑 `docker compose up`（Postgres＋server），`GET /api/health` 回 200、能以 Compose 的管理員帳號登入後拿到 200；失敗時 job 紅；run 連結記進 `docs/DECISIONS.md` | Claude Sonnet | `.github/workflows/docker-build-check.yml:30-34`（只 build＋`python3 -c import`）；`src/khoj/routers/api.py:241`（health route）；[`docs/DECISIONS.md`](docs/DECISIONS.md) 2026-10-25「本機沒有 Docker」 |
| 決定 `deepmerge` 警報 #367 維持 open 或以 `tolerable_risk` dismiss | 沒有修補版、只在文件站建置期合併自家 SVGO 設定；維持 open 會讓每次盤點都看到同一筆 | `docs/DECISIONS.md` 2026-10-28 條目補一行最終決定；若 dismiss，`gh api repos/SanHsien/khoj/dependabot/alerts/367` 的 `dismissed_reason` 為 `tolerable_risk` | 維護者 | [`docs/DECISIONS.md`](docs/DECISIONS.md) 2026-10-28「`deepmerge` 警報 #367 延後」 |

## 中期：等條件成立再做
| 項目 | 觸發條件 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| 採用 adoption pending 的上游 PR：#1424（Windows PDF 暫存檔）、#1430（工具選擇 fallback）、#1432（inline HTML）、#1440／#1437（空標題卡住）、#1442／#1439（operator 對話輪次）、#1445（串流收尾）、#1454（研究模式並行工具） | 近期表的伺服器 smoke 已能跑，或上游 `master` 合併其中任一筆 | 每筆讀完整 diff、在 smoke 環境實跑對應路徑（PDF 匯入、聊天、研究模式），`pwsh -NoProfile -File tools\dev_check.ps1` 綠；`docs/DECISIONS.md` 逐筆記採用或不採用 | Claude Sonnet | [`docs/DECISIONS.md`](docs/DECISIONS.md) 2026-09-30「採用待辦」、2026-10-25 上游審查表 |
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
