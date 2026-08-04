# 系統設計：修正 G1/G2 問答、Wiki 初始化與 Extension bundle 相容性

<!-- DEVWEAVE:artifact=design version=1 work=20260804-183511-feature-g1-g2-wiki-extension-bundle -->

## 設計摘要

選定方案由三個深模組與一個 router contract 組成：

1. DevWeave router/phase guidance 定義 host-native-first 的 material decision interface；native facility 不可用時，由同一份決策資料格式化成 structured fallback。它只改變詢問介面，不新增 engine state、CLI、JSON schema、question ledger 或 VS Code UI。
2. Python knowledge module 先以 reserved-starter preflight 判斷 Wiki compatibility，再在 `init_project()` 內二次檢查並建立 skeleton；非保留內容採用且不覆寫，保留 path 的型別/frontmatter/path conflict fail closed。
3. Extension bootstrap module 將 manifest file entry 的 `existingPolicy` 與 `compatibility` kind 正規化，透過單一 compatibility validator seam 同時服務 `BootstrapInstaller` 與 `WorkspaceSnapshotReader`。合法 evolved governance/Wiki bytes 是 adopted；只有 missing 才進入 write set。

不變量：G1/G2/G3 與 explicit `$devweave approve` 不變；Wiki 在 verification 前唯讀；Extension 不執行 engine/shell/network；既有 bytes 不覆寫；manifest source integrity、path containment、symlink/type checks 在 semantic adoption 前完成。

## 選項比較

### Option comparison 1：問答介面放在 router host contract

- Engine question state/CLI：可保存 pending question，但會新增 lifecycle/schema/ledger，且無法保證 Chat 與 CLI 的共同 UI。
- Router host-native-first：保留既有 artifact/Gate contract，能力由 host detection 決定，無 native 時輸出同格式 fallback。
- 選定後者，因為它最符合使用者需求且維持 engine 單一權威；代價是 native API availability 需 capability-detect，不能測試未公開 host API 的實際 UI。

### Option comparison 2：Wiki 採 reserved-starter compatibility 加雙階段 preflight

- 嚴格要求非空 Wiki 必須已有合法 index：會阻擋既有 notes-only/custom Wiki，與「保留自訂內容並補齊 starter」目標衝突。
- 全面接受任意不同內容：會讓錯誤的 index/overview/log 或 starter directory 延後到寫入階段才失敗。
- 選定只檢查 reserved starter files/directories，並在 lock 前與 lock 內各預檢；既有非保留內容不干涉，保留 path type/frontmatter conflict 在任何 durable control write 前回報。

### Option comparison 3：Manifest 宣告 explicit policy 與 compatibility kind

- 只依 destination 推斷：介面較小，但新增檔案容易意外進入寬鬆 adoption，規則散落在 caller。
- 所有檔案 exact：安全但無法區分 bootstrap template 與合法 evolved project/baseline/Wiki。
- 選定每個 file entry 明確宣告 `existingPolicy: "exact" | "adopt-compatible"`，compatible entry 再宣告固定 `compatibility` kind。舊 manifest 缺欄位正規化為 exact，維持向後相容與 fail-closed。

### Option comparison 4：共用 deep validator module 作為外部 seam

- Installer 與 snapshot 各自實作 parser：短期較快，但同一 workspace 可能得到不同 completeness 結果，造成 locality 與測試重複。
- 將 validator 放入新的共享 module，提供小而穩定的 `validateExistingBootstrapContent(file, bytes)` interface；installer/snapshot 只負責 adapter、I/O 與結果投影。
- 選定共享 seam。其 implementation 隱藏 UTF-8/JSON/frontmatter/heading 規則，兩個 caller 與 unit tests 使用同一 interface，形成較深的 module。

### Option comparison 5：Compatibility 只開放七個明確資料 contract

- `devweave-project-v1`：UTF-8 JSON object，schema 1、managed true、合法 locale/commands/verification/evidence/knowledge contract。
- `baseline-product-v1`、`baseline-architecture-v1`、`baseline-quality-v1`：保留對應 title 與 required headings，body/provenance 可演進。
- `wiki-index-v1`、`wiki-overview-v1`、`wiki-log-v1`：regular file、可解析 frontmatter 且 `type` 符合；日期/body 可不同。
- AGENTS、skills、hook、lock 與其他 bundle files 維持 exact，避免把 executable/policy drift 靜默採用。

## 介面與資料流

### Host question interface

概念上的決策資料為 `question + options[{label, description}] + recommended-first + allowCustom`。router 每次只送出一題；native host 可用時直接交給 host question facility，否則以相同排序輸出 numbered structured fallback。回答正常化後回流 G1 `brief.md`/`requirements.md` 或 G2 `design.md`/`plan.md`；不產生 pending state。

### Wiki data flow

```text
derive existing/default project knowledge root
  -> inspect_wiki (no write)
  -> acquire project lock and inspect_wiki again
  -> bootstrap_wiki reserved skeleton (no overwrite)
  -> create/upgrade project, baseline, cache and work-item directories
  -> load_project and return
```

`inspect_wiki` 對 missing/empty/custom-only root 回傳 compatible；對 reserved path 只接受 regular file/directory 與正確 frontmatter/type。`bootstrap_wiki` 保留既有內容，只 exclusive-create 缺少 starter。`knowledge bootstrap` 仍獨立評估 readiness 並 create/resume/already-complete feature work。

### Extension manifest and validator interface

```ts
type BootstrapExistingPolicy = "exact" | "adopt-compatible";
type BootstrapCompatibilityKind =
  | "devweave-project-v1"
  | "baseline-product-v1" | "baseline-architecture-v1" | "baseline-quality-v1"
  | "wiki-index-v1" | "wiki-overview-v1" | "wiki-log-v1";

interface BootstrapBundleFile {
  source: string;
  destination: string;
  transform: "copy" | "date";
  byteLength: number;
  sha256: string;
  existingPolicy?: BootstrapExistingPolicy;
  compatibility?: BootstrapCompatibilityKind;
}
```

Normalized rules: absent policy means `exact`; `adopt-compatible` requires a known kind; `exact` rejects a compatibility kind. Resource bytes are integrity-checked first. Existing same bytes are adopted; different bytes use the shared validator; invalid content is conflict; absent files form the only write set. Snapshot passes the same normalized file contract and validator, so `complete`, installer `inspect` and installer `install` agree.

### State and observability

- Native unavailable: no state change; structured fallback is the only degradation.
- Wiki conflict: `knowledge_conflict` includes exact reserved paths/reasons; existing Wiki and control files remain unchanged.
- Extension inspection/report: `adopted`, `missing`, `conflicts`, `errors`, `created`, `rolledBack` remain the observable result; semantic adoption appears in `adopted`, not conflict.
- Existing exact controls continue to surface drift; UI only removes false conflict for the seven compatible contracts.

## 失敗模式與回復

- Host question facility unavailable or malformed: fall back to structured one-question rendering; do not guess an answer or advance the phase.
- Wiki root outside repository, root/reserved path wrong type, symlink escape, invalid frontmatter or duplicate/invalid reserved target: fail before starter/control writes and preserve user bytes.
- `init_project()` second preflight detects a race: raise the same `knowledge_conflict`; no project/baseline/cache/work-item durable write is attempted by that init path.
- Manifest source missing, SHA/length mismatch, malformed policy/kind, traversal, parent type/symlink issue or validator failure: installer fails closed. Existing files are never overwritten.
- Write failure after some missing directories/files: retain existing rollback behavior and delete only paths created by this invocation; semantic adopted files are never rollback targets.
- Old manifest without policy fields: normalize to exact, so old behavior is safe but may still report evolved files as conflicts until a new bundle is used.

## 高風險分析

- Migration：不升級 engine ledger/schema；manifest schema 1 保持相容，新增欄位 optional and build-generated。既有 workspace 不自動覆寫 exact policy/skill files。
- Rollback：extension write set remains missing-only; failed writes rollback invocation-created paths. Python init uses preflight before control creation; Wiki starter creation is no-overwrite and conflict-safe.
- Security：verify bundle source integrity before semantic validation; normalize relative paths; reject symlink/parent/type/traversal; exact executable/policy controls remain exact; validators are local and dependency-free.
- Compatibility：project/baseline/Wiki validators are strict on identity and structure, permissive only on evolved body/provenance/date. Unknown policy kinds fail before writes.
- Performance：validators parse only existing manifest destinations already read by snapshot/installer; no repository-wide scan or network. Complexity is linear in the target file bytes.
- Observability：keep existing JSON report, output log and snapshot fields; add reasons identifying semantic mismatch versus exact drift without adding telemetry or a new state machine.

## 設計決策

<!--
Example decision heading and fields are retained only as a comment template.
-->

## DEC-001: Host-native-first material decision contract

- Requirements: REQ-001, REQ-002, REQ-003, NFR-002
- Decision: Router uses host-native question facility when exposed; otherwise the same single-question structured fallback; answers return to existing phase artifacts and `$devweave approve` remains unchanged.
- Rationale: Satisfies Chat/CLI preference without inventing an undocumented common API or engine question state.
- Consequences: Better option/recommendation/custom-answer UX; actual native UI requires host-level acceptance, while fallback remains repository-testable.

## DEC-002: Reserved Wiki preflight before control writes

- Requirements: REQ-004, REQ-005, REQ-006, NFR-002
- Decision: Allow arbitrary non-reserved Wiki content, validate reserved starter targets, preflight before and inside the project lock, and keep `knowledge bootstrap` separate from skeleton init.
- Rationale: Fixes both over-strict compatibility and partial initialization while preserving no-overwrite lifecycle boundaries.
- Consequences: Existing notes-only Wiki becomes adoptable; malformed reserved files remain blocking; a second read protects the write path from races.

## DEC-003: Explicit manifest adoption contract

- Requirements: REQ-007, REQ-008, NFR-001
- Decision: Add optional `existingPolicy` and `compatibility` fields, normalize absent policy to exact, and require known compatibility kinds for adoption.
- Rationale: The explicit interface is safer and more local than destination heuristics, while schema-1 optionality preserves old bundles.
- Consequences: Build/package fixtures need declared policies; compatible governance content no longer produces false conflict; new compatible types require an explicit validator and tests.

## DEC-004: Shared compatibility validator seam

- Requirements: REQ-007, REQ-008, NFR-001
- Decision: Put destination-specific project/baseline/Wiki validators behind one deep module interface consumed by installer and snapshot adapters.
- Rationale: One implementation gives deterministic agreement and concentrates security/compatibility logic and tests at a single seam.
- Consequences: A new internal module is added; callers remain small, and validator behavior is independently testable through bytes plus manifest metadata.

## DEC-005: Fail-closed write and verification treatment

- Requirements: REQ-005, REQ-008, NFR-002
- Decision: Keep source integrity/path/type/symlink checks and missing-only writes; preserve rollback and exact policy for skills/hook/lock/AGENTS.
- Rationale: The requested adoption must not weaken bootstrap safety or silently accept executable/policy drift.
- Consequences: Some genuinely customized exact controls still require manual reconciliation; semantic adoption is limited to seven reviewed data contracts.
