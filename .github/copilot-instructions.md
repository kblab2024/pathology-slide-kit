# GitHub Copilot 的指引

本 repo 的守則正本是根目錄的 `AGENTS.md`（所有工具共用）。動手前先讀它，再照它第 2 節的讀法讀其他檔；本檔不另寫規則。

- Copilot 沒有 Claude Code 的 Workflow 工具：多代理的步驟照 `AGENTS.md` 第 4.0 節與 `docs/跨工具做法.md` 做，強度照第 4.0 節的對照表。
- 文字檔一律 UTF-8、LF；commit 前跑 `cd scripts && PYTHONIOENCODING=utf-8 python check_public.py`，FAIL 要是 0；它印出找不到 `pseudonyms.tsv`、第三人真名未檢查時，表示只查了一半（硬規則 12），PR 說明寫明，等維護者在兩個 repo 都在的環境再跑一次才合併。
- Copilot coding agent 在雲端只看得到本 repo：只改程式與文件，不做課（`AGENTS.md` 第 1 節）。
