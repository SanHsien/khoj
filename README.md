<p align="center"><img src="https://assets.khoj.dev/khoj-logo-sideways-1200x540.png" width="230" alt="Khoj Logo"></p>

<p align="center">
  <a href="README.md"><strong>繁體中文</strong></a> ·
  <a href="README.en.md">English</a>
</p>

<div align="center">

[![ci](https://github.com/SanHsien/khoj/actions/workflows/ci.yml/badge.svg)](https://github.com/SanHsien/khoj/actions/workflows/ci.yml)
[![test](https://github.com/khoj-ai/khoj/actions/workflows/test.yml/badge.svg)](https://github.com/khoj-ai/khoj/actions/workflows/test.yml)
[![docker](https://github.com/khoj-ai/khoj/actions/workflows/dockerize.yml/badge.svg)](https://github.com/khoj-ai/khoj/pkgs/container/khoj)
[![pypi](https://github.com/khoj-ai/khoj/actions/workflows/pypi.yml/badge.svg)](https://pypi.org/project/khoj/)
[![discord](https://img.shields.io/discord/1112065956647284756?style=plastic&label=discord)](https://discord.gg/BDgyabRM6e)

</div>

> **這是 [`khoj-ai/khoj`](https://github.com/khoj-ai/khoj) 的 Windows-first 維護型 fork**，沿用 GNU AGPL v3.0 與完整 Git 歷史。產品行為跟隨上游；本維護線補上繁中入口、Windows 開發／驗收 gate，以及逐筆審查的上游追蹤。差異見 [`FORK.md`](FORK.md)，同步策略見 [`docs/UPSTREAM.md`](docs/UPSTREAM.md)。官方 Docker 映像與 PyPI 套件仍以上游為準。本 fork 不發佈到 PyPI、GHCR、docs.khoj.dev 或 Obsidian 外掛商店。

<div align="center">
<b>開源、可自託管的個人 AI 第二大腦</b>
</div>

<br />

<div align="center">

[📑 文件](https://docs.khoj.dev)
<span>&nbsp;&nbsp;•&nbsp;&nbsp;</span>
[🌐 官網](https://khoj.dev)
<span>&nbsp;&nbsp;•&nbsp;&nbsp;</span>
[🔥 雲端試用](https://app.khoj.dev)
<span>&nbsp;&nbsp;•&nbsp;&nbsp;</span>
[💬 Discord](https://discord.gg/BDgyabRM6e)
<span>&nbsp;&nbsp;•&nbsp;&nbsp;</span>
[✍ 部落格](https://blog.khoj.dev)

</div>

***

Khoj 直接讀取本機文件與筆記，可在斷網環境用 Ollama 等開源模型對話，敏感資料留在自己的電腦。也支援切換雲端模型，並提供網頁、桌面端與 Obsidian 外掛。

- 對話可用本機或線上 LLM（例如 Llama、Qwen、Gemma、Mistral、GPT、Claude、Gemini、DeepSeek）。
- 從本機文件找答案：Markdown、PDF、Word、org-mode、圖片、Notion 等。
- 從瀏覽器、Obsidian、Emacs、桌面、手機或 WhatsApp 使用。
- 自訂 Agent：知識庫、人設、模型與工具。
- 語意搜尋、排程研究、圖片生成與語音。
- 永遠開源、可自託管。隱私優先時走本機；也可以用上游的[雲端服務](https://app.khoj.dev)。

產品使用方式以上游文件為準：<https://docs.khoj.dev>。

## 本機自託管（Windows，建議 Docker）

需要已安裝 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。

```powershell
git clone https://github.com/SanHsien/khoj.git
cd khoj
docker compose up -d
```

預設網頁在 <http://127.0.0.1:42110>。連本機 Ollama 時，在 `docker-compose.yml` 的 `server` 服務取消註解：

```yaml
- OPENAI_BASE_URL=http://host.docker.internal:11434/v1/
- KHOJ_DEFAULT_CHAT_MODEL=qwen3
```

並把 `KHOJ_ADMIN_EMAIL` / `KHOJ_ADMIN_PASSWORD` / `KHOJ_DJANGO_SECRET_KEY` 改成自己的值。本 fork 的 Compose 把 `42110` 綁在 `127.0.0.1`、關掉 `--anonymous-mode`、預設 `KHOJ_TELEMETRY_DISABLE=True`。computer／VNC 服務要 `docker compose --profile operator up` 才會起來。若要把埠對區網或網際網路開放，先改密鑰再改 port mapping。

完整選項見上游 [Self-Host 文件](https://docs.khoj.dev/get-started/setup) 與 [`docker-compose.yml`](docker-compose.yml)。

## 開發這個 fork

```powershell
git clone https://github.com/SanHsien/khoj.git
cd khoj
pwsh -NoProfile -File tools\bootstrap_dev.ps1
```

這只安裝維護工具並跑 Windows gate，**不會**裝 torch / Django 等產品依賴。要從原始碼跑 Khoj 伺服器，見 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)。Agent 維護規則見 [`AGENTS.md`](AGENTS.md)。

## 授權

GNU Affero General Public License v3.0。若你修改本專案並以網路服務提供，必須向使用者提供對應原始碼。聲明見 [`NOTICE.md`](NOTICE.md) 與 [`LICENSE`](LICENSE)。

## 貢獻

產品行為的修正，優先考慮回報 [`khoj-ai/khoj`](https://github.com/khoj-ai/khoj)。本 fork 的文件與 Windows 骨架見 [`CONTRIBUTING.md`](CONTRIBUTING.md)。安全問題走 GitHub Advisory，不要開公開 Issue。
