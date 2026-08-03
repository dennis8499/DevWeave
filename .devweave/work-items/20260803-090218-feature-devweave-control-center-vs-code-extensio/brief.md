# 工作摘要：建立 DevWeave Control Center VS Code Extension

<!-- DEVWEAVE:artifact=brief version=1 work=20260803-090218-feature-devweave-control-center-vs-code-extensio kind=feature -->

## 問題與目標

目前 DevWeave 以 repository 內的 Python engine、Markdown artifacts、JSON/JSONL ledger、Wiki 與 Codex hook 維持可追溯 SDLC，但使用者需要透過命令或 Codex 對話理解 phase、gate、task、evidence 與 Wiki health。這使得 onboarding、人工 gate review 與 G3 verification 的狀態瀏覽成本偏高。

本工作項為一般開發者與 reviewer 建立通用、desktop-first 的 VS Code Extension Control Center。Extension 讀取 managed DevWeave repository 的現況，提供 Apple-inspired、VS Code theme-aware 的 dashboard、sidebar work-item navigation、Wiki/phase 瀏覽與 deterministic Codex Chat prompt composer。成功訊號是：使用者可以在 VS Code 中看懂目前工作項的下一個安全步驟，並將每個需要 mutation 的操作以可審閱 prompt 複製至 Codex Chat，而不產生第二套 lifecycle 或繞過既有 engine、hook 與人工 gate。

## 現況證據

- G1 knowledge context 已依規定先讀 `wiki/index.md`，再讀 `wiki/overview.md`；overview 仍為 bootstrap placeholder，已記錄 raw-source follow-up gap。
- `README.md` 與 `docs/使用手冊.md` 定義 DevWeave 的三道 gate、八個 phase、五份 Markdown artifacts、task/evidence、Wiki-first、fingerprint、baseline 與 machine CLI contract。
- `.devweave/project.json` 顯示目前 repository 為 `managed: true`、locale 為 `zh-TW`、knowledge root 為 `wiki`，目前只有 `unit-tests` verification command。
- `devweave.py` 的 public CLI 覆蓋 project initialization、work lifecycle、risk/scope/baseline、knowledge、task、evidence、verification、waiver、gate approval、revision 與 close；`devweave_core.py` 及 `knowledge_core.py` 保有 state transition、fingerprint、path safety 與 Wiki validation 行為。
- `.codex/hooks.json` 與 `guard.py` 對 managed repository 實施 session binding、G2 write boundary、scope boundary 與 verification-only Wiki/baseline write policy。
- 目前 repository 沒有 VS Code Extension manifest 或 TypeScript build surface，因此 Extension 必須是一個 bounded new subtree，且需建立獨立 typecheck、unit test、activation smoke test 與 package verification。

## 範圍

- 新增 `vscode-extension/` 內的 TypeScript VS Code Extension，包含 Extension Host、TreeView、Dashboard Webview、vanilla UI、contract projection、snapshot reader、prompt composer、clipboard adapter 與測試。
- 以 workspace file API 唯讀解析 `.devweave/project.json`、work-item state/artifacts/evidence/events、baseline、Wiki、hook 與 DevWeave skill presence；不呼叫 Python、shell、Codex agent API 或任何 mutation process。
- 提供 repository welcome/doctor、dashboard、work-item detail、G1/G2/implementation/G3 檢視、Wiki-first workspace、audit view、command/action preview 與 clipboard copy flow。
- 對既有 DevWeave machine/public command surface 提供完整 `ActionIntent` 對應；每個 mutation action 產生可複製至 Codex Chat 的 Traditional Chinese prompt 與 machine command preview。
- 提供 filesystem snapshot、last engine-observed state、stale/refresh warning 與 malformed/unsupported contract fallback。
- 保持既有 Python engine、schema version、JSON envelope、state/event/evidence ledger、Wiki contract、hook policy 與人工 G1/G2/G3 gate 不變。

## 非目標

- 不重寫、fork、複製或在 TypeScript 中重建 DevWeave engine、fingerprint、state transition、Wiki lint 或 guard。
- 不直接執行 CLI，不直接寫入 `state.json`、`events.jsonl`、evidence、project config、Wiki、baseline、product source 或 tests。
- 不新增 branch、commit、tag、push、PR、remote coordination、release/version management 或 Git 操作 UI。
- 不建立第二個 agent、router、orchestrator、RAG、database 或 Codex model runtime；Codex Chat 仍由使用者送出 prompt。
- 不在本 work item 內提升 Wiki placeholder 為完整 codebase overview；Extension 的 raw-source projection 只讀取並呈現現況。

## 風險

風險等級：high

- 新增 TypeScript/Node build 與 VS Code runtime surface，現有 repository 只有 Python standard-library verification baseline。
- Extension 若重複 engine policy，可能造成 UI 與 Python contract drift；因此以小型 projection interface 與單一 deep `PromptComposer` seam 隔離複雜度，並以 fixture/contract tests 驗證。
- Webview 可能造成 theme、high-contrast、keyboard、ARIA 或 CSP 問題；以 VS Code theme tokens、vanilla DOM、accessibility test matrix 與 conservative CSS 控制。
- 不直接執行 mutation 可造成 snapshot 與 engine authoritative state 短暫不同；UI 必須顯示 snapshot provenance、last observed time 與 Codex refresh instruction。
- 所有 mutation 透過 clipboard prompt 仍可能被使用者誤送；approval、waiver、revise、close 使用明顯的 destructive/governance warning 與 action preview。
- 失敗回復為移除/停用 Extension；既有 DevWeave engine 與 repository state 不受 Extension runtime 影響。

## Profile 補充

本 work item 是 feature：價值是降低 DevWeave 的瀏覽與操作認知成本，但不改變 engine 的既有行為；影響面是新增 `vscode-extension/**`、Node/TypeScript build 與 project verification commands，並需維持 current Python suite、JSON contract、hook safety 與 gate semantics。第一個可驗證切片為「讀取 managed repository、呈現 dashboard/work item snapshot，並將一個完整 mutation action 產生 deterministic Codex prompt 後複製到 clipboard」。
