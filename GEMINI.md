# GEMINI.md：Gemini CLI 的入口

@./AGENTS.md

上面匯入的 `AGENTS.md` 是所有工具共用的守則正本，本檔不另寫規則。

- Gemini CLI 沒有 Claude Code 的 Workflow 工具：多代理的步驟照 `AGENTS.md` 第 4.0 節與 `docs/跨工具做法.md` 做；強度的對照與在哪裡設也在那兩處。
- 用 `/memory show` 確認 `AGENTS.md` 有載入；改了檔用 `/memory refresh` 重新載入。
- 也可以在 Gemini CLI 的 `settings.json` 設 `"context": {"fileName": ["AGENTS.md"]}` 直接讀 `AGENTS.md`；這時不要再列 `GEMINI.md`，否則同一份會載入兩次。
