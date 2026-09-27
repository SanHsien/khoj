# NOTICE

khoj (SanHsien maintenance fork)
Copyright 2026 SanHsien

This project is derived from [`khoj-ai/khoj`](https://github.com/khoj-ai/khoj), originally licensed under the GNU Affero General Public License v3.0.

Original work:

- Project: `khoj`
- Authors: Debanjum Singh Solanky, Saba Imran, and Khoj contributors
- License: GNU AGPL v3.0
- Upstream: https://github.com/khoj-ai/khoj
- Homepage: https://khoj.dev

This repository keeps the original AGPL-3.0 license text in [`LICENSE`](LICENSE). Modifications, documentation, and future project-specific changes in this fork are also licensed under GNU AGPL v3.0 unless otherwise noted.

## License Notes

GNU AGPL v3.0 is a copyleft license. If you modify this project and run it as a network service, you must provide the corresponding source to users of that service. When redistributing this project or substantial parts of it:

- Keep [`LICENSE`](LICENSE) with the original AGPL-3.0 text.
- Keep attribution to `khoj-ai/khoj`.
- License your modifications under AGPL-3.0.
- Add separate attribution for new third-party libraries when their licenses require it.

This fork does not grant additional permissions beyond AGPL-3.0.

## Project Scope

This repository ships a self-hostable personal AI knowledge base. It does not include user notes, PDFs, Obsidian vaults, model weights, API keys, or Docker volume data. Generated indexes, chat logs, and `~/.khoj/` state belong to the user and must not be committed.

Official container images (`ghcr.io/khoj-ai/khoj`), PyPI package `khoj`, and https://docs.khoj.dev are published by the upstream project, not by this fork.

## Credits

`khoj` is a fork of `khoj-ai/khoj` (GNU AGPL v3.0). The server, clients, RAG pipeline, and Docker setup belong to the upstream project.

This project is not affiliated with, endorsed by, or sponsored by Khoj Inc., OpenAI, Anthropic, Google, Meta, Obsidian, Ollama, or any model vendor mentioned in examples.

Do not commit secrets, personal notes, vaults, or model weights.
