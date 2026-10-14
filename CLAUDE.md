# CLAUDE.md：Claude Code 的入口（病理學教案投影片工具組）

@AGENTS.md

上面匯入的 `AGENTS.md` 是所有工具共用的守則正本：環境、讀法、硬規則 1–16、工作流、交件、路徑對照。舊文件寫「CLAUDE.md 第 N 節」「硬規則 N」「CLAUDE.md 規則 N」，指的是它的同一節、同一號（2026-10-14 從本檔搬過去，編號不變）。本檔只放 Claude Code 才用得到的附註。

## Claude Code 附註

- **Workflow 工具怎麼叫**：

  ```text
  Workflow({
    scriptPath: "<kit>/workflows/lecture-write.js",
    args: { kit: "<kit>", materials: "<materials>", course: "<course>", ...該工作流的其他參數..., done: {} }
  })
  ```

  各工作流的參數、代理數、費用見 `workflows/README.md`。沒有 Workflow 工具的環境照 `AGENTS.md` 第 4.0 節與 `docs/跨工具做法.md` 做。
- **effort**：`agent()` 的 `effort` 可設 `'low'`、`'medium'`、`'high'`、`'xhigh'`、`'max'`。沒寫就繼承主 session 當時的 effort（2026-10-14 uro-a3 撰寫第一次開跑就繼承到 medium，停掉、改成明寫後重開）。kit 的六支通用工作流只吃一個 `args.effort` 套到全部代理，叫它們時一定要給（例 `effort: "xhigh"`）；要分角色就照課程自寫腳本的寫法（args `effort` 一般、`effort_hard` 查證；之後的腳本機械性角色用 `effort_light`）；通用工作流只能給一個值時怎麼辦，見 `workflows/README.md`「角色與強度」的「程式現況」。
- **續跑**：本專案續跑一律用 `args.done`（DONE 表）。Claude Code 的 `resumeFromRunId` 只沿用「從頭算起沒有改動的那一段 agent() 呼叫」，換機器、改腳本或 args 就整批重跑，細節見 `workflows/README.md`「續跑」。從前一次 run 重建 DONE 表用 `workflows/tools/done_from_journal.py`，不要手動拼。
- **journal 的位置**：`~/.claude/projects/<專案代號>/<session id>/subagents/workflows/<runId>/journal.jsonl`。每跑完一個工作流，把它與當次 args 複製到 `<materials>/courses/<course>/_archive/journals/`（雲端 VM 回收後就不見了）。
- **開跑前的固定步驟**（`docs/多session做法.md` 第 5 步）裡的「壓縮對話」＝請教師下 `/compact`；「附目前用量」＝附 `/usage` 的結果（`/usage` 只統計這台電腦上的 session）。
- **ultracode**：教師要多代理、高強度的做法時說的詞。2026-10-14 實測：他說「開 ultracode」之後，主 session 的 effort 從 medium 變成 xhigh；工作流裡的代理仍要逐一明寫 effort。本專案「ultracode 等級」的結構見 `docs/多session做法.md`「四個階段」。
- **plan mode**：在 plan mode 由主 session 派的 Explore、Plan 輔助子代理不算工作流；階段 0「不開工作流」指的是不跑 `workflows/*.js` 這類腳本（uro-a3 的階段 0 用了 4 個輔助子代理）。
- **判斷雲端**：`echo "remote=$CLAUDE_CODE_REMOTE"`，雲端 session 是 `true`。雲端 session 的開法、費用與陷阱見 `docs/cloud_session_教學.md`。
- **寫大檔**：在 Windows 的 Bash 工具裡，約 100 行以上的 heredoc 會被截斷、反斜線會被改寫；先用 Write 工具寫成檔再執行。
- **記憶**：本機記憶（`~/.claude/projects/<專案代號>/memory/`）在雲端與其他工具都看不到，放摘要、repo 不能放的原話（例：含舊模型名的教師原話）與指向；規則與裁決寫進 repo（`AGENTS.md` 開頭）。兩邊不一致時以 repo 為準。
- 其他工具的對應指令（`/compact`、`/usage`、`/add-dir`、`/memory`）見 `docs/跨工具做法.md` 第 5 節。
