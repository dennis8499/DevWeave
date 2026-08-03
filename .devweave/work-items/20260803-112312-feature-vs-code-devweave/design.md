# 系統設計：空白 VS Code 專案初始化產生 DevWeave 流程內容

<!-- DEVWEAVE:artifact=design version=1 work=20260803-112312-feature-vs-code-devweave -->

## 設計摘要

選擇一個位於 Extension 與 VS Code workspace filesystem 之間的 deep module：
`BootstrapInstaller`。它以小介面接收「版本化 bootstrap bundle」與可替換的 workspace
filesystem adapter，內部負責 manifest 驗證、path containment、資產完整性、preflight
conflict scan、冪等判定、寫入與 rollback；`ExtensionController` 只負責選 root、要求
使用者確認、呼叫 installer、刷新 snapshot 與顯示結果。

這個 seam 讓所有安全與一致性規則集中在一個 implementation，Webview、command palette
與未來其他初始化入口共用同一個行為；memory adapter 可以跨平台測試，不需要啟動 VS Code、
Python 或 shell。Extension 原本的 `WorkspaceSnapshotReader` 保持唯讀，bootstrap 的
write interface 不污染既有 projection reader。

## 選項比較

## DEC-001: 採用 Extension 內建的直接檔案 bootstrap

- Requirements: REQ-001, REQ-002, REQ-003, REQ-005, NFR-001, NFR-002
- Decision: 由 Extension 在明確確認後，透過 VS Code workspace filesystem API 寫入
  fixed manifest 內的檔案與目錄。
- Rationale: 滿足「只靠 VS Code Extension 完成安裝初始化」，不需要 Codex Chat、手動
  CLI 或外部 process；installer 是單一 deep module，呼叫端介面小且測試面一致。
- Consequences: Extension 從唯讀變成受控的初始化寫入者，必須增加 high-risk security
  review、rollback、package provenance 與使用者確認；後續 workflow mutation 仍交由
  DevWeave engine 與既有 gate。

## DEC-002: 以 build-time source-derived bundle 提供 engine 與 starter

- Requirements: REQ-002, NFR-002, NFR-003
- Decision: `esbuild.mjs` 從 repository 目前的 `.agents/skills/devweave/`、hook template
  與 bootstrap templates 產生 `dist/bootstrap/` 及 `manifest.json`；manifest 為每個
  destination 記錄 source、kind、byte length 與 SHA-256。Runtime 只讀取 VSIX 內的 bundle，
  不下載或執行來源。
- Rationale: 保持 engine、skill、references、assets 與 Extension 版本一起發佈，避免
  手工複製的第二份 runtime 長期漂移；production package 可透過 manifest completeness
  test 驗證。
- Consequences: package build 必須能讀取 repository source；VSIX 會變大，但仍是有限的
  text-only runtime 資產；project defaults 與日期化 Wiki starter 由 installer 依同一版本
  templates 產生。

## DEC-003: preflight 全掃描後 commit，失敗只 rollback 本次新建檔案

- Requirements: REQ-004, NFR-001, NFR-002
- Decision: installer 先驗證 manifest、所有 parent path、symlink、目標類型與既有 bytes；
  只有沒有 conflict 時才建立 directories 與 missing files。commit 期間記錄本次新建的
  files，任何 write error 都只刪除本次新增且仍可安全辨識的 files，並回傳 rollback/error
  report；既有檔案永不刪除或覆寫。
- Rationale: most failure paths 在任何 mutation 前被擋下；不可避免的 I/O failure 不會
  留下可被誤認為成功的半套初始化，且不會碰使用者原有 bytes。
- Consequences: rollback 若本身失敗，report 必須列出殘留 created paths，使用者需依診斷
  手動處理；installer 不嘗試猜測或修復 partial/conflicting project。

## DEC-004: native modal confirmation 加上 direct command 與 dashboard CTA

- Requirements: REQ-001, REQ-003, REQ-005
- Decision: 未初始化 dashboard 的 primary action 與 `DevWeave: Initialize Workspace`
  command 都進入同一個 controller method；host 以 `showWarningMessage(..., { modal: true })`
  要求使用者確認後才呼叫 installer。初始化不再以「Copy initialization prompt」作為主要
  入口，既有 action composer 仍可保留給其他 engine actions。
- Rationale: confirmation 不依賴 Webview 自己可信的 HTML state，且 keyboard/command
  palette 與 dashboard 行為共用一個 seam。
- Consequences: Webview protocol 新增 `initialize` message 與 bootstrap result；成功後
  需要 refresh snapshot，取消不寫入任何 repository bytes。

## 介面與資料流

### Bootstrap bundle interface

```text
BootstrapBundle {
  version: string
  directories: [{ destination: repo-relative path }]
  files: [{ destination, source, sha256, byteLength }]
}
```

`destination` 必須是固定 repo-relative path；`source` 只能指向 Extension package 的
`dist/bootstrap/` 下資產。Bundle loader 先驗證 JSON shape、duplicate destinations、
hash/length 與 source containment，再交給 installer。

### Workspace filesystem seam

```text
BootstrapWorkspace {
  stat(path): file | directory | symlink | absent
  readBytes(path): Uint8Array
  writeBytes(path, bytes): void
  createDirectory(path): void
  delete(path): void                 // 僅 rollback 本次建立的 path
}
```

`VscodeBootstrapWorkspace` 是 VS Code `workspace.fs` adapter，將 `FileType.SymbolicLink`
與非 regular file 映射成安全診斷；`MemoryBootstrapWorkspace` 是 unit-test adapter。兩者
共享 `normalizeRelativePath` 與 parent traversal 檢查，production adapter 不接受使用者
傳入的任意 root。

### Installer interface

```text
install(bundle, workspace): Promise<BootstrapReport>

BootstrapReport {
  ok: boolean
  status: initialized | already_initialized | conflict | failed
  created: string[]
  adopted: string[]
  skipped: string[]
  conflicts: [{ path, reason }]
  errors: [{ path, reason }]
  rolledBack: string[]
}
```

Installer 的唯一 public method 是 `install`；它內部依序執行：

1. canonicalize/validate manifest destinations 與 source；
2. 確認每個 parent path 都不是 symlink，directory target 類型正確；
3. 讀取所有 file source，驗證 byte length/SHA-256，並掃描既有 destination；相同 bytes
   記為 `adopted`，不相同記為 conflict；
4. conflict/asset error 時不進入 commit；
5. 先建立缺少的 directories，再以 atomic adapter write 建立缺少的 files；
6. I/O 失敗時 rollback 本次新建 files，回傳 failed report；成功回傳 initialized report。

### Controller、host 與 Webview flow

1. `WorkspaceSnapshotReader` 發現 project missing，snapshot 保持 warning 且不產生 mutation。
2. `renderRepositoryState` 顯示 Not initialized、安裝內容摘要與 `Initialize DevWeave`。
3. Webview 傳 `{ type: "initialize" }`；`DashboardPanel` 轉交 controller。
4. controller 重新 refresh/確認 project 仍不存在，呼叫 native modal confirmation；取消
   直接回傳 no-op。
5. controller 透過 package resource adapter 讀取 bundle，呼叫 `BootstrapInstaller`；
   不呼叫 prompt composer、clipboard、Python、shell 或 network。
6. 成功或失敗都寫入 output channel，傳送 bootstrap report；成功才重新讀取並傳送 snapshot，
   失敗保留 conflict/error diagnostics。
7. command palette command `devweave.initialize` 與 dashboard CTA 使用同一 controller method。

### Bootstrap targets

- Runtime: `.agents/skills/devweave/**`（SKILL、scripts、references、assets、agent metadata）。
- Hook: `.codex/hooks.json`。
- Project: `.devweave/project.json`，schema 1、managed true、zh-TW、空 commands/profile
  defaults、knowledge root `wiki`。
- Directories: `.devweave/cache/sessions/`、`.devweave/work-items/`、
  `.devweave/baseline/capabilities/`、`wiki/` 與九個 typed Wiki directories。
- Generated files: `.devweave/baseline/{product,architecture,quality}.md`、
  `wiki/{index,overview,log}.md`；Wiki `{date}` placeholders 只在 install 時替換為 UTC date。

## 失敗模式與回復

| 情況 | 行為 | 使用者可觀察結果 |
| --- | --- | --- |
| VSIX manifest 缺失/格式錯誤 | preflight fail，零 workspace mutation | output channel + UI 顯示 bundle diagnostic |
| source hash/length 不符 | preflight fail，零 workspace mutation | 顯示 source 與 expected/actual hash |
| target 已是 symlink、非預期類型或 path 不安全 | preflight fail，零 workspace mutation | 顯示 exact destination 與安全原因 |
| existing bytes 與 bundle 不同 | conflict fail closed，保留所有 bytes | 顯示 conflict paths，建議人工檢視或另立 migration |
| write/createDirectory I/O error | rollback 本次新建 files；不碰既有 files | 顯示 failed/rolledBack/rollback residual paths |
| 使用者取消 modal | no-op | 不建立或改變任何 repository bytes |
| 已有合法 project.json | 不進入 installer | 維持原 dashboard/prompt workflow |

Installer 不會刪除既有檔案、不會自動修復 partial installation，也不會把 conflict 誤標成
`managed` success。若 rollback 無法完成，report 明確標示 residual paths，避免靜默失敗。

## 高風險分析

- Migration：不是 schema migration；只接受 project missing 的 additive bootstrap。已存在
  project、hook、skill 或 starter 的 workspace 不由本 feature 自動升級。
- Rollback：preflight 是主要控制；commit rollback 只針對本次 created files，並以 report
  保留無法刪除的殘留。沒有 destructive cleanup，也不使用 OS trash/外部命令。
- Security：manifest destination/source containment、duplicate detection、SHA-256、
  symlink/ancestor 檢查、native confirmation 與無 process/network 是必要 invariant；
  `openFile` allowlist 仍不擴張到任意 workspace path。
- Compatibility：schema 1 project defaults 與既有 `WorkspaceSnapshotReader` contract
  相容；已 managed workspace 不觸發 write；既有 `.gitignore` 不在 bootstrap target，避免
  未經確認的 user-file merge。
- Performance：bundle 主要是有限的 UTF-8 text files；preflight 讀取每個 source 一次並
  計算 SHA-256，應在一般 workspace 內以單次 UI action 完成；不掃描整個 repository。
- Review：G3 必須提供 current `review` evidence，獨立檢查 path containment、asset
  provenance、rollback、managed compatibility 與 no-external-process invariant。

## 設計決策

以上 DEC-001 至 DEC-004 為本 feature 的完整設計決策；`plan.md` 會以這些 decision、
REQ/NFR 與 AC 建立 immutable TASK graph。
