# 安全政策

## 支援範圍

安全修正以本 fork 的最新 `main` 為主；上游版本的問題也會視需要回報原作者。

## 私下回報

請使用 GitHub Security Advisories 的 **Report a vulnerability**
私下回報：<https://github.com/SanHsien/khoj/security/advisories/new>。
若該入口不可用，請透過 GitHub 個人檔案聯絡維護者，不要先建立公開 Issue。

回報請包含影響範圍、重現步驟、受影響版本與最小必要證據。請勿附上真實 API key、cookie、
帳號，或可識別個人的筆記與聊天內容。

若問題也存在於上游，維護者會視需要轉報 [`khoj-ai/khoj`](https://github.com/khoj-ai/khoj)。不要在公開 Issue 放密鑰或 exploit 細節。

## 特別注意

- Khoj 會索引本機文件。不要把真實筆記、客戶文件或憑證提交進 repo。
- 本 fork 的 `docker-compose.yml` 把 `42110` 綁在 `127.0.0.1`、關掉 `--anonymous-mode`、預設 `KHOJ_TELEMETRY_DISABLE=True`。computer 服務要 `--profile operator` 才會啟動，VNC `5900` 也只綁 loopback。
- 檔裡仍有範例管理員密碼與 `KHOJ_DJANGO_SECRET_KEY=secret`。本機試用可以；把埠改成對區網或網際網路開放前必須換成自己的值。
- Django／Session 的程式 fallback secret 仍是 `!secret`（見 `src/khoj/app/settings.py`）。from-source 未設環境變數時不要當成正式密鑰。
- 把文件丟進雲端模型（OpenAI / Anthropic / Gemini 等）前需另行審查該供應商的資料政策。本機 Ollama 路徑才把推論留在自己的電腦。
- 本 fork 不發佈官方映像或 PyPI 套件；不要把本 repo 的 tag 當成上游發行。
