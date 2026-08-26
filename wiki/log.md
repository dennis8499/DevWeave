---
title: Wiki Activity Log
type: log
sources: []
last_updated: 2026-08-26
tags: [log]
status: active
source_fingerprint: none
verified_by: 20260825-163914-feature-devweave-v2-app-server-harness
---

# Activity Log

> Append-only chronological record。不得刪除或重寫既有 body。

## [2026-08-02] init | Wiki skeleton installed

- 建立 index、overview placeholder、log 與 typed directories。

## [2026-08-03] promote | 20260803-161041-feature-codebase-llm-wiki

- 將 [[overview]] 提升為 active source-bound 專案概觀。
- 新增 [[devweave-knowledge-workflow]]，記錄 Bootstrap→Query→Review→Promotion 生命週期。
- 新增 [[knowledge-engine]]，記錄 machine commands、state、coverage、scaffold 與 seal 邊界。

## [2026-08-03] promote | 20260803-215202-feature-devweave-control-center-ux

- Refresh [[overview]] 與 [[knowledge-engine]]，補充 Control Center presentation boundary、public prompt handoff、workspaceState preference、active/closed work 分組與 bounded Wiki browsing。

## [2026-08-04] promote | 20260804-085630-feature-g1-g2

- Refresh [[overview]]、[[devweave-knowledge-workflow]] 與 [[knowledge-engine]]，記錄 G1/G2 關鍵決策逐題問答、Companion Skill 階段邊界、Gate Double Check、explicit approval 與 `revise` 回流規則。

## [2026-08-04] promote | 20260804-102428-feature-vs-code-extension-wiki

- Refresh [[overview]]、[[devweave-knowledge-workflow]] 與 [[knowledge-engine]]，補充 VS Code Control Center 的 projection、Wiki-first/G3 邊界與 Extension integration。
- 新增 [[vscode-extension]]，記錄 Enter 套用的 case-insensitive contains 搜尋、局部 render、single-flight refresh、deterministic snapshot、0.2.0 bootstrap repair、embedded help 與安全邊界。

## [2026-08-04] promote | 20260804-122803-feature-g3-review-agent

- Refresh [[overview]] 與 [[devweave-knowledge-workflow]]，記錄 high-risk G3 exactly-one isolated read-only Independent Review、G2 design-agent 分離、critical finding gate 與 human approval boundary。
- Refresh [[knowledge-engine]]，記錄 machine-only `review record`、bounded/redacted report provenance、source fingerprint stale invalidation 與 named `review-critical` waiver。
- Refresh [[vscode-extension]]，記錄 high-risk acceptance readiness、missing/unavailable/advisory attention、critical not-ready 與 raw review evidence projection；Extension 不啟動 Agent 或 mutation。

## [2026-08-04] promote | 20260804-183511-feature-g1-g2-wiki-extension-bundle

- Refresh [[overview]]、[[devweave-knowledge-workflow]] 與 [[knowledge-engine]]，記錄 native-first G1/G2 structured decision interface、Wiki reserved-starter preflight/order、custom-only compatibility 與 ordinary bootstrap advisory boundary。
- Refresh [[vscode-extension]]，記錄七個 data-contract semantic adoption kinds、shared installer/snapshot validator、exact controls、missing-only writes 與 fail-closed conflict behavior。

## [2026-08-04] promote | 20260804-205655-feature-devweave-0-2-1-windows

- Refresh [[overview]]、[[devweave-knowledge-workflow]]、[[knowledge-engine]] 與 [[vscode-extension]]，記錄 0.2.1 Windows VSIX 支援邊界與 rollback artifact、PreviewGate 的 panel/intent/revision copy enforcement、Refresh stale invalidation、legacy `copyNextAction`/multi-work semantics、Wiki `#wiki-results` DOM mount、五區 tab/tabpanel accessibility 與繁中 handoff。
- 追加 release hardening：`wikiBootstrap` 統一進入 host preview route，五個 inactive tabpanel 保持可指向的 ARIA target，並以 current-source bounded walkthrough/accessibility output 與固定舊版 VSIX hash 驗證 G3 release bar。
- 再同步 review hardening：Control Center 明確為五區，copy success notification 不會 restore 已 consumed ticket，EVID-035/EVID-038 raw logs 保存 accessibility 與 Python/Extension walkthrough markers。
- 再同步 critical-review hardening：`status --all` 明確承接未選定 work 的全量查詢，PreviewGate 改用 typed intent 欄位比較並拒絕危險控制字元，錯誤 primary status 改為繁中且保留可展開 technical detail；EVID-046～EVID-048 保存 current 73-test、package、smoke、typecheck 與 Python verification provenance。

## [2026-08-05] promote | 20260805-081842-feature-skills-writing-great-skills

- Refresh [[overview]]、[[devweave-knowledge-workflow]] 與 [[knowledge-engine]]，記錄五個 companion Skill 的 local predictability overlay、唯一 router/phase boundary、G1/G2 decision return、G2 前 bug repro 與 TDD public-seam 規則。
- 固定 `writing-great-skills` 為 maintenance-only exclusion；`skills-lock.json` 的五筆 upstream source/path/hash 與 Extension bootstrap 六組受治理 Skill set 維持不變。
- 補記 frontmatter/metadata/invocation contract、UTF-8 quick validation、isolated forward-test、repository contract 與 Python/Extension verification evidence。

## [2026-08-05] promote | 20260805-094544-feature-plan-first

- Refresh [[overview]]、[[devweave-knowledge-workflow]] 與 [[knowledge-engine]]，將 Plan Mode 定為 G1/G2/Gate material decision 的正式 native 入口，canonical host tool 固定為 `request_user_input`。
- 記錄一題／二至三選項／推薦第一項 `(Recommended)`／host `Other`、等待 answer、普通 pre-G2 回到 Plan Mode、明確 compatibility structured fallback、G2 後 approved-task boundary 與新決策 `revise` 回流。
- 記錄 ordinary/Skill native tool visibility 是外部 host capability；不新增 engine question state、CLI、ledger、fake adapter 或 Extension 問答 UI，並保留 cancel/timeout/malformed 的 no-guess/no-mutation safety。

## [2026-08-05] promote | 20260805-104700-bug-windows-codex-pretooluse-hook

- Refresh [[overview]]、[[devweave-knowledge-workflow]]、[[knowledge-engine]] 與 [[vscode-extension]]，記錄 Windows Codex runner 以標準 `command` 經 `cmd.exe` 啟動 PowerShell／`python -B` guard 的 bootstrap contract。
- 提升 process failure 與 DevWeave policy `permissionDecision: deny` 的分層語意、`commandWindows` 移除、source-derived 0.2.1 embedded hook verifier，以及既有 exact workspace hook 需使用者確認、不由 Extension 靜默覆寫的邊界；0.1.0／0.2.0 rollback artifacts 保持不變。

## [2026-08-05] promote | 20260805-120943-feature-devweave-0-2-1-current-version-only-rele

- Refresh [[overview]]、[[devweave-knowledge-workflow]]、[[knowledge-engine]] 與 [[vscode-extension]]，將 0.2.1 release contract 統一為 current-version-only，並限定本次 Windows x64／VS Code／Python／Git／Codex 認證環境。
- 記錄 98 項 Python suite、73 項 Extension tests、58 個 bootstrap files、118 個 VSIX entries、current artifact SHA-256 與無舊版 binary rollback 的資料保留事故處理。

## [2026-08-05] promote | 20260805-150125-bug-codex-cli-pretooluse-hook-powershell-utf

- Refresh [[overview]]、[[devweave-knowledge-workflow]]、[[knowledge-engine]] 與 [[vscode-extension]]，記錄 Windows Codex hook 的 shell-neutral Git-root launcher、`powershell.exe -NoLogo -NoProfile -NonInteractive`、`python.exe -X utf8 -B` 與 no-`commandWindows` contract。
- 提升 guard 直接以 UTF-8 bytes 讀寫 hook JSON、policy deny 維持 process exit 0、PowerShell/cmd runner compatibility、nested cwd、malformed input 與 read-only silence 的 process-level regression；source-derived 0.2.1 package verifier 同步檢查相同語意。
- 本 Work Item 新增四項 hook regression，Python final run 為 102 tests；Extension tests 73、bootstrap files 58、VSIX entries 118 維持既有 release contract。

## [2026-08-05] promote | 20260805-184040-feature-plan-mode

- Refresh [[overview]]、[[devweave-knowledge-workflow]]、[[knowledge-engine]] 與 [[vscode-extension]]，記錄所有 pre-G2 mutation entry 的 Plan Mode preflight、未具 host capability 時在 Work Item mutation 前停止，以及僅明確 compatibility 才使用 structured fallback。
- 提升 `PlanModeGuidance` optional metadata、`chatText` 相容性、Control Center overview/preview/copy 的 Plan Mode handoff 與 Extension 不提供 host mode adapter 的邊界。
- 同步 0.2.2 current package、58 個 bootstrap files、119 個 VSIX entries 與保留 0.2.1 artifact。

## [2026-08-10] promote | 20260810-130022-feature-openai-hooks-windows-shell-pretooluse

- Refresh [[overview]]、[[devweave-knowledge-workflow]]、[[knowledge-engine]] 與 [[vscode-extension]]，記錄 exact `PreToolUse` matcher、POSIX `command`/Windows `commandWindows` dual path、`py -3 -X utf8 -B` Git-root launcher 與 CMD/PowerShell 5.1/PowerShell 7/VS Code terminal matrix。
- 記錄 `doctor` prerequisite/schema/root-nested probe、launcher failure 與 policy deny 的分層診斷、source-derived root/embedded hook verification、0.2.3 current VSIX（58 bootstrap files／119 entries）與保留 0.2.2/0.2.1 artifact。
- 以 Python 101 tests（1 項因 symlink 權限 skipped）、Extension 77 tests、package/typecheck/smoke 與 repository contract evidence 固定本次驗證邊界；hook 是 Codex guardrail，不是 OS sandbox，hosted/global/plugin-owned paths 不在覆蓋範圍。

## [2026-08-10] refresh | 20260810-130022-feature-openai-hooks-windows-shell-pretooluse

- Refresh [[overview]]、[[devweave-knowledge-workflow]]、[[knowledge-engine]] 與 [[vscode-extension]]，補記 Windows handler 先設定 .NET console input/output 為 UTF-8、避免 shell-scoped encoding variable、以及最後一輪 source-derived hook/package contract。
- 維持四頁 content upsert 與 index/log coupling；本次只更新已規劃的 Wiki targets，既有 activity log body 保持 append-only。

## [2026-08-13] promote | 20260813-142228-feature-devweave-vs-code-extension

- Refresh [[overview]]、[[devweave-knowledge-workflow]]、[[knowledge-engine]] 與 [[vscode-extension]]，補記 summary-first Work Item projection、bounded Wiki provenance、projection-only engine authority 與 affected-path verification。
- 記錄 command metadata、release-only dependency exclusion、high full-set policy、bounded evidence metrics 與 Codex usage unavailable 語意；build provenance 與 cache-only VS Code 1.131.0 smoke contract 維持 source-bound。
- 將 0.2.3 package provenance 固定為 candidate → verify → atomic promotion；verification 或 promotion failure 保留 current artifact 並清理 candidate，Extension final run 更新為 88 tests。
- 將 metrics contract 的 250,000-byte payload／10,000,000 numeric bounds 與 usage unavailable/null semantics 同步到 engine、Extension 與驗證投影。

## [2026-08-16] promote | 20260814-233520-bug-guard-policy-engine-v2-side-effect-comma

- Refresh [[overview]]、[[devweave-knowledge-workflow]] 與 [[knowledge-engine]]，同步 Verification Policy v2 的 shared evaluator、G2 frozen Effective Verification Plan、digest-bound evidence eligibility、controlled executor 與 G3 plan parity。
- 新增 [[command-policy-engine]]，記錄 typed read-only grammar、trusted executable/cwd、writer barrier、temporary candidate、undeclared-write failure 與 policy mutation stale boundary。
- 本批 Wiki 內容由四個 planned upsert 與 coupled index/log 更新組成；既有 log body 保持 append-only，完成後由 Router seal current source fingerprints。

## [2026-08-26] promote | 20260825-163914-feature-devweave-v2-app-server-harness

- 刪除 [[overview]]、[[devweave-knowledge-workflow]]、[[command-policy-engine]]、[[knowledge-engine]] 與 [[vscode-extension]] 五個 legacy 內容頁；它們描述的 clipboard、Wiki runtime、legacy verifier 與 0.2.3 Extension authority 已由 V2 clean cutover取代。
- V2 durable knowledge 只保留在 root `ARCHITECTURE.md` 與 indexed `docs/` tree；本 index/log 只記錄本次 legacy G3 的受治理刪除，hash-bound finalizer 會移除剩餘 Wiki starter tree。
