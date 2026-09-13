# CLAUDE.md

請先完整閱讀並遵守 [`AGENTS.md`](AGENTS.md)。本檔只補充 Claude Code 的最小入口：

- 這是保留上游歷史的 fork；不要移除 `upstream`、原作者或 GNU AGPL v3.0 授權標示。
- 產品程式在 `src/khoj` 與 `src/interface/`，以上游為準，除非 `FORK.md`／`REVIEW.md` 已記錄 fork overlay。
- 提交前跑 `pwsh -NoProfile -File tools\dev_check.ps1`。不要把 gate 改成完整 `uv sync`。
- 筆記、vault、模型權重、`.env` 與 Docker volume 一律不可提交。
- 使用繁體中文，直接交付可驗證結果，避免冗長背景鋪陳。
