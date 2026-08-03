# 系統設計：建立 DevWeave Control Center VS Code Extension

<!-- DEVWEAVE:artifact=design version=1 work=20260803-090218-feature-devweave-control-center-vs-code-extensio -->

## 設計摘要

新增一個通用、desktop-first 的 VS Code Extension，作為 DevWeave 的唯讀 Control Center 與 Codex Chat prompt composer。Extension 只透過 VS Code workspace file API 讀取 repository snapshot，將既有 Python engine 的狀態投影成 dashboard、TreeView、Wiki view、artifact trace 與 action preview；所有會改變 repository 或 DevWeave state 的操作只寫入 clipboard，由使用者在 Codex Chat 送出。

Extension 不執行 Python、shell、Codex agent API 或任何檔案寫入，不複製 engine policy，也不建立第二套 router。既有 `devweave.py`、`devweave_core.py`、`knowledge_core.py`、`guard.py`、JSON/JSONL ledger、Wiki contract 與三道人工作業 gate 保持 authoritative。

主要 module 與 seam：

- `WorkspaceSnapshotReader`：讀取與辨識 workspace/repository、project、work item、artifact、evidence、baseline、Wiki、hook 與 skill 檔案。
- `DevWeaveProjection`：把 raw files 轉成 UI 可用的 typed snapshot；projection 是 lossy/read-only，不重建 engine fingerprint。
- `PromptComposer`：唯一深 module，隱藏 public `$devweave` verb、machine CLI argv、work/gate/path/warning 組合與 prompt sanitization。
- `HostController`：協調 snapshot、TreeView、Webview message、file open 與 clipboard copy。
- `ClipboardAdapter`：唯一允許的 mutation-like side effect，只使用 VS Code clipboard API。

## 選項比較

### Option A：Extension 內重寫 DevWeave engine

此方案會在 TypeScript 重新實作 state transition、fingerprint、Wiki lint、scope guard 與 gate validation。雖然 UI 可直接取得完整模型，但會產生第二份 router，且 Python engine 與 Extension 很容易 drift；不符合 REQ-004、NFR-001 與 NFR-004。

### Option B：Extension 直接啟動 Python CLI

此方案可取得 engine 的 authoritative output，但會讓 Extension 具備 process execution 與潛在 mutation 能力，並依賴 Python、shell、Codex session 與本機環境；這會違反 REQ-005、REQ-006 的 copy-only boundary。

### Option C：唯讀 workspace projection＋prompt composer（採用）

Extension 只讀取檔案並顯示 snapshot，mutation 由既有 DevWeave public/machine command 透過 Codex Chat 執行。這讓 Python engine、hook、人工 gate 保持唯一 authority；`PromptComposer` 提供小 interface 但封裝完整 command/prompt policy，具有足夠 depth、testability、leverage 與 locality。

## 介面與資料流

### Extension Host interface

```ts
interface WorkspaceSnapshotReader {
  readWorkspace(): Promise<WorkspaceSnapshot>;
}

interface PromptComposer {
  compose(intent: ActionIntent, snapshot: WorkspaceSnapshot): PromptBundle;
}

interface ClipboardAdapter {
  copy(text: string): Promise<void>;
}
```

`ActionIntent` 使用 discriminated union，覆蓋 project、lifecycle、governance、knowledge、task、evidence、verification、waiver、approve、revise 與 close；UI 不直接建立 command string。

```ts
type PromptBundle = {
  chatText: string;
  machineCommand?: string;
  workId?: string;
  gate?: "scope" | "build" | "acceptance";
  targetPaths: string[];
  warnings: string[];
  mutation: boolean;
};
```

### Snapshot data flow

1. Resolve active workspace folder containing `.devweave/project.json`; multi-root workspace 必須明確選擇 repository。
2. 以 `workspace.fs` 讀取 project config、hook/skill presence、work-item directories、state、五份 Markdown、evidence JSON、events、baseline 與 Wiki page files。
3. 以 bounded text reads、UTF-8 decode、minimal frontmatter parser 與 schema guards 建立 `WorkspaceSnapshot`。
4. 將 `managed`、schema、parse error、missing file、Wiki health、work selection、phase/gate、task/evidence、knowledge 與 freshness metadata 傳給 TreeView/Webview。
5. Webview 只傳回 `selectWork`、`openFile`、`refresh`、`previewAction`、`copyAction`；Host 重新以 snapshot 驗證 intent，再由 PromptComposer 產生 PromptBundle。
6. `copyAction` 經 ClipboardAdapter 寫入 clipboard；Host 顯示 success/error notification 與 accessible status。沒有 command execution path。

### UI shell

- Activity Bar `DevWeave` container：TreeView 顯示 repository、active work items、closed work items、phase/gate/risk/blocker/knowledge badges。
- Dashboard Webview Panel：Overview、three-gate track、next safe action、snapshot provenance 與 refresh warning。
- Work detail：Overview、Requirements、Design、Implementation、Verification、Acceptance、Wiki 與 Audit sections。
- Action Preview：顯示 chat text、machine command、target paths、expected effect、gate warning 與 copy-only notice。
- File opener：只開啟 artifact、Wiki、baseline 或 evidence/raw-log path；不以 custom editor 取代標準 Markdown editor。

### Prompt policy

- `new/feature/refactor/bug/next/status/revise/approve` 優先使用既有 public `$devweave` chat surface。
- `init`、`doctor`、`project`、`instructions`、`validate`、`bind`、risk/scope/baseline、knowledge、task、evidence、verify、waiver、close 與 command configuration 產生 deterministic machine CLI preview，包在要求 Codex 執行的 Traditional Chinese prompt 內。
- command preview 使用 repository-relative paths、work ID 與 canonical argument ordering；不得加入 shell operators、absolute paths、raw verification logs 或 credential-like values。
- approval、waiver、revise、close 與 G3 knowledge/baseline actions 使用高風險 warning；複製不代表已核准或已執行。

### State and compatibility

Extension 不新增或修改 DevWeave state。所有 approval、task、evidence、fingerprint、revision 與 close 仍由 engine 寫入既有 ledger。若 `schema_version` 非 1、JSON malformed、artifact/Wiki parse failure 或 project invalid，projection 進入 read-only diagnostic state；status/doctor prompt 仍可產生，但 mutation prompt 會被停用並顯示原因。

File watchers 監看 `.devweave/project.json`、`.devweave/work-items/**`、`.devweave/baseline/**`、`wiki/**`、`.codex/hooks.json` 與 DevWeave skill metadata，使用 debounce 後重新讀 snapshot。UI 顯示 `filesystem snapshot`、`last engine-observed state`、captured time 與「需在 Codex 執行 status/validate」提示，不自行計算 approval fingerprint。

### Visual and accessibility design

Webview 使用 vanilla DOM/CSS、VS Code `--vscode-*` theme tokens、8px spacing grid、10–14px rounded grouped cards、semantic status icon+text、visible focus ring、ARIA labels、keyboard navigation、high-contrast rules 與 reduced-motion media query。只在工具列/浮動控制使用輕微 transparency；主要內容維持不透明與高可讀性。使用 Codicons，不引入 Apple proprietary assets 或 SF Symbols。

## 失敗模式與回復

- **No workspace / multiple repositories**：顯示 repository picker 或 welcome state；不猜選、不產生帶錯誤 root 的 mutation prompt。
- **Uninitialized / managed false**：顯示明確啟用與 initialization prompt；不自動建立 `.devweave` 或 project state。
- **Malformed/unsupported project/state/artifact**：顯示檔案、parse error 與 read-only fallback；禁止修復、覆寫或推測缺失 state。
- **Missing hook/skill/Wiki compatibility warning**：doctor card 顯示 warning，僅提供診斷 prompt；不改 hook、Wiki 或 skill。
- **Multiple eligible work items**：要求使用者在 TreeView 選擇 work ID；PromptComposer 不接受 implicit selection。
- **Changed source after engine observation**：標記 possible stale，要求使用者在 Codex 執行 status/validate；不自行更新 gate/evidence。
- **Clipboard failure**：保留 preview、顯示錯誤並提供可選取的 read-only text area；不嘗試使用 terminal 或檔案暫存。
- **Large file/raw log**：預設只顯示 raw-log path 與 metadata，超過 bounded read limit 顯示 truncated；不自動把 raw log 放入 clipboard/Webview。
- **Webview crash/message mismatch**：Host 保留 snapshot、重新建立 panel；未知 message type 直接忽略並寫入 OutputChannel，不執行任何 side effect。

Rollback 是移除/停用 `vscode-extension/` 或回到上一個 Extension package；不需要資料 migration，也不改動既有 DevWeave engine/state。若未來需要新增 engine contract，必須另開 work item。

## 高風險分析

- **Migration**：不適用。這是 additive Extension subtree，沒有既有 state migration、schema migration 或 ledger rewrite；schema version 1 僅做 read compatibility check。
- **Rollback**：Extension 可被停用/移除，repository 的 Python engine、hook、state、Wiki、baseline 與 product source 不依賴 Extension runtime；package build 失敗不會改變 repository behavior。
- **Security**：禁止 `child_process`、shell、file writes、Codex private API 與外部 network；Webview 使用 strict CSP、nonce、local resources；不讀取/複製 raw log content，不把 secrets 放入 prompt；所有 user-controlled path 只允許 workspace-relative URI。
- **Compatibility**：不改既有 CLI/JSON contract；project `schema_version` 不支援時 fail closed；現有 Python unittest/guard/knowledge tests 必須保持通過；Extension 使用 standard VS Code APIs，無 React runtime。
- **Performance**：初始讀取只掃描必要 metadata 與 work artifacts，raw logs lazy-load；單檔 bounded read、Wiki directory lazy enumeration、watcher debounce；大 repository 顯示 partial/refresh state 而不阻塞 UI。
- **Observability**：UI 顯示 snapshot timestamp、source category、parse/compatibility warnings；Extension OutputChannel 記錄非敏感讀取與 Webview protocol error；不新增 production instrumentation 或 remote telemetry。

## 設計決策

## DEC-001: 保留 Python engine 並建立 Extension adapter seam

- Requirements: REQ-004, NFR-001, NFR-004
- Decision: Extension 只實作 workspace projection 與 PromptComposer，不重寫或直接啟動 Python engine。
- Rationale: 保持單一 DevWeave authority、降低 contract drift，並讓 UI/test 以小 interface 隔離複雜度。
- Consequences: UI 只能顯示 disk snapshot；需明確告知使用者在 Codex refresh/execute，不能提供即時 engine sync。

## DEC-002: 使用 VS Code workspace file API 建立 read-only snapshot

- Requirements: REQ-001, REQ-006, REQ-010, NFR-001
- Decision: 所有 repository access 透過 `WorkspaceSnapshotReader` 與 workspace file API，不使用 Node fs、child process 或 shell。
- Rationale: 支援 workspace/remote abstraction，且以 interface-level safety 強制 no-write/no-execution boundary。
- Consequences: 需要處理檔案不存在、編碼、large file、parse failure 與 snapshot freshness；不會取得 engine 重新 sync 後的 authoritative status。

## DEC-003: TreeView＋vanilla Webview Panel

- Requirements: REQ-002, REQ-003, REQ-007, NFR-002, NFR-004
- Decision: Sidebar 使用原生 TreeView，Dashboard/detail 使用單一 vanilla Webview Panel，不引入 React 或 custom editor。
- Rationale: TreeView 適合 hierarchy；Webview 只承擔 cards、gate track、trace view、preview 等原生 API 無法表達的內容；減少 runtime/dependency surface。
- Consequences: 需自行維護 Webview DOM、CSP、message protocol、ARIA 與 responsive CSS；標準 Markdown 仍由 VS Code editor 開啟。

## DEC-004: 單一 PromptComposer 與 copy-only action preview

- Requirements: REQ-004, REQ-005, REQ-009, NFR-003
- Decision: 所有 action intent 先通過 PromptComposer 產生 PromptBundle，再由 ClipboardAdapter 複製；UI 不直接拼命令或執行。
- Rationale: 將 command ordering、path safety、warning、public/machine route 與 sanitization 集中在一個 deep module，便於 snapshot tests。
- Consequences: 使用者必須在 Codex Chat 手動送出；UI 需提供清楚的 preview、copied status 與 refresh guidance。

## DEC-005: Fail-closed contract projection

- Requirements: REQ-001, REQ-006, REQ-010, NFR-001
- Decision: unsupported schema、malformed source、invalid path、missing root 或未知 Webview message 都只產生 diagnostic/read-only state。
- Rationale: Extension 不能猜測或修復 engine-owned state；安全與相容性優先於部分可用性。
- Consequences: 部分 repository 可能只能看到 doctor/diagnostic prompt；使用者需由 DevWeave/Codex 修復後重新整理。

## DEC-006: Stage-oriented Apple-inspired information architecture

- Requirements: REQ-002, REQ-003, REQ-007, REQ-008, REQ-009, NFR-002
- Decision: 以 repository welcome、dashboard、work detail、Wiki workspace、verification/acceptance 與 action preview 組織 UX；以 VS Code theme tokens 實作 hierarchy、grouped cards、semantic status 與 accessibility。
- Rationale: 讓使用者先理解「目前在哪裡／下一步是什麼」，再進入 artifact/evidence detail；保持 Apple-inspired visual language 而不複製 Apple proprietary UI。
- Consequences: 需要完整 phase/gate projection 與 responsive/high-contrast UI test matrix。

## DEC-007: Vanilla TypeScript build with isolated verification

- Requirements: NFR-001, NFR-003, NFR-004
- Decision: 使用 TypeScript、vanilla Webview、esbuild 與 Node test runner/VS Code activation smoke tests；不引入 React、external network 或 runtime dependency。
- Rationale: 新增最小可維護 build surface，並使 parser/composer 可在無 Python、無 Codex、無 real repository write 的環境測試。
- Consequences: 必須新增 extension-specific verification commands，並在 G3 同時保留 Python suite 與 package checks。

## DEC-008: Additive architecture baseline update

- Requirements: NFR-001, NFR-004
- Decision: G3 verification 階段宣告並更新 `.devweave/baseline/architecture.md`，記錄 Extension 與 Python engine、Codex Chat、hook、Wiki、state 的 accepted boundary；不更新 Wiki，因本 work item 不改變既有 Wiki source-bound pages。
- Rationale: Extension 是新的 accepted system boundary，architecture baseline 必須可追溯；Wiki promotion 僅處理真正 affected pages。
- Consequences: baseline update 只能在 verification/acceptance 依 DevWeave plan 執行，並納入 G3 fingerprint。
