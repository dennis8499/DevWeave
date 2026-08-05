# 功能驗收：DevWeave 0.2.1 current-version-only release contract

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260805-120943-feature-devweave-0-2-1-current-version-only-rele -->

## 驗證矩陣

Final Git HEAD：`ce6d661a21530b20e9f23c43b0117c0a25175690`  
Final source fingerprint：`c5895da4a8096f3885efb2221e7e7a5783a65e546d7f268e75df88c692185eba`  
Release artifact：`vscode-extension/devweave-control-center-0.2.1.vsix`，277,076 bytes，SHA-256 `3e23ba0a75b49dd4bfbb645d7296d68d5e882cf303078aeefdcf574c61530aba`。

| 驗收條件 | Task | Current evidence | 結果 |
| --- | --- | --- | --- |
| AC-001 舊版缺席 regression | TASK-001 | EVID-020 | Extension 73/73；package unit 不讀取 prebuilt legacy VSIX。通過。 |
| AC-002 0.2.1 package verification | TASK-001、TASK-004 | EVID-018、EVID-024 | 只驗證 0.2.1；58 個 bootstrap files、118 個 VSIX entries、metadata、manifest、required entries 與 source hashes 全數通過。 |
| AC-003 可重現 artifact | TASK-004 | EVID-018、EVID-024 | 同一 source 連續兩次皆為 277,076 bytes 與相同 SHA-256。通過。 |
| AC-004 Current-only 文案契約 | TASK-002 | EVID-023 | Repository contract 13/13；public docs、Help、baseline 與四頁 promoted Wiki 的 bounded audit 通過。 |
| AC-005 公開介面 regression | TASK-003、TASK-005 | EVID-019、EVID-020、EVID-021、EVID-022、EVID-025 | Typecheck、73 Extension tests、VS Code smoke、98 Python tests及 symlink containment 補驗通過。 |
| AC-006 Current version lifecycle | TASK-005 | EVID-021、EVID-026、EVID-027 | VS Code 1.131.0 activation／Activity Bar／commands，以及 GUI／CLI install、reinstall、disable、uninstall 與資料保留通過。 |
| AC-007 Release evidence currentness | TASK-004、TASK-005 | EVID-018、EVID-023～EVID-027 | 所有 release evidence 綁定 final source fingerprint；`debug.log` 不存在，artifact hash、doctor、scope、Wiki 與 diff audit一致。 |
| AC-008 零缺陷放行 | TASK-005 | EVID-020、EVID-022、EVID-023、EVID-025、EVID-027 | Current RC 零 assertion failure、零未補驗 skip、零 open defect；等待唯一一次 Independent Review 與人工 G3。 |

Task reconciliation：TASK-001～TASK-005 均 completed，machine task ledger 與核准 plan 完全一致。

## Profile 證據

- Feature acceptance：EVID-018、EVID-021、EVID-024、EVID-026、EVID-027。
- Feature regression：EVID-019、EVID-020、EVID-022、EVID-023、EVID-025。
- 五個 high-risk configured commands 在 final fingerprint 全部具有 current passing evidence：`extension-package`、`extension-smoke`、`extension-tests`、`extension-typecheck`、`unit-tests`。
- Python final run 為 98 tests、0 failure、1 privilege-only skip；該 exact containment test 已在同一 Windows build 以 UAC 隔離補跑 `Ran 1 ... OK`（EVID-025），因此沒有未補驗 skip。
- GUI 安裝、Control Center、停用與解除安裝由使用者明確確認；隔離 profile logs 與空的 post-uninstall extension registry 交叉驗證（EVID-026）。
- EVID-001～EVID-017 是 RC freeze 過程中因 source fingerprint 變化而保留的歷史／stale audit records；EVID-004 是 sandbox 阻擋 esbuild 父路徑讀取的環境型 attempt，已由非 sandbox current runs EVID-018 等取代。它們均不屬於 final release evidence set，也沒有 waiver。

## 基線更新

- `.devweave/baseline/product.md`：唯一 0.2.1 VSIX、限定認證 stack、data-preserving incident response 與無舊 binary rollback。
- `.devweave/baseline/architecture.md`：current-only verifier seam及58／118、metadata、manifest、source length/hash、artifact SHA-256 fail-closed contract。
- `.devweave/baseline/quality.md`：Python 98、Extension 73、symlink privilege補驗、current-only package與本次認證範圍。
- 三個變更路徑均已透過 machine `baseline --target` 宣告，沒有 undeclared 或 unchanged target。

## Wiki 知識提升

- Disposition：`promote`。Current-only packaging、certification、test counts 與 incident response 是可重用的 durable knowledge。
- Upsert／seal：`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`。
- Coupled pages：`wiki/index.md` 已同步；`wiki/log.md` 只追加一個包含本 Work Item ID 的 promote heading，沒有重寫歷史 body。
- Knowledge health：healthy；四個 affected pages 全部 current／sealed，無 placeholder、critical lint、pending refresh 或 warning。
- `debug.log`、VSIX 與 Extension public-copy／test paths 由上述四頁的整體 release／Extension 知識覆蓋，不採一檔一頁。

## 獨立 Review

本 Work Item 為 high risk；唯一一次 isolated、read-only Independent Review 已由 `independent-g3-review-agent` 完成並透過 machine-only `review record` 登錄為 EVID-028。

- Result：`passed`
- Severity：`none`
- Findings：`[]`
- Covers：AC-001～AC-008、TASK-001～TASK-005
- Source fingerprint：`c5895da4a8096f3885efb2221e7e7a5783a65e546d7f268e75df88c692185eba`
- Report SHA-256：`1dd0063cecf7d9bafc11890231eabce9e219c19c1e341114a0a5721c83f18518`

Reviewer 確認 scoped diff、baseline、Wiki、artifact 與 current evidence 符合 current-version-only 契約；58／118 integrity、public interface、append-only Wiki log、`debug.log` absence、scope containment、data-preserving lifecycle 與 elevated symlink補驗均無 advisory 或 critical finding。EVID-001～EVID-017 是已正確標為 stale 的歷史 RC attempts，不構成 current release defect。

## 殘餘風險

- 無產品已知缺陷、無 open defect、無 waiver。
- 認證僅涵蓋 Windows x64 build 10.0.26200／25H2、VS Code 1.131.0、Python 3.14.6、Git 2.51.0.windows.1 與目前 Codex host；其他環境不宣稱已完成本次認證。
- Git 未建立 commit，符合核准 artifacts 的非目標與 repository policy；release evidence 以既有 HEAD 加完整 dirty-source fingerprint 綁定，worktree 僅包含已核准 scope。發布前若另行 commit 或任何 byte 改變，必須重新凍結並完整重跑。
- 發布事故不提供舊 binary rollback；停止散布並停用或解除安裝 0.2.1，保留 `.devweave`、Wiki、workspace snapshot 與 logs，再以新版本修復。

## 驗收結論

Current-version-only 產品契約、最終 VSIX、公開文件、Help、accepted baseline、Codebase Wiki、自動化 Gate、symlink 補驗、GUI／CLI lifecycle 與 Independent Review 均已完成並綁定 final source fingerprint。Machine acceptance validation 通過後，即可提交產品負責人進行明確 G3／Go 簽署；在簽署前仍不得發布。
