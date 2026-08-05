# 系統設計：修正 Codex CLI PreToolUse Hook 的 PowerShell 與 UTF-8 失敗

<!-- DEVWEAVE:artifact=design version=1 work=20260805-150125-bug-codex-cli-pretooluse-hook-powershell-utf -->

## 設計摘要

本設計維持現有的單一 DevWeave PreToolUse guard 與 JSON policy schema，只修正
兩個 adapter seam：

1. `Codex hook bootstrap` module：`.codex/hooks.json` 的 Windows `command`
   改為不依賴 shell variable 的 Git-root expression，並固定 PowerShell 非
   互動模式與 Python UTF-8 mode。這是 Codex runner 與 repository 的 process
   adapter，不是新的 lifecycle 或 policy engine。
2. `guard transport` seam：`.agents/skills/devweave/scripts/guard.py` 的
   `main()` 以 stdin/stdout bytes 明確使用 UTF-8；JSON decode/encode 失敗仍
   fail closed 為合法 deny JSON、process exit 0。既有 `handle_hook()` 是
   policy deep module，保持輸入 dict、輸出 `dict | None` 與所有 gate 判斷不變。

選定 launcher：

```text
powershell.exe -NoLogo -NoProfile -NonInteractive -Command "python.exe -X utf8 -B (Join-Path (git rev-parse --show-toplevel) '.agents\\skills\\devweave\\scripts\\guard.py')"
```

這個 command 同時適用於 Codex 的 `cmd.exe` runner 與 PowerShell 外層 runner；
不再使用會被多層 shell 重複展開的 `$repo`，也不新增 `commandWindows` 平行
設定。

## 選項比較

## DEC-001: Windows launcher 介面

- Requirements: REQ-001, REQ-003, NFR-001, NFR-002
- Option A（選定）：單一 shell-neutral `command`，以 `(git rev-parse
  --show-toplevel)` 直接傳給 `Join-Path`。
  - 優點：cmd 與 PowerShell 共用同一 source-derived contract；沒有外層
    variable re-expansion；Extension bootstrap 不需平行欄位。
  - 代價：仍需以真實兩種 child process 驗證 Windows quoting。
- Option B（拒絕）：加入 `commandWindows` 專用 command。
  - 拒絕理由：會形成兩份 launcher contract，且目前 repository/package
    contract 明確要求單一 `command`；也無法單獨修正 guard 的 UTF-8 input。
- Option C（拒絕）：在 command 內以 `chcp 65001`、環境變數或額外 wrapper
  改變 code page。
  - 拒絕理由：依賴 shell state，污染 runner，且不能保證 Python pipe 的
    stdin encoding。

## DEC-002: Hook transport encoding

- Requirements: REQ-002, REQ-003, NFR-001
- Option A（選定）：`guard.py` 直接讀 `sys.stdin.buffer`、以 UTF-8 decode
  後交給 `json.loads`；JSON output 以 UTF-8 bytes 寫至 `sys.stdout.buffer`。
  - 優點：不受 CP950/console code page 影響，ASCII 與繁中均可重現；輸出
    的 ASCII subset 仍是合法 UTF-8。
- Option B（拒絕）：只在 launcher 加 `python -X utf8`，保留 text stream。
  - 拒絕理由：依賴每個啟動路徑都保留 Python flag，guard 直接執行或其他
    host adapter 仍可能繞過該保護。
- Option C（拒絕）：只把 JSON 改成 `ensure_ascii=True`。
  - 拒絕理由：可降低輸出風險，但不能修正 raw UTF-8 input 被 CP950 讀取的
    問題；它也把 transport 邊界留給 host。

G1 已確認選用 A/A；沒有未回答的 material design decision。

## 介面與資料流

### Module / interface / seam

- Module：`PreToolUse hook bootstrap`（source：`.codex/hooks.json`、build
  copy：`vscode-extension/dist/bootstrap/hooks.json`）。
- External interface：Codex 傳入一個 UTF-8 JSON payload；hook 以 stdout
  回傳零或一個 hook JSON；process exit 0 表示 launcher/guard 正常完成，
  不代表 policy 一定 allow。
- Adapter seam：PowerShell 只負責從 Git root 定位 `guard.py` 並啟動
  `python.exe`；不解析或改寫 policy payload。
- Deep module：`guard.handle_hook(payload)` 維持 repo resolution、Work
  Item binding、G2/build gate 與 allow/deny 判斷。
- Transport adapter：`guard.main()` 負責 bytes→UTF-8→JSON、exception
  fail-closed 與 JSON→UTF-8 bytes；不把 encoding 細節傳入 policy module。
- Test surface：`tests/test_repository_contract.py` 的真實 child-process
  runner，並與既有 `tests/test_guard.py` 的直接 policy seam 測試互補。

### Data flow

1. Codex runner 將 payload bytes 寫入 hook stdin。
2. PowerShell 從目前工作目錄執行 Git root expression，呼叫 `python.exe
   -X utf8 -B` 與 repository guard。
3. `main()` 讀取 bytes、UTF-8 decode、`json.loads`，再呼叫 `handle_hook`。
4. `handle_hook` 回傳 `None`（正常放行/不需 policy output）或既有 deny/allow
   envelope；`main()` 以 UTF-8 bytes 輸出 envelope。
5. policy deny、malformed UTF-8/JSON 與未綁定寫入均保持 process exit 0；
   launcher 無法啟動等真正 process failure 仍由 runner 顯示為 failure。

### State and compatibility

不新增 state、ledger、CLI、JSON schema、session binding 欄位或 public verb。
`cwd` 仍由 payload 提供並由既有 `find_repo_root` 找到 repository；root 與
`vscode-extension` nested cwd 都是 supported regression inputs。Python 3.11+
stdlib-only、Windows cmd/PowerShell 及既有 Codex hook envelope 維持相容。

## 失敗模式與回復

- Invalid UTF-8 或 malformed JSON：捕捉 decode/parse error，輸出繁中 deny
  reason 的合法 JSON，exit 0；絕不轉成 allow 或 traceback-only failure。
- Guard runtime exception：沿用現有 top-level fail-closed deny，輸出 exception
  type/message 的 bounded reason，exit 0。
- Read-only Bash 或不需 policy 的 payload：`handle_hook` 回傳 `None`，stdout
  保持空白、exit 0，避免改變既有 runner semantics。
- Git root/PowerShell/Python 找不到：屬 launcher environment failure，不做
  silent fallback；tests 與 package verifier 必須讓它可見。
- Rollback：以同一 Work Item 回復 `.codex/hooks.json`、guard、tests、verifier
  與 package source，重新 build 0.2.1；沒有資料 migration 或 ledger rollback。
  既有 workspace 的 hook trust/reload 由使用者在 Codex `/hooks` 或新 session
  完成，不由 Extension 靜默覆寫。

## 高風險分析

- Migration：不適用；只改 process adapter 與 transport parsing，沒有資料
  format 或 Work Item state migration。
- Rollback：可逆；source-derived bootstrap 重新產生，VSIX 僅接受 current
  0.2.1；回復前後均以 verifier 與 child-process regression 檢查。
- Security：保持 fail-closed。UTF-8 decode 只影響 transport，不放寬
  `handle_hook` policy；`-NoProfile -NonInteractive` 降低 profile side effect，
  Git root 仍由 repository Git CLI 決定；不接受 user-controlled shell fragment。
- Compatibility：同一 command 必須通過 cmd.exe 與 PowerShell，root/subdir、
  ASCII/繁中 raw payload；不依賴 `commandWindows`，避免 host 版本分歧。
- Performance：每次 hook 只增加一次 bounded bytes decode/encode，沒有常駐
  process、network、cache 或新 dependency；以 package/full-suite 基線確認。
- Independent review：因為是 high-risk，G3 final artifacts、diff、scope、
  evidence 與 Wiki context 穩定後由唯一 DevWeave router 啟動一次 isolated
  read-only review；主 agent 不自行模擬或修改 review evidence。

## 設計決策

## DEC-003: Guard policy 與 transport 分離

- Requirements: REQ-002, REQ-003, NFR-002
- Decision: 保持 `handle_hook` policy seam 不變，把 UTF-8 bytes parsing/output
  限定在 `main()` transport adapter。
- Rationale: 最小 locality、避免把 encoding 分支散佈到 gate/policy 邏輯，且
  可用 process-level tests 直接驗證 public hook seam。
- Consequences: main 增加少量 adapter helper；直接 unit policy tests 不需改
  payload contract，malformed input 由 subprocess regression 補上。

## DEC-004: Source-derived package contract

- Requirements: REQ-004, NFR-003
- Decision: 由根 `.codex/hooks.json` 產生 bootstrap，verifier 檢查
  `powershell.exe`、`-NoLogo`、`-NoProfile`、`-NonInteractive`、`-X utf8`、
  `python -B`、Git-root expression 與無 `commandWindows`。
- Rationale: 讓 package 內的 control 與 live source 同步，避免只修 root hook
  卻讓 Extension bootstrap 帶出舊 launcher。
- Consequences: package build 會刷新 dist/VSIX artifact，需在 G3 保存 current
  package/verifier evidence；manifest entry count/版本契約不變。
