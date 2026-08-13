# 工作摘要：強化 DevWeave VS Code Extension 治理、驗證與效率

<!-- DEVWEAVE:artifact=brief version=1 work=20260813-142228-feature-devweave-vs-code-extension kind=feature -->

## 問題與目標

本工作改善實際由 DevWeave VS Code Extension 初始化的專案內容與其驗證流程，目標使用者是需要在 Windows/VS Code 中以 Codex 執行 DevWeave SDLC 的開發者與維護者。

目前治理流程、安全邊界與 Wiki-first 方向正確，但 Extension projection、bootstrap path 判斷、package/smoke reproducibility、verification 選擇性、context/token 量測與文件基線仍有落差。成果必須在不增加 Extension 內部 Shell、網路、Codex API 或第二套 lifecycle 的前提下，提升準確度、可追溯性與效率。

成功訊號是：錯誤的 bootstrap filesystem type 不再被判為完成；Extension 不把非權威 snapshot 顯示成 engine Gate 通過；package 與 smoke 使用可重現且固定的版本；無關的低風險修改不再觸發昂貴封裝與完整 suite；context/tool/verification metrics 可透過既有 evidence 管線觀察；高風險完整驗證與單一獨立 reviewer 保持不變。

## 現況證據

### Wiki facts

- 已先讀 `wiki/index.md`，再讀 `wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`。
- 五頁 context 已透過 `knowledge context` 記錄；四頁的 stored source fingerprint stale，已先記錄 gap。Wiki 內容只作 context，不覆蓋目前 source 與 accepted baseline。
- Wiki 描述 Extension 為 filesystem snapshot、preview/copy handoff、無 runtime process/network/Git/Codex API；這與目前 source 一致。

### Source-backed facts

- `.devweave/project.json` managed=true；目前 profiles 對 low/standard 也包含 `extension-package`，standard/high 另包含 smoke 與所有 Python suites。
- `vscode-extension/src/model.ts` 將 WorkspaceSnapshot 標為 `authoritative: false`、`source: filesystem`；`snapshot.ts` 的 bootstrap completeness 目前以 `exists()` 作為第一層判斷。
- `vscode-extension/src/filesystem.ts` 的 `FileSystemPort` 沒有 typed path inspection；因此同名 file/directory mismatch 需要回歸測試與介面補強。
- Extension typecheck 通過，Extension unit tests 為 80 passed；Python 分拆 suite 為 104 passed、1 skipped。既有 README/Wiki/baseline 仍記錄較舊數字。
- `verify-package.mjs` 在目前工作樹因 generated manifest 0.3.1 與 package 0.2.3 不一致而失敗；保留的 0.2.3 VSIX 仍是 58 bootstrap files、119 entries。
- smoke 曾使用已安裝的 VS Code 1.133.0 fallback 並嘗試網路解析；accepted 文件宣稱的驗證版本為 1.131.0。

### Inferences

- 目前 extension snapshot 的 readiness 只能是預檢，不能單獨代表 CLI engine 的 Gate 狀態；UI 若顯示未區分的 ready，會造成精準度風險。
- 58-file bootstrap 與約 57 KB 的 G1 Wiki read set 是 context footprint proxy，不是精確 Codex token 數；中文 tokenizer 與 host usage 未被本專案控制。
- 封裝與 smoke 的 dependency、完整 suite 與資料讀取可透過 impact metadata 和 lazy detail read 降低無效 tool calls，但 high-risk coverage 不應降低。

### Unresolved gaps

- Codex host/API 是否提供 exact input/output/cached/cache-write token 與 cost 欄位未知；實作必須把 unavailable 與 proxy 明確分開。
- Wiki stale pages 需要在 verification 依實際 diff 決定 promote 或 no-update；本階段不直接改 Wiki。

## 範圍

範圍包含：

- Extension bootstrap completeness、filesystem path kind、WorkspaceSnapshot authority/readiness、Wiki parser/search provenance、lazy Work Item detail 與初始化後 verification readiness。
- build/package manifest provenance、乾淨 generated output、pinned smoke、VSIX verification 與 verification profile/command impact metadata。
- context/tool/verification/optional usage metrics，整合既有 evidence/event CLI，不新增 ledger。
- Extension unit/smoke tests、CLI/contract 驗證設定、README、Extension README、quality baseline 與 verification 時需要的 source-bound Wiki refresh。
- DevWeave engine/CLI command schema、verification profile selection、verification execution metrics 與其 unit/contract tests；這些是實際支撐 impact-based verification 與 evidence metrics 的必要 source path。

本次 G3 審查後修訂 scope，補齊實際完成上述功能所需的整合 seam 與回歸驗證：`docs/使用手冊.md`、`tests/devweave_test_support.py`、`tests/test_cli.py`、`tests/test_devweave_core.py`、`tests/test_repository_contract.py`、`vscode-extension/src/dashboard.ts`、`src/extension.ts`、`src/vscode-filesystem.ts`、`src/wiki-search.ts`、`webview/help-content.ts`、`webview/main.ts`、目前 `0.2.3` VSIX，以及原先已列出的 engine、Extension、package、README、baseline 與 Wiki paths。完整清單由 DevWeave `scope` CLI 記錄，避免以人工摘要取代機器 scope。

本次修訂另明確要求 VSIX release seam 使用 candidate artifact：package 先建立暫存候選、完成 provenance verifier，只有成功後才以同目錄原子替換 current VSIX；任何 verifier failure 都必須保留既有 current/retained artifact，並由回歸測試驗證。

## 非目標

不包含：

- Extension 直接執行 Python/Shell、網路、Git、Codex API、background agent 或外部 deployment。
- 向量資料庫、RAG、第三方 Wiki index、完整 YAML 依賴或第二套 OpenSpec/Work Item lifecycle。
- 自動更新 upstream companion skills、`skills-lock.json` 或修改本 repository policy/skill router。
- 建立 branch、worktree、commit、push、PR、issue 或 remote tracker。
- 以 bytes/4 推算並宣稱精確 token；沒有 host/API usage 時只提供 proxy metrics。

## 風險

風險等級：high

風險因素：跨越 Extension runtime、build/package、verification config 與 source-bound knowledge；錯誤可能造成錯誤 readiness、漏跑必要驗證或產生錯誤發布產物。主要變更可回退，bootstrap installer 的 no-overwrite/rollback 必須保留。

相容性：以 Extension 0.2.3、58 bootstrap files、119 VSIX entries、Windows VS Code 1.131.0 accepted baseline 為起點；新增 projection/metrics 欄位採向後相容 optional 形式。high profile 維持全 suite、pinned smoke、package verifier 與一個 read-only independent reviewer。

## Profile 補充

本 Work Item 為 feature，第一個 vertical slice 是 path-kind regression + typed filesystem inspection；其後依序處理 authority/readiness、reproducible build、selective verification、metrics 與文件/knowledge reconciliation。

已確認的 material decision：治理品質優先；保留 G1/G2/G3、Plan Mode、Wiki-first、安全邊界與 high-risk single reviewer，效率改善只能在這些硬門檻之內進行。
