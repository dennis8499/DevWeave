# 系統設計：修正 Windows Codex PreToolUse Hook 失敗

<!-- DEVWEAVE:artifact=design version=1 work=20260805-104700-bug-windows-codex-pretooluse-hook -->

## 設計摘要

Hook launcher 是本次修改的 Module 與 Seam；它將 Codex 的 Windows command runner 接到既有 `guard.py` Module。Interface 維持不變：stdin 接收 Codex PreToolUse JSON，stdout 可輸出 `hookSpecificOutput` JSON，正常 policy allow/deny 的 process exit code 都是 0。選定以 PowerShell 作為 Windows Adapter，讓標準 `command` 可被 Codex 的 `cmd.exe /C` 啟動；`guard.py` 繼續承擔 DevWeave work binding、gate、scope 與 Wiki write policy。

此設計的 Depth 來自既有 guard：呼叫端只需遵守 JSON/exit contract，複雜的 repository、session、scope 與 phase 判定留在 guard 內。launcher Adapter 保持薄，提升修改 Locality；不新增第二個 guard、state machine、JSON schema 或 platform fallback。

## 選項比較

### Option A：Windows-first PowerShell canonical command（選定）

- 將 `.codex/hooks.json` 的標準 `command` 改為 `powershell -NoProfile -Command ...`，由 Git root 定位 `guard.py`；移除 `commandWindows`。
- 優點：符合目前 0.2.1 正式 Windows 支援範圍；能直接通過 Codex 的 `cmd.exe /C`；修改面小，能以 process-level test 覆蓋真實啟動鏈。
- 代價：不承諾 Unix/WSL 執行；若未來擴大平台，需另建明確的 launcher 設計。

### Option B：跨平台 launcher

- 新增跨 shell 的啟動層或依賴 repository-root working directory 的相對 Python 命令。
- 不選定：超出目前 Windows-only release scope，增加 bootstrap、launcher、跨平台 shell quoting 與測試維護面，不能改善本次已知問題的必要部分。

### Option C：保留 `commandWindows` 作為 platform override

- 不選定：目前 Codex runner 的 command interface 使用標準 `command`，不能把未被採用的欄位當作可靠 adapter；保留它會掩蓋 canonical command 仍然錯誤的問題。

## 介面與資料流

1. Codex 觸發 `PreToolUse`，將 JSON payload pipe 到 hook process stdin。
2. Windows runner 以 `cmd.exe /d /s /c` 執行標準 `command`。
3. PowerShell 執行 `git rev-parse --show-toplevel`，使用 `Join-Path` 定位 `.agents\\skills\\devweave\\scripts\\guard.py`，再以 `python -B` 啟動它。
4. `guard.py` 讀取 stdin、以 payload `cwd` 尋找 repository，執行既有 policy；allow 沒有 stdout，deny 輸出 `hookSpecificOutput.permissionDecision = deny`，兩者 process exit code 都為 0。
5. `esbuild.mjs` 既有 source-derived copy 將同一份根目錄 hook 放入 `dist/bootstrap/hooks.json`；package verifier 檢查 manifest/hash/VSIX entry。

不新增 public API、CLI command、type 或 ledger schema。`commandWindows` 從 hook wire configuration 移除；Codex stdin/stdout 與 guard decision interface 不變。

## 失敗模式與回復

- Git root 定位失敗、Python 不存在或 script path 不可讀：PowerShell/launcher 以非零狀態結束，Codex 仍顯示 process failure；不以未受控方式放行寫入，也不改 guard fail-closed policy。
- Guard policy 拒絕：`guard.py` 輸出合法 deny JSON 並以 0 結束；這與 launcher failure 在測試與手冊中明確區分。
- Bootstrap package build 失敗：不接受新 VSIX；既有 0.1.0／0.2.0 artifact 不覆寫。
- Rollback：以版本控制回復 `.codex/hooks.json`、測試、手冊與 verifier，重新 package 產出上一個 0.2.1 artifact；既有 target workspace 不由 Extension 自動覆寫 exact hook。

觀測方式包括 cmd.exe process smoke、deny JSON assertion、repository contract test、package verifier、Codex UI manual acceptance 與 G3 完整 diff/evidence reconciliation；`statusMessage` 保持 `Checking DevWeave gates`。

## 高風險分析

- Migration：不涉及 state、資料庫、schema、CLI 或使用者資料 migration；只更新 source-derived hook control 與 release artifact。
- Security：維持既有 guard policy；測試必須確認未綁定 Write 仍 deny，且 launcher failure 不被當成 allow。`python -B` 避免 hook 啟動時新增 bytecode cache。
- Compatibility：正式 acceptance 只涵蓋 native Windows 0.2.1；legacy VSIX hash/bytes 固定；exact bootstrap conflict/no-overwrite 行為維持。
- Performance：新增／保留一次 PowerShell process，沒有額外 network、persistent process 或 repository scan；以 bounded process smoke 與完整 suite 驗證可接受延遲。
- Rollback：保留 0.1.0／0.2.0 回退 artifact，並可從 source diff 反向回復 canonical command。

## 設計決策

## DEC-001: 使用 Windows PowerShell 作為 canonical hook adapter

- Requirements: REQ-001, REQ-002, NFR-001
- Decision: 將 Windows PowerShell launcher 放入標準 `command`，移除 `commandWindows`。
- Rationale: Codex Windows runner 執行標準 `command`；目前 Unix command 的 `$()` 不能由 `cmd.exe` 解讀。這是最小且可由真實 process contract 驗證的 Seam 修正。
- Consequences: native Windows 穩定；不新增 Unix/WSL 承諾，未來跨平台需求需另立設計。

## DEC-002: 以 source-derived package 驗證取代手動同步

- Requirements: REQ-003, NFR-002
- Decision: 只修改根目錄 source hook，依既有 `esbuild.mjs` 產生 bootstrap，再由 verifier 檢查 embedded hook 與 VSIX。
- Rationale: 維持單一來源與 bootstrap exact contract，避免手動修改 `dist` 與 package 造成 drift。
- Consequences: 0.2.1 VSIX 必須重建；legacy artifacts 維持固定 hash；既有 workspace 的 exact conflict 行為不變。
