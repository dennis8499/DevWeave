# 執行計畫：DevWeave 0.2.1 current-version-only release contract

<!-- DEVWEAVE:artifact=plan version=1 work=20260805-120943-feature-devweave-0-2-1-current-version-only-rele -->
<!-- Task 定義在 G2 後保持不變；執行狀態由 state.json 管理。 -->

## 工作分解

## TASK-001: 固定 current-only package policy regression
- Traces: REQ-001, REQ-002, AC-001, AC-002, DEC-001, DEC-002
- Inputs: 現有 failing `package-version.test.ts`、`verify-package.mjs` 與 package version 0.2.1。
- Output: Unit test不依賴prebuilt VSIX並拒絕legacy policy；verifier只讀current VSIX，保留完整archive/bootstrap checks並輸出current SHA-256。
- Verification: 先確認既有test因legacy ENOENT為red；修改後執行targeted package-version test，再以暫時建置執行package verifier。
- Dependencies: none

## TASK-002: 統一current-only公開文案與contract test
- Traces: REQ-003, REQ-005, NFR-003, AC-004, AC-006, DEC-003, DEC-004, DEC-005
- Inputs: README、使用手冊、Extension README、內嵌Help及現有repository contract test surface。
- Output: Source-facing public copy一致描述唯一0.2.1、實測認證stack、無legacy downgrade與data-preserving incident response；新增bounded regression防止規範文字回歸。
- Verification: 先新增會對現行legacy文案失敗的targeted repository contract test；修改文案後targeted test與Extension Help contract通過。
- Dependencies: TASK-001

## TASK-003: 鎖定既有公開介面與安全邊界
- Traces: REQ-004, NFR-002, AC-005, DEC-002, DEC-003
- Inputs: TASK-001／002結果與既有Python／Extension contract suites。
- Output: 證明chat/CLI/schema/Gate/Hook/Wiki lifecycle、五個command IDs、bootstrap destinations/policies、CSP與no-process/network boundaries沒有產品行為變更。
- Verification: 執行repository contract、Extension security／package-version／webview contract targeted tests與typecheck。
- Dependencies: TASK-001, TASK-002

## TASK-004: 產生可重現的0.2.1 release candidate
- Traces: REQ-001, REQ-002, NFR-001, AC-002, AC-003, DEC-001, DEC-002
- Inputs: TASK-001至003穩定source與clean build inputs。
- Output: 唯一`devweave-control-center-0.2.1.vsix`；兩次build SHA-256一致；`debug.log`及非發布檔清除。
- Verification: 連續兩次`npm.cmd run package`並比較size／SHA-256；verifier回報58 bootstrap files、118 VSIX entries及current hash，且manifest包含必要的`native-question-contract.md`。
- Dependencies: TASK-001, TASK-002, TASK-003

## TASK-005: 完成current-version驗收與G3交接
- Traces: REQ-004, REQ-005, NFR-001, NFR-002, AC-005, AC-006, AC-007, AC-008, DEC-003, DEC-004, DEC-005
- Inputs: TASK-004唯一RC artifact與認證環境。
- Output: 自動化full-suite與current VSIX install/reinstall/disable/uninstall、Control Center walkthrough、offline/runtime safety及symlink補驗結果；所有evidence可交由G3 reconciliation。
- Verification: 執行configured high-risk commands、manual current-version lifecycle與bounded text audit；任何failed／stale／unverified skip使task blocked而非waived。
- Dependencies: TASK-004

## 驗證策略

- Targeted red/green：package-version test與新增current-only repository contract test。
- Extension regression：73 unit tests、typecheck、production package、VS Code Extension Host smoke。
- Python regression：98-test full suite及repository contract；symlink containment在同build具權限環境補跑。
- Determinism：同HEAD連續兩次package的bytes／SHA-256一致，release evidence綁定final hash。
- Manual acceptance：0.2.1 GUI／CLI install、reinstall、disable、uninstall；fresh/evolved/conflict/failure/multi-work walkthrough；workspace before/after hashes不變。
- Security／compatibility：current verifier仍驗path/hash/manifest/archive，Hook process/policy分離、CSP、no process/shell/network、public command IDs與schema不變。
- G3：完整diff、scope、baseline、Knowledge Review/promote、Wiki seals、zero-defect matrix及exactly one high-risk Independent Review；任何source變動後完整重跑。

## 基線更新計畫

- Verification 更新 `.devweave/baseline/product.md`：唯一0.2.1交付、認證stack與無legacy rollback capability。
- Verification 更新 `.devweave/baseline/architecture.md`：package verifier只驗current artifact，其他Extension/runtime seams不變。
- Verification 更新 `.devweave/baseline/quality.md`：98-test Python baseline、73 Extension tests、current-only package與deterministic hash bar。
- Knowledge Review採`promote`，refresh `wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`，同步`wiki/index.md`並append一筆`wiki/log.md`後seal；不改寫歷史log。
