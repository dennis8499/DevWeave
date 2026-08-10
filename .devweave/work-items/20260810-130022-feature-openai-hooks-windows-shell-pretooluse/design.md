# 系統設計：依 OpenAI Hooks 最佳實踐強化 Windows 跨 Shell PreToolUse 相容性

<!-- DEVWEAVE:artifact=design version=1 work=20260810-130022-feature-openai-hooks-windows-shell-pretooluse -->

## 設計摘要

選定方案是保留單一 `PreToolUse` policy seam，為同一個 command handler 提供 POSIX `command` 與 Windows `commandWindows` 兩個 launcher Adapter。Windows adapter 使用無 profile、非互動的 `powershell.exe`，再以 `py -3 -X utf8 -B` 從 Git root 執行既有 `guard.py`；POSIX fallback 使用 `python3 -X utf8 -B` 與 Git-root path expression。兩條路徑只負責啟動，同一份 stdin/stdout JSON 仍交給同一個 guard policy implementation。

這是三個深模組的組合：

- Hook Contract Module 的 Interface 是 `.codex/hooks.json` 的精確 JSON schema；它隱藏 Codex tool matcher、OS launcher selection、timeout 與 source-derived bootstrap contract。
- Guard Module 的 Interface 是既有 `handle_hook(payload, repo)` 與 raw UTF-8 stdin/stdout；它隱藏 work binding、gate、scope、Wiki write policy、malformed input 與 fail-closed decision。
- Doctor Diagnostics Module 的 Interface 是既有 `doctor(repo) -> {ok, checks[]}`；它隱藏 executable lookup、version probe、hook schema validation、launcher child process 與 bounded diagnostics。

主要不變量：matcher 不使用 wildcard；只保留一個必要 `PreToolUse` event；`guard.py` 的 policy 與 decision schema 不變；正常 logical allow/deny 的 process exit 維持 0；malformed/exception 不得放行；Extension 只從根 hook source-derive，不執行 launcher 或 engine。

## 選項比較

### Hook launcher

- 選項 A：維持目前單一 Windows PowerShell `command`。優點是變更小；缺點是沒有可被 Codex 選取的 POSIX fallback，且不能把 Windows adapter 的 contract 與其他 OS 明確分開，無法滿足完整跨環境要求。
- 選項 B：只提供 `commandWindows`。優點是 Windows 設定直觀；缺點是非 Windows fallback 缺失，source-derived bundle 在其他 host 沒有可用的標準 command。
- 選項 C：提供 POSIX `command` 加 Windows `commandWindows`（選定）。兩個 Adapter 共用 `guard.py`，最小化 policy 變更並讓 verifier 可檢查雙路徑；代價是 schema、package verifier 與 matrix tests 需要同時維護。

### Doctor probe

- 選項 A：只檢查 executable 是否存在。成本低，但無法發現 PowerShell quoting、Git-root resolution 或 UTF-8 stdin/stdout 問題。
- 選項 B：先檢查 schema/executables，再以實際 `commandWindows` 執行 read-only Bash payload（選定）。這會驗證真正 launcher seam，同時不觸發寫入；代價是 doctor 在 Windows 上需要 bounded child process。
- 選項 C：只提供 manual instructions，讓 operator 自己執行 hook。可避免 doctor process，但結果不可機械驗證，也無法滿足 current release contract。

### Extension consistency

- 選項 A：讓 Extension 自己重建 hook JSON。拒絕，會產生第二個 source of truth。
- 選項 B：維持 `esbuild.mjs` 從根 `.codex/hooks.json` copy，verifier 比對 root 與 embedded bytes/semantic contract（選定）。這保留 source-derived locality；代價是每次 hook contract 變更都必須重建 current VSIX。

## 介面與資料流

### Hook Contract Module

Interface：

```text
hooks.PreToolUse = [
  {
    matcher: "^(Bash|apply_patch|Edit|Write)$",
    hooks: [{
      type: "command",
      command: "python3 -X utf8 -B ...guard.py",
      commandWindows: "powershell.exe ... py -3 -X utf8 -B ...guard.py",
      timeout: 30,
      statusMessage: "Checking DevWeave gates"
    }]
  }
]
```

`command` 使用 POSIX path separator 與 command substitution；`commandWindows` 使用 `Join-Path (git rev-parse --show-toplevel)`，不讀取 `$repo`、current cwd 或 profile。Windows literal 為：

```text
powershell.exe -NoLogo -NoProfile -NonInteractive -Command "py -3 -X utf8 -B (Join-Path (git rev-parse --show-toplevel) '.agents\\skills\\devweave\\scripts\\guard.py')"
```

Codex 依 host OS 選擇 field；兩者都把 payload bytes 傳給 `guard.py`。Matcher 不會擴張到 hosted tools；未來 MCP mutation 需明確加入另一個具名 matcher 才能受本地 guard 保護。

### Guard Module

Guard 的外部 Interface 不變：stdin 是 Codex PreToolUse JSON，stdout 是 optional `hookSpecificOutput` JSON，正常 logical result 的 process exit 是 0。`_read_hook_payload` 仍從 `sys.stdin.buffer` decode UTF-8，`_write_hook_json` 仍以 `ensure_ascii=False` encode UTF-8；`handle_hook` 繼續以 tool name 分派既有 policy。Launcher failure（找不到 `py`、PowerShell、Git 或 script）與 policy deny 是兩種不同結果：前者由 doctor/host launcher error 顯示，後者是合法 deny JSON。

### Doctor Diagnostics Module

保留 `doctor(repo)` 的 JSON Interface 與既有 check names，新增 bounded checks：`py-3`、`cmd`、`powershell`、`pwsh`、`hook-schema`、`launcher-probe`。Windows 上 `py -3 --version`、各 shell version/process probe 與 `commandWindows` read-only Bash payload 都使用 `subprocess.run(..., capture_output=True, timeout=...)`；不得寫入 project、cache、Wiki 或 work state。非 Windows host 將 Windows-only checks 標示為 not applicable，而不冒充 Windows certification。

`hook-schema` 解析 JSON 並確認 exact matcher、唯一 command hook、雙 launcher、timeout/status；`launcher-probe` 在 repository root（必要時也以 nested fixture）執行 read-only `Bash` payload，預期 exit 0 且 stdout 為空。每個 check 的 detail 以繁體中文說明缺少 executable、trust step、schema mismatch 或 process stderr，方便 CMD/PowerShell/VS Code operator 定位問題。

### Cross-shell test seam

`tests/test_repository_contract.py` 會建立一個小型 runner Adapter，輸入 `{command, cwd, payload}`，分別以 `cmd.exe /d /s /c`、`powershell.exe -NoLogo -NoProfile -NonInteractive -Command` 與 `pwsh -NoLogo -NoProfile -NonInteractive -Command` 執行 `commandWindows`。同一組 cases 在 root 與 `vscode-extension` nested cwd 執行，測試 raw UTF-8 Chinese path、unbound Write deny、malformed JSON deny、read-only Bash silence 與 process exit。

### Extension release flow

`esbuild.mjs` 維持唯一 source-derived seam：copy root `.codex/hooks.json` 到 `dist/bootstrap/hooks.json`，manifest 保存 byte length/SHA-256 與 bundle version。`verify-package.mjs` 讀 root 與 embedded hook，檢查 byte/semantic equality、雙 launcher contract、0.2.3 package/bundle/VSIX version、58 files、119 entries 與 required entries。0.2.2 VSIX 只作為保留 artifact，不是 current verifier input。

## 失敗模式與回復

- Hook JSON malformed、guard exception 或 UTF-8 decode failure：沿用 fail-closed deny JSON、process exit 0；測試必須確認不會放行，也不把正常 policy deny 誤報為 launcher crash。
- `py -3`、PowerShell、Git 或 `guard.py` 不存在：Windows launcher 可能在 host 端失敗；doctor 將對應 check 標為 false 並顯示安裝/信任/路徑診斷，不修改使用者環境、不自動下載 runtime。
- Git-root expression 或 nested cwd 解析失敗：launcher probe 與 matrix test fail；不改用 current cwd 或 `$repo` workaround，避免把路徑錯誤隱藏成偶發 policy 行為。
- Hook schema 缺少 `commandWindows`、matcher 過寬或 timeout/status 不符：doctor 與 package verifier fail closed；Extension 不會以不完整 bundle bootstrap。
- 0.2.3 package、manifest、embedded hook 或 VSIX integrity mismatch：`npm.cmd run package`/verifier 失敗，current artifact 不可接受；保留 0.2.2 artifact 與 workspace data，停止散布並以修正後新版本重建。
- 既有 workspace 的 exact `.codex/hooks.json`：Extension 不靜默覆寫；operator 需在確認內容與 Codex trust 後套用新 source。這避免 migration 造成既有 hook bytes 被無提示改動。

Rollback 是可逆的 source/release 操作，不引入自動 destructive cleanup：停止散布 0.2.3、保留 0.2.2、保留 `.devweave`/Wiki/logs，建立修正 work item 後重新產出 current artifact。G3 以完整 Git diff、source fingerprint、VSIX hash 與 Wiki reconciliation 確認沒有遺漏。

## 高風險分析

- Migration：不修改 ledger/schema、既有 guard policy 或 Extension runtime API；只演進 hook configuration、doctor diagnostics 與 current release metadata。既有 exact workspace 需明確確認後更新，不能由 Extension 靜默 migration。
- Rollback：保留 0.2.2 VSIX 與 workspace data；0.2.3 verifier fail、launcher failure 或 critical review 時停止 release，不自動刪除資料或改寫 conflict file。
- Security：exact matcher、無 wildcard、無 trust bypass、無 profile、無 `$repo`、Git-root containment、`py -3` explicit runtime、raw UTF-8、malformed deny 與正常 deny exit 0 都是 security invariants。Hook 仍是 Codex guardrail，不是 OS sandbox；外部 editor/disabled hook 的限制要在文件與 G3 diff review 說明。
- Compatibility：POSIX `command` 與 Windows `commandWindows` 共用 guard interface；CMD、Windows PowerShell 5.1、PowerShell 7、root/nested cwd 由實際 child process 覆蓋。缺少任何正式 Windows prerequisite 時 doctor 不宣稱通過。
- Performance：hook timeout 30 秒，guard policy 不增加額外 network/process；doctor probe 每個 executable/launcher 使用短 timeout 且只在 operator 呼叫時執行。package verifier 只在 build time hash files/VSIX。
- Observability：doctor 每項 check 有 machine name、boolean 與 bounded detail；verification 透過 DevWeave raw logs/evidence 保存 exit code、stdout/stderr、source fingerprint 與 command profile；不新增 production telemetry。
- Independent Review：G3 final diff 穩定後由既有 router exactly once 啟動 isolated read-only reviewer；engine 不 spawn reviewer，reviewer 不修改 source/Wiki/ledger，也不執行 approve/revise/close。

## 設計決策

## DEC-001: 以雙路徑 hook adapter 固定 OS launcher contract

- Requirements: REQ-001, REQ-002, REQ-003, NFR-001, NFR-002
- Decision: 選定 POSIX `command` 加 Windows `commandWindows`；Windows 使用 `powershell.exe -NoLogo -NoProfile -NonInteractive` 與 `py -3 -X utf8 -B`，兩路徑都從 Git root 找到 `guard.py`。
- Rationale: 同時滿足 host OS fallback、Windows shell matrix、UTF-8 與 source-derived bootstrap；不把未宣告或 wildcard workaround 當作 contract。
- Consequences: `.codex/hooks.json`、verifier、tests、docs 與 Wiki 必須一起更新；guard policy 本身不變。

## DEC-002: 把 guard 保持為 policy 深模組，launcher 只做 Adapter

- Requirements: REQ-002, REQ-003, NFR-001
- Decision: 不把 shell detection、doctor logic 或 package release logic 塞進 `guard.py`；launcher 只傳輸 stdin/stdout，既有 guard module 繼續承擔 policy。
- Rationale: guard interface 小且 depth 高，維持 policy locality；兩個 OS launcher 是真正的 adapters，測試可跨同一 interface。
- Consequences: launcher/process failure 與 logical deny 必須在 docs、doctor、tests 分開表達；不新增 guard JSON 欄位。

## DEC-003: Doctor 以唯讀 real-process probe 作為 operator diagnostic seam

- Requirements: REQ-005, NFR-002
- Decision: 在 `devweave_core.py` 的既有 `doctor(repo)` 內加入 schema/executable/version/launcher checks，所有 subprocess 都 bounded、capture output 且不寫入 repository。
- Rationale: 僅有 `which` 不能發現 quoting/Git-root/UTF-8 問題；直接呼叫 commandWindows read-only payload 能提供較深的 diagnostic leverage，而不複製 guard policy。
- Consequences: doctor 在缺少 runtime 時會回報 false；非 Windows 只標示 not applicable，不把該環境列為 Windows certification。

## DEC-004: 用真實 child-process matrix 跨同一 hook interface 驗證

- Requirements: REQ-004, NFR-002
- Decision: repository contract 以 CMD、Windows PowerShell 5.1、PowerShell 7 三個 runner，在 root/nested cwd 執行相同 payload cases；VS Code integrated terminal 保留 G3 manual walkthrough。
- Rationale: process-level evidence 能捕捉 shell quoting、code page、Git-root 與 stdout/exit 邊界；VS Code host profile 本身不能由 Python engine 假裝自動證明。
- Consequences: tests 依賴 Windows prerequisites；缺少 shell 時要由 doctor/verification 明確記錄 failure，而不是 silently skip。

## DEC-005: 0.2.3 current-only source-derived release

- Requirements: REQ-006, REQ-007, NFR-003
- Decision: package/lock/verifier/help/docs 使用 0.2.3；`esbuild.mjs` 維持從 root hook 產生 embedded bundle；0.2.2 artifact 保留但不參與 current verification。
- Rationale: current-only verifier 能避免歷史 artifacts 污染 release decision，同時保留上一版供事故處置與資料保全。
- Consequences: 需重新建立 VSIX、更新 baseline/Wiki release facts，並以 root/embedded hook equality 防止 drift。

## DEC-006: Wiki 與 baseline 延後至 verification promotion

- Requirements: REQ-007, NFR-003
- Decision: G2/implementation 只把既有 Wiki 作 read-only context；verification 以 Knowledge Review `promote` 更新 overview、architecture、knowledge-engine、vscode-extension 四頁及 coupled index/log，並透過 CLI 更新三份 baseline。
- Rationale: 避免在設計未核准或測試未完成時寫入 source-bound knowledge；四頁正好覆蓋 affected source 與 release contract，仍在五頁上限內。
- Consequences: Wiki stale warning 會持續到 G3；任何新增 source change 都要刷新 affected pages、source fingerprints、seals 與 promote log。

## DEC-007: High-risk reviewer 維持既有 router-owned lifecycle

- Requirements: NFR-001, AC-007
- Decision: 不在 Python engine、doctor 或 Extension 新增 reviewer spawn；G3 穩定後由單一 router 啟動 exactly one isolated read-only reviewer，machine-only `review record` 保存結果。
- Rationale: 保持 reviewer 的 authority、context containment 與人工作業 Gate 邊界；避免第二套 orchestrator 或 permission surface。
- Consequences: implementation/verification 必須保留 current approved artifacts、complete diff、scope/baseline/Wiki context 與 evidence，供 G3 reviewer 使用。
