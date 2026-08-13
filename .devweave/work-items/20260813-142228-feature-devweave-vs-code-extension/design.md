# 系統設計：強化 DevWeave VS Code Extension 治理、驗證與效率

<!-- DEVWEAVE:artifact=design version=1 work=20260813-142228-feature-devweave-vs-code-extension -->

## 設計摘要

本設計把 DevWeave 分成三個深模組與兩個 release seams：

- `Filesystem Projection Module`：以 `FileSystemPort.inspectPath()` 取得 path kind，負責讀取 workspace、bootstrap completeness、Wiki provenance 與 bounded Work Item summary/detail。Extension 仍是非權威 filesystem projection。
- `Verification Selection Module`：由 DevWeave engine/CLI 讀取 command metadata，驗證依 profile、affected paths、releaseOnly 與 dependency 選擇可執行 command；高風險 profile 維持完整集合。
- `Evidence Metrics Module`：在既有 verification/evidence record 上加入 optional context/tool/usage metrics；不建立第二個 ledger，未提供的 host usage 明確標成 unavailable。
- `Build Provenance Seam`：build 先清理 generated `dist`，manifest 寫入 package version、source HEAD、manifest hash、bootstrap count；package builder 只建立同目錄唯一 candidate，verifier 以明確 `--artifact` 驗證 candidate，release orchestrator 只有在驗證成功後才以同目錄 atomic rename promotion current VSIX。
- `Pinned Smoke Seam`：smoke 明確使用 accepted VS Code runtime version；缺少 cache/runtime 時 fail with guidance，不下載、不 fallback。

關鍵不變量：Extension 不執行 engine、Shell、network、Git 或 Codex API；bootstrap 只新增缺失內容且保留 conflict/rollback；Wiki 在 G3 前 read-only；`WorkspaceSnapshot.authoritative` 永遠為 false；只有 engine 明確輸出的資料才可稱為 engine observation；high-risk G3 exactly one isolated read-only reviewer。

## 選項比較

### DEC-001：Filesystem path kind seam

- 選項 A：在 `WorkspaceSnapshotReader` 內以 `exists()` 加讀目錄推測 path kind。拒絕；會複製 `BootstrapInstaller` 的 stat 語意，且無法可靠辨識同名 file、symlink 與 other。
- 選項 B：把 `stat()` 直接暴露給每個 caller。拒絕；呼叫端會散落 path-kind、symlink 與錯誤語意，介面變淺。
- 選項 C：在 `FileSystemPort` 增加單一 `inspectPath()` seam，由 VS Code adapter 與測試 adapter 實作（選定）。一個小介面隱藏 VS Code FileType/錯誤轉換，Bootstrap 與 Snapshot 共用同一分類。

### DEC-002：Snapshot detail loading

- 選項 A：維持一次讀取所有 Work Item artifact/evidence/events。拒絕；closed history 增加 refresh latency、memory 與 host context footprint。
- 選項 B：初次只讀 state summary，選取 work 時以新的 detail seam 讀取 artifact/evidence/events/raw log（選定）。初次刷新較輕，且保留選取 work 的完整檢視能力。
- 選項 C：Extension 啟動另一個 engine/API 取得 detail。拒絕；違反既有 Extension security boundary 與 source-of-truth 原則。

### DEC-003：Readiness authority

- 選項 A：以目前檔案狀態推導 `engineObservedAt` 與 ready。拒絕；updated file time 不是 engine observation。
- 選項 B：保留 projection precheck，將 engine status/observation 設為 unknown/unavailable，UI 只顯示「可供人工審查」並交由 `$devweave status/next`（選定）。這是最精準且不增加 runtime authority 的做法。
- 選項 C：在 Extension 內重做 engine Gate algorithm。拒絕；會產生第二個治理 implementation，且容易與 CLI 漂移。

### DEC-004：Verification selection

- 選項 A：只透過手工 profile list 選 command。拒絕；無法表達影響範圍與 release-only constraint。
- 選項 B：在既有 command object 增加 optional metadata，由 engine 做 path intersection、dependency closure 與 release policy selection（選定）。舊 command 沒有 metadata 時維持 profile 行為，保持向後相容。
- 選項 C：另建 workflow/CI matrix file。拒絕；增加第二個 source of truth 與 governance surface。

### DEC-005：Metrics transport

- 選項 A：新增獨立 metrics database/ledger。拒絕；增加資料保留、權限與同步成本。
- 選項 B：在既有 evidence JSON summary 加 optional `metrics` object，context manifest 使用 bounded artifact/cache reference（選定）。可與 source fingerprint、task、AC 一起驗證，不宣稱 host 未提供的 token。
- 選項 C：只在 console 輸出 metrics。拒絕；無法建立 baseline、比較 eval 或在 G3 重現。

## 介面與資料流

### Extension interfaces

```text
type FileSystemPathKind = "missing" | "file" | "directory" | "symlink" | "other";
interface PathInspection { kind: FileSystemPathKind; }
interface FileSystemPort {
  inspectPath(path: string): Promise<PathInspection>;
  ...existing read/exists/readDirectory methods...
}
```

`exists()` 保留給簡單 presence checks；bootstrap completeness 與 directory/file contract 必須使用 `inspectPath()`。`BootstrapCompletenessProjection` 新增 `pathKinds: Record<string, FileSystemPathKind>` 與 `conflictReasons: Record<string, string>`，保留既有 `missing`/`conflicts` 欄位供舊 Webview 相容。

`WorkspaceSnapshot` 新增 `projectionReadiness` 與 `engineGateStatus`。前者是 `ready | attention | blocked` 的非權威預檢；後者只有讀到明確 engine observation 時才可為 `observed`，目前 filesystem reader 固定回傳 `unavailable`，`engineObservedAt` 不再由 work `updatedAt` 偽造。`ReviewReadiness` 的 ready 語意改為「projection ready / manual reviewable」，不能宣稱 Gate 已通過。

Work Item read flow：初次 `readWorkspace()` 讀 project、baseline、Wiki page summaries、bootstrap inspection 與每個 work 的 bounded state summary；UI 選取 work 後才呼叫 `readWorkItemDetail(workId)` 取得 artifact、tasks、evidence、waivers、events 與 bounded raw-log metadata。Snapshot revision/selection revision 維持既有 PreviewGate invalidation；detail failure 只影響選取 work。既有 cache 以 path/content hash invalidation，每個 artifact、event 與 raw log 維持安全上限。

Wiki page projection 保留 title/type/status/sources/fingerprints/bodyPreview，新增 `contentHash`、`truncated` 與 parser diagnostics；Wiki search UI 明確說明為 bounded snapshot search。

### Engine/CLI command contract

Command entry 的 optional metadata：

```json
{
  "affected_paths": ["vscode-extension/src", "vscode-extension/test"],
  "writes": "none | generated | tracked-artifact",
  "outputs": ["vscode-extension/dist"],
  "release_only": false
}
```

`depends_on`、`required_for`、`exclusive_group` 維持既有格式。`command set` 接受 metadata flags；validator 驗證 relative paths、allowed enum、string arrays、no duplicate paths。Profile selection 先取 profile members，閉包補齊 dependencies，再以 caller-provided changed paths 過濾 affected paths；沒有 metadata 的 legacy command 只在 explicit full profile 中執行。`release_only` commands 只在 high/release selection 執行；high profile 維持完整 current command 集合。

為避免未指定 changed paths 導致誤漏跑，CLI `verify --profile` 的 `--path` 為 optional；省略時執行完整 profile。指定 paths 時只允許省略非-high-required 且與 affected paths 無交集的 command，batch output 記錄 selected/skipped/reason。

### Evidence/context metrics

既有 evidence 增加 optional bounded `metrics` object：

```json
{
  "metrics": {
    "duration_ms": 123,
    "context": {"pages": 5, "bytes": 57772, "chars": 54800},
    "verification": {"selected": 3, "skipped": 2, "cache_hit": false},
    "tools": {"read": 12, "search": 2, "write": 0, "test": 3},
    "usage": {"status": "unavailable", "input_tokens": null, "output_tokens": null, "cached_tokens": null, "cost": null}
  }
}
```

Exact host usage 僅在 caller 傳入合法 usage object 時保存；engine 不估算 token。Metrics 綁定 command/profile、source fingerprint、Git HEAD 與 batch id，並受 raw log limit 約束。

### Build/smoke flow

`npm run build` 清理並建立 development `dist`；`npm run package` 以 production build、source-derived bootstrap manifest、candidate VSIX builder、candidate verifier 與 release orchestrator 組成 release gate。Manifest 加入 `sourceGitHead`、`manifestSha256`、`packageVersion`、`bootstrapFileCount`。`package-vsix.mjs` 只接受 `--output` 並寫入同目錄唯一 candidate；`verify-package.mjs` 必須接受 `--artifact`，沒有指定 artifact 時 fail closed；orchestrator 以明確 argv 執行兩者，成功後才 promotion。

`npm run test:smoke:current` 要求固定 accepted runtime `1.131.0` 的 cached executable；缺少時輸出 actionable failure。網路下載只允許明確 operator setup，不在 canonical smoke command 中進行。

## 失敗模式與回復

- `inspectPath()` 失敗：回傳 `other`/diagnostic，bootstrap completeness 不得 complete；不可用 `exists()` 猜測為缺失或正常。
- 同名 file 取代 expected directory、symlink 或 other：加入 `conflictReasons`，保留現有 bytes，不覆寫；使用者修正後 Refresh 可重試。
- detail read 失敗或超過上限：保留 summary，selected work 顯示 detail unavailable/truncated，提供 `$devweave status <work>` handoff。
- Wiki frontmatter 不支援：page 保留 source/hash/body preview，加入 parse error；不把 malformed field 當作核心 bootstrap readiness。
- engine 沒有 explicit observation：`engineGateStatus=unavailable`，UI 顯示 projection-only，不顯示 engine passed。
- command metadata invalid：project/CLI validation fail closed；legacy command 僅在 metadata 缺失時走 legacy full-profile 語意。
- selective profile 依賴未被選入：自動補 dependency closure；若仍違反 profile/high policy，verification fail，不執行不完整集合。
- clean build/package provenance mismatch：verifier fail，保留既有 current/retained VSIX 與 workspace data；orchestrator 不執行 promotion，finally best-effort 清理 candidate 並回傳非零錯誤。
- pinned smoke runtime 缺失：command 失敗並指向 accepted runtime/cache setup，不 fallback 或自動下載。
- metrics malformed/unknown：忽略 optional usage payload、保留 `unavailable`，不讓 metrics 影響核心 Gate；context/source fingerprints 仍由 engine authoritative path 驗證。

Bootstrap rollback 只刪除此 install operation 建立的 files/directories；build rollback 是保留舊 VSIX、清除 generated output 後重建，不刪除 workspace state。VSIX release transaction 永不先刪除 current 或建立 backup：candidate 與 current 同目錄以確保同檔案系統 promotion，verify failure、promotion failure 與 cleanup error 都保留 current/retained bytes；硬中斷可能留下可辨識 candidate，但不會改變 current。command schema 以 optional fields 向後相容；現有 project 使用舊 schema 時，load/verify 仍可運作。

## 高風險分析

### Migration

不改 `.devweave` state/evidence/event ledger schema；project command metadata 為 optional，現有 commands 可被原樣讀取。Extension snapshot 新欄位皆由 source reader 產生，舊 Webview payload 以 defaults 相容。若 command profile 要採 selective behavior，必須由同一 Work Item 透過 CLI 更新 commands/profiles，不手改 JSON。

### Rollback

Extension bootstrap 使用既有 prepare/revalidate/install/rollback；path-kind mismatch 只 report conflict。Generated `dist` 可重建，current/retained VSIX 不自動刪除。Selective verification 若 selection logic 失敗，fallback 為完整 profile 或 fail closed，不能默默省略 high-required command。

### Security

不新增 Extension process/network/Git/Codex API。`inspectPath` 僅 workspace-relative；command metadata paths 不允許 absolute/traversal；engine 執行既有 argv array，不引入 shell string。Release orchestrator 使用 Node `execFile` 的 argv，不使用 shell interpolation；candidate path 由 orchestrator 在 extension root 下產生，不接受任意外部 promotion target；verifier 只讀 `--artifact` 指定檔案。Metrics 不保存 prompt secrets/raw token，usage 欄位只接受 numbers/null/status enum；raw logs 維持既有 bounds。

### Compatibility

保留 existing `FileSystemPort` behavior through test adapters and update all adapters in one change；保留 model fields and add optional/derived fields。Legacy commands without metadata run as before。`npm run package` 維持既有公開入口，但 package builder 的直接呼叫改由 orchestrator 統一；verifier 的新 `--artifact` 為必填，避免舊的無參數隱式 current 語意。VS Code 1.131.0 is the accepted smoke baseline；other versions require explicit baseline update。POSIX/Windows hook and existing no-direct-write Extension boundary unchanged。

### Performance

Summary-first removes unselected artifact/evidence/event reads；selected detail remains bounded。Independent root/project/Wiki reads remain parallel；`inspectPath` calls are cached per refresh。Verification profile selection records skipped reasons and never removes dependencies/high commands。Release orchestration adds one candidate write and one verifier read before the single promotion；只在 release-only package command 執行，不增加 network/background work。Metrics capture timing without adding network or background work。

### Build Provenance Seam interface

`ReleaseOrchestrator` 是 production release flow 的深模組；caller 只需提供 package root 與 version-derived current path，模組隱藏 candidate naming、builder/verifier argv、same-directory promotion、cleanup 與 error propagation。其外部 Interface 的不變量如下：

```text
runReleaseTransaction({
  extensionRoot: string,
  currentArtifact: string,
  buildCandidate: (candidatePath: string) => Promise<void>,
  verifyCandidate: (candidatePath: string) => Promise<void>,
  promote: (candidatePath: string, currentPath: string) => Promise<void>,
  cleanup: (candidatePath: string) => Promise<void>
}): Promise<{ currentArtifact: string }>
```

Production adapters are the Node child-process adapter (`execFile` with explicit argv) for builder/verifier and the same-directory filesystem rename adapter for promotion. Tests inject in-process adapters for build, verify, promote and cleanup; the transaction seam is therefore real across production and test implementations. `verifyCandidate` failure never calls `promote`; `promote` failure propagates without claiming success; cleanup is attempted in `finally` and cleanup failure is attached to the original failure. The current and retained artifacts are outside the transaction's delete set.

## 設計決策

## DEC-001: 採用 typed path inspection seam

- Requirements: REQ-001, NFR-001, NFR-002
- Decision: 在既有 `FileSystemPort` 增加 `inspectPath()`，由 VS Code adapter 以 `FileType` 映射 `missing/file/directory/symlink/other`；bootstrap installer 保留既有可回復交易邊界。
- Rationale: `exists()` 無法辨識「預期目錄卻是檔案」與 symlink/其他類型，typed seam 可讓 Snapshot 與 bootstrap completeness 共享明確判斷，且不把 VS Code API 洩漏進 core。
- Consequences: 需要更新所有 test adapter 與 path-kind regression tests；讀取多一次 bounded stat，但同一 refresh 會快取結果。

## DEC-002: summary-first 與 projection-only authority

- Requirements: REQ-002, REQ-003, REQ-004, REQ-009
- Decision: Workspace Snapshot 先讀 bounded summary；只對選定 Work Item 讀 bounded detail，Wiki 顯示 source/hash/truncation/parse diagnostics。Extension projection 永遠標記 `authoritative=false`，engine observation 缺失時不得推導成通過。
- Rationale: 降低初始 I/O、Token 與 UI 延遲，同時保留使用者追查細節的路徑；避免把檔案投影誤當作 DevWeave gate 真相。
- Consequences: model/read protocol 需支援 detail loading 與 unavailable 狀態；舊 UI 必須相容新增欄位，測試需覆蓋 summary/detail 與 malformed Wiki。

## DEC-003: clean build provenance 與 pinned smoke runtime

- Requirements: REQ-005, REQ-006, NFR-002
- Decision: package 先清理並產生帶 `sourceGitHead`、file count、canonical manifest hash 的 dist，再由 candidate builder 建立 VSIX；release orchestrator 驗證 candidate 後才 promotion；smoke 固定 accepted VS Code `1.131.0` 與已快取 runtime，缺失時失敗，不使用 current/fallback runtime。
- Rationale: 讓封裝物可追溯、可重現，並使 smoke 結果能對應明確 runtime，而不是依賴開發機偶然版本。
- Consequences: 本機未準備 accepted runtime 時 smoke 會明確失敗；更新版本必須同步 baseline、manifest、candidate/current artifact 與 acceptance evidence。

## DEC-004: optional command metadata 與 selective verification

- Requirements: REQ-007, NFR-003
- Decision: command entry 增加可選 `affected_paths`、`writes`、`outputs`、`release_only`；CLI `verify --profile --path` 依 metadata 選擇命令並補 dependency closure，high profile 維持完整集合；未標註 metadata 的 legacy command 保留既有語意。
- Rationale: 將工具呼叫與變更範圍建立可驗證關聯，減少低/標準驗證的不必要呼叫，同時保留高風險完整覆蓋與向後相容。
- Consequences: project validation、CLI schema、batch output 與 tests 必須同步；metadata 不正確會導致 selection 偏差，因此所有路徑/enum 以 fail-closed 驗證。

## DEC-005: metrics 擴充既有 evidence

- Requirements: REQ-008, NFR-003
- Decision: 將 verification selection/skipped/cache 狀態與 bounded context/tool/usage metrics 放入既有 evidence payload；unknown token/cost 使用 `unavailable`，不另建 ledger、不估算不存在的數值。
- Rationale: 維持單一可追溯 evidence source，能比較成功率、完整性、Token、延遲與成本，又不洩漏 prompt 或造成第二套狀態。
- Consequences: evidence parser/projection 必須接受舊 payload；caller 未提供 usage 時仍能記錄 duration/selection，但報表必須清楚標示 unavailable。

## DEC-006: 沿用單一高風險 reviewer 與 knowledge promotion

- Requirements: REQ-010, NFR-001, NFR-002
- Decision: 高風險 G3 只由 DevWeave router 啟動一個 isolated read-only Independent Review Agent，並以既有 `review record` 記錄固定結果；可重用知識於 verification 依 knowledge plan promote，最多五頁並同步 index/log。
- Rationale: 避免 Extension、Python engine、外部 prototype 各自產生 reviewer 或 ledger；將安全、範圍與知識閉環集中在既有 gate。
- Consequences: reviewer 只接收 approved artifacts/diff/evidence，不可修改或 delegate；任何 source fingerprint 變更會使 review stale，需重新取得 G3 readiness。

## DEC-007: candidate-first release transaction 與 atomic promotion

- Requirements: REQ-005, NFR-001, NFR-002
- Decision: 新增獨立 `ReleaseOrchestrator` module；`package-vsix.mjs` 只寫入 extension root 同目錄唯一 candidate，`verify-package.mjs` 以必填 `--artifact` 驗證指定檔案，orchestrator 只有 verifier 成功後才以同目錄 rename promotion current。任何 verify/promotion/cleanup failure 都保留 current/retained artifact，candidate 由 finally best-effort 清理。
- Rationale: 將封裝、驗證與發布責任分開，讓 failure path 的「不覆寫 current」成為單一 deep seam 的可測試不變量；同目錄候選避免跨磁碟 copy/delete 破壞 atomic promotion。
- Rejected: 直接讓 `package-vsix.mjs` 同時負責 child process、verifier 與 promotion；這會使封裝器成為 shallow/pass-through release controller，且難以在 builder/verifier failure 下隔離 current artifact。
- Consequences: package script 增加 orchestrator 入口；verifier 的無參數呼叫改為 fail closed；新增 transaction seam 測試與 package contract 測試；硬中斷可能留下可辨識 candidate，但 current/retained artifact 不受影響。
-->
