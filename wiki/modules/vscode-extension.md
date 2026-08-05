---
title: DevWeave VS Code Extension
type: module
sources: [.codex/hooks.json, vscode-extension/esbuild.mjs, vscode-extension/package.json, vscode-extension/scripts, vscode-extension/src]
last_updated: 2026-08-05
tags: [module, vscode, control-center]
status: active
source_fingerprint: "sha256:5e7023ce0927414252c31e9d3658432260cb762b131f86a2f07316206be3273c"
verified_by: 20260805-184040-feature-plan-mode
---

# DevWeave VS Code Extension

## Responsibility

`devweave-control-center` 是 DevWeave 0.2.2 Windows 公開版的唯讀 Control Center，本次提供 `devweave-control-center-0.2.2.vsix` 並保留 `devweave-control-center-0.2.1.vsix`。認證環境限定為 Windows x64 build 10.0.26200／25H2、VS Code 1.131.0、Python 3.14.6、Git 2.51.0.windows.1 與目前 Codex host；VS Code 1.90+／Python 3.11+ 是技術門檻，不代表其他組合已完成本次認證。Extension host 將 project、Work Item、Wiki、evidence、diagnostics 與 bootstrap completeness 投影給 Webview；workflow decision 仍以 prompt handoff 回到 Codex Chat，Extension 不執行 DevWeave engine、CLI、shell、Git 或 network。

## Webview interaction

- Knowledge 搜尋由 `WikiSearchModel` 保存 `draftQuery` 與 `appliedQuery`。輸入期間只更新 draft，因此 input DOM、focus、selection 與字元順序穩定；按 Enter 才套用查詢。
- 套用後以大小寫不敏感的 `includes` 搜尋 title、path 與 body preview；拼字錯誤不保證命中。type 是精確分類篩選，show-all 只控制可見頁數。
- 結果與 metrics 真實 mount 到 `#wiki-results`，`RenderScheduler` 合併連續 local updates；搜尋不重建整個 Knowledge section，也不觸發 workspace scan。
- 五個 section tab/tabpanel 具 `aria-controls`、`aria-labelledby`、selected/tabindex 語意，支援方向鍵、Home/End 與 focus restore；主要 CTA、native modal action、error 與 readiness status 使用繁體中文，技術 command 名稱保留於 code label。
- `dashboard-sections.ts` 提供純的 tab order 與 panel state contract；五個 panel 即使 inactive 也保留穩定 `tabpanel-*` target 並以 `hidden`/`aria-hidden` 表示，避免未選取 tab 的 `aria-controls` 懸空。release test 實際檢查方向鍵/Home/End、roving tabindex、focus restore key 與 forced-colors boundary。
- Help 是 Extension-local 的 lazy section，內容包含初始化、workflow/Gate、Windows VSIX 安裝、Preview/Refresh、Wiki、multi-work、companion skills 與安全邊界；不寫入 target workspace，也不依賴網路。
- `PreviewGate` 將 copy ticket 綁定 panel、typed intent、bundle 與 snapshot revision；Refresh、selection、初始化或 snapshot 更新會使舊 preview stale，clipboard failure 只允許同一 ticket 安全 retry 一次。
- No-active 與 pre-G2 overview 會顯示 Plan Mode 下一步；mutation preview 與 copied result 在 `PlanModeGuidance.required` 時顯示「先切換 Plan Mode，再貼到 Codex Chat」。這是 optional `SnapshotGuidance`／`PromptBundle` metadata，`chatText` 維持原本的 `$devweave ...` 內容，copy 仍可用；Extension 不讀取或切換 host mode。
- PreviewGate 以 discriminated-union 欄位逐欄比較 typed intent，不用 NUL 或其他 delimiter 組 key；protocol 拒絕危險控制字元，避免不同 intent 因分隔符碰撞而通過 copy gate。
- Clipboard callback 成功後，`copyResult` 與 native success toast 走獨立 notification path；只有 clipboard callback 失敗才 restore ticket，避免 notification transport 失敗造成重複 copy。
- 多 active work 時 `next` 必須先選定 work；未選定 work 的 `status` 產生 `$devweave status --all`，讓 engine 明確回報全部 active work；錯誤 primary status 使用繁中，原始 technical detail 以可展開區呈現。
- Verification projection 對 high-risk acceptance 增加 `Independent Review` readiness：current passed 是 ready，missing/unavailable/advisory 是 attention，critical finding 是 not-ready；raw evidence 展開區顯示 result、severity、reviewer、report hash 與 findings。

## Refresh and snapshot

Workspace watcher 保留自動 refresh，事件經 250ms debounce 後交給 `RefreshCoordinator`。Coordinator 只允許一個 read in flight，burst 中只保留最新 pending request；成功 publish 的 snapshot 不會被較舊結果覆蓋。`WorkspaceSnapshotReader` 對獨立的 project、Wiki、Work Item artifacts、evidence 與 events 讀取平行化，最後依固定 path/id 排序合併 diagnostics 與 projection。

手動 Refresh 與 watcher/snapshot revision 共用同一個 stale boundary：既有 preview/result 不可跨 revision 複製。Codex Chat 操作完成後，使用者回到 Control Center Refresh，重新讀取 filesystem snapshot 並再次預覽下一個 prompt。

## Bootstrap contract

Production bundle `0.2.2` 使用由 package version 產生的 manifest，固定完整控制套件：`devweave`、`codebase-design`、`diagnosing-bugs`、`grill-me`、`grilling`、`tdd` 六組 skills，加上通用 `AGENTS.md`、`skills-lock.json`、hook、project、baseline 與 Wiki starter。README、docs、產品 source、tests、fixtures、work item 與 history 不會成為 target workspace 的 bootstrap files；使用手冊只留在 Extension help。Project、三份 baseline 與三份 Wiki starter 明確宣告 `adopt-compatible` contract，其餘 controls 宣告 `exact`。

Windows Codex 的 PreToolUse hook 是由根目錄 `.codex/hooks.json` 產生的 exact bootstrap control：標準 `command` 使用 `powershell.exe -NoLogo -NoProfile -NonInteractive -Command`，由 Codex 的 `cmd.exe` 或 PowerShell 外層啟動，再從 Git root 以 `python.exe -X utf8 -B` 找到並執行 `guard.py`；guard 直接以 UTF-8 bytes 讀寫 JSON，不再維護不會被 Codex runner 採用的 `commandWindows` 欄位。`cmd.exe /d /s /c`、PowerShell outer runner、nested cwd、raw UTF-8、malformed input 與 read-only silence 均由 process-level contract 驗證，policy deny 仍以合法 JSON 與 process exit 0 回傳。

`BootstrapInstaller.inspect()` 先驗證 manifest path、byte length 與 SHA-256，再依 `bootstrap-compat.ts` shared validator 檢查 semantic identity。合法 evolved project/baseline/Wiki bytes 會 adopted；AGENTS、skills、hook、lock 與其他 controls 仍以 exact bytes 判定。初始化或修復只建立 missing paths，不同或不合法內容永不覆寫並列為 conflict；只要仍有 missing 或 conflict，report 與 Dashboard 就標示 partial；若中途寫入失敗，僅 rollback 本輪新增內容，既有檔案保持不變。重跑完整 bundle 是 idempotent。

Hook 的 source-derived consistency 由 package verifier 檢查根目錄 hook 與 `dist/bootstrap/hooks.json` 的 PowerShell／explicit UTF-8／`python -B`／Git-root／no-`commandWindows` semantic contract；0.2.2 VSIX 從 current source 重新產出，其他 VSIX（包含保留的 0.2.1 artifact）不屬於 current package 驗收輸入。

## Security and compatibility

Runtime 維持 CSP、no process、no shell、no external network 與 preview-first public command boundary。所有 workspace write 都集中在使用者確認後的 allowlisted bootstrap installer；snapshot、搜尋、help、prompt composition 與 Independent Review readiness 都是 Extension-local/read-only。Extension 不啟動 Review Agent、不呼叫 Python engine、不判定或核准 gate，也不提供 host mode adapter 或切換命令；事故時停止散布並停用或解除安裝 0.2.2，不自動刪除 `.devweave`、Wiki 或 workspace 資料，修復以新版本發布。Public commands 與 legacy snapshot projection 維持相容；`devweave.copyNextAction` 僅開啟 Control Center，單一 active work 才能自動顯示 next preview，多 work 必須先明確選取。

## Verification seams

`WikiSearchModel`、`RenderScheduler`、`RefreshCoordinator`、`PreviewGate`、Wiki result mount adapter、instrumented snapshot reader、`dashboard-sections.ts`、copy transaction boundary、`bootstrap-compat.ts` 與 `BootstrapInstaller.inspect()` 是不依賴 VS Code UI 的測試 seams。package verifier 只讀取 current 0.2.2 VSIX，檢查 manifest 每個 entry 的 destination、byte length、SHA-256、policy/kind、package／bundle version、58 個 bootstrap files、119 個 VSIX entries、required entries 與 current artifact SHA-256；77 項 Extension tests、typecheck 與 smoke test 再確認 host 可載入 bundle，既有 0.2.1 artifact 保留。Configured full-suite raw logs 另保留 Windows walkthrough 與 accessibility marker。
