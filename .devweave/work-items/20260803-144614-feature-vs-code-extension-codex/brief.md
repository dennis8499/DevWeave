# 工作摘要：收斂 VS Code Extension 至初始化與公開 Codex 命令

<!-- DEVWEAVE:artifact=brief version=1 work=20260803-144614-feature-vs-code-extension-codex kind=feature -->

## 問題與目標

目前 DevWeave Control Center 的 Dashboard 將完整 workflow audit 與可操作的 machine `ActionIntent JSON` 混在同一個頁面；使用者可以看到 doctor、validate、task、knowledge、evidence、close 等非公開 engine 操作，且預覽內容仍包含 Python machine CLI。這與《使用手冊.md》定義的唯一公開 Codex chat surface 不一致，也增加使用者誤用內部 contract 的機會。

目標使用者是使用 VS Code Extension 操作 DevWeave 的 repository 開發者。成功後，既有唯讀 dashboard 仍可檢視 workflow 狀態，但所有 workflow 操作入口只提供直接初始化與八個公開 `$devweave` 對話命令；命令以表單建立、先預覽，再複製到 Codex Chat。成功訊號是所有八種 prompt 都輸出正確公開命令，Webview 無法送出內部 action，既有初始化與唯讀 projection/安全邊界測試保持通過。

## 現況證據

G1 依序讀取 `wiki/index.md`、`wiki/overview.md`；`wiki/overview.md` 是 placeholder，已記錄 gap：它沒有 Extension 操作流程或公開命令映射，因此以下以 accepted baseline 與目前 source 補足。

- `.devweave/baseline/product.md` 已接受公開 verbs `new/feature/refactor/bug/next/status/revise/approve`，並要求既有 workspace 保留唯讀 dashboard 與 prompt preview/copy。
- `.devweave/baseline/architecture.md` 將 `PromptComposer`、`previewAction`/`copyAction` 與 bootstrap seam 視為 Extension 邊界；bootstrap 直接初始化的 safety 行為不在本次變更內。
- `vscode-extension/webview/main.ts` 目前渲染完整 work/gate/task/evidence/Wiki projection，但也渲染 Doctor、Validate、Knowledge、Task 等 quick actions 與任意 `ActionIntent JSON` composer。
- `vscode-extension/src/model.ts` 與 `src/protocol.ts` 的 `ActionIntent`/parser 支援大量 machine-only action；`src/prompt.ts` 雖能把部分 intent 映射成公開 `$devweave` 標頭，仍生成 Python `--repo` machine command、target paths 與 gate metadata。
- `src/extension.ts` 的初始化流程已具備 modal confirmation、固定 bootstrap bundle、conflict/idempotence/rollback；本次只調整 prompt/copy 的 page-facing contract，不改該流程。
- project 已配置 `extension-package`、`extension-smoke`、`extension-tests`、`extension-typecheck` 與 root `unit-tests`，可作為 G3 的既有 verification baseline。

## 範圍

1. 將 page-facing `ActionIntent` 收斂為只包含八個公開命令的 typed intent 與 parser；更新 Dashboard callback、Extension controller、prompt composer 與 Webview message handling。
2. 將操作區改為命令表單：`new`/`feature`/`refactor`/`bug` 各有一個文字需求欄位；`next`/`status` 使用可選目前 work；`revise` 需要目前 work 與 decision change；`approve` 需要目前 work。
3. 沿用目前選取 work 的解析規則：單一 work 自動使用，多 work 必須明確選取；`next`/`status` 可不帶 work；`revise`/`approve` 沒有 work 時不可送出。
4. 保留 preview → confirm copy 流程；clipboard 與 preview 只含 `$devweave ...` 公開命令，不含 Python machine CLI、target paths 或 gate 參數，並保留既有 sanitization/warning 行為。
5. 移除非公開 action 的頁面入口，保留唯讀 dashboard sections、Refresh、work 選取、檔案開啟與直接初始化。
6. 更新 Extension README 與 extension unit/security tests；不修改使用手冊列出的公開命令內容。

## 非目標

- 不新增從檔案系統手動挑選既有資料夾、切換 workspace 或把絕對路徑帶入 prompt 的功能。
- 不新增 Codex API、直接執行 Codex、Python、shell、Git、network 或 DevWeave engine 的能力。
- 不改 `BootstrapInstaller`、`VscodeBootstrapWorkspace`、固定 manifest、初始化確認、conflict/idempotence/rollback 或 workspace root resolution。
- 不移除唯讀的 work item、gate、task、evidence、Wiki、artifact 與 audit projection；只移除其非公開操作按鈕。
- 不提供 branch、commit、push、PR、close、validate、task、knowledge、evidence 或其他 machine CLI 的替代 UI。

## 風險

風險等級：standard

主要風險是 Webview message/type 收斂可能影響既有 preview/copy caller，以及公開 prompt 格式改變可能使舊測試或使用者依賴 machine command 顯示。變更集中在 Extension UI 與 typed prompt seam，可透過既有 unit/typecheck/package/smoke suite 回歸；初始化 writer 與 repository state 不變，因此可逆性與資料風險低。安全上必須維持 Webview parser、clipboard-only mutation、CSP、無 process/network 路徑與 input redaction。

## Profile 補充

本 work 是 feature：現況為完整 dashboard 與 machine action composer 並存；價值是讓 Extension page-facing workflow 與 repository 已接受的公開 chat contract 一致；影響面是 Webview UI、message/type contract、prompt composition、README 與 extension tests；相容性要求是保留 bootstrap、唯讀 projection、clipboard preview/copy、公開 command semantics 與既有 security/build/smoke baseline。
