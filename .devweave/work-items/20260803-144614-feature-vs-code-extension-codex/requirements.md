# 需求與驗收條件：收斂 VS Code Extension 至初始化與公開 Codex 命令

<!-- DEVWEAVE:artifact=requirements version=1 work=20260803-144614-feature-vs-code-extension-codex -->

## REQ-001: 公開命令表單
- Priority: must
- Acceptance: AC-001
- Description: Dashboard 操作區必須只提供 `new`、`feature`、`refactor`、`bug`、`next`、`status`、`revise`、`approve` 八個公開命令；表單欄位分別為 goal、request、request、symptom、可選 work、可選 work、work + decision change、work。

## REQ-002: Work context resolution
- Priority: must
- Acceptance: AC-002
- Description: 命令表單必須沿用目前 Dashboard work selection；單一 work 自動帶入，多 work 未選取時不得猜測。`next` 與 `status` 可以省略 work；`revise` 與 `approve` 必須有目前選取 work 才能預覽。

## REQ-003: 公開 prompt preview/copy
- Priority: must
- Acceptance: AC-003
- Description: 使用者提交命令表單後必須先看到 preview，確認後才寫入 clipboard；preview 與 clipboard 的主要文字必須是對應的 `$devweave ...` 公開命令，不得包含 Python machine CLI、`--repo`、target paths 或 gate 參數。

## REQ-004: 初始化保留
- Priority: must
- Acceptance: AC-004
- Description: 未初始化 workspace 仍可透過既有 modal confirmation 直接執行固定 bootstrap；既有 conflict、same-byte adoption、idempotence、rollback 與 critical diagnostic fail-closed 行為不得改變。

## REQ-005: 唯讀 Dashboard 相容性
- Priority: must
- Acceptance: AC-005
- Description: work item、gate、task、evidence、artifact、Wiki 與 audit projection 必須維持唯讀展示；Refresh、work 選取、檔案開啟與初始化等展示/基礎操作維持可用。非公開 machine action 的按鈕與任意 JSON composer 必須消失。

## REQ-006: Page-facing protocol boundary
- Priority: must
- Acceptance: AC-006
- Description: page-facing typed intent 與 Webview parser 只接受八個公開命令的欄位與必要性規則；`doctor`、`commandSet`、`taskStart`、`knowledgePlan`、`close` 等內部 action 不得由 Webview message 送入 Dashboard callback。

## REQ-007: 使用文件一致
- Priority: should
- Acceptance: AC-007
- Description: `vscode-extension/README.md` 必須描述初始化、八個公開命令表單、preview/copy 流程與 Refresh；不得再把任意 workflow action 或 machine action composer 描述為使用入口。

## NFR-001: 安全與輸入處理
- Priority: must
- Acceptance: AC-008
- Description: 變更不得新增 process、shell、Git、network 或 Codex direct execution path；既有 CSP、clipboard-only mutation、absolute/traversal path redaction、credential-like redaction 與 malformed message rejection 必須維持。

## NFR-002: Deterministic compatibility
- Priority: must
- Acceptance: AC-009
- Description: 相同 public intent 與 snapshot 必須產生相同 prompt bundle；既有 extension typecheck、unit、package、smoke 與 root unit verification commands 必須通過。

## AC-001: 八個命令均可由表單建立
- Requirement: REQ-001
- Scenario: Given Dashboard 已載入，When 使用者切換八個命令並填入其必要欄位，Then 每個命令都能形成對應的 typed public intent，空白必要欄位會被拒絕並顯示錯誤。

## AC-002: Work selection 不猜測
- Requirement: REQ-002
- Scenario: Given 零個、單一或多個 work item，When 使用者建立 `next`/`status`/`revise`/`approve`，Then 單一 work 自動帶入、多 work 必須先選取、`next`/`status` 可無 work，且 `revise`/`approve` 無 work 時不可預覽。

## AC-003: Preview 與 clipboard 只有公開命令
- Requirement: REQ-003
- Scenario: Given 一個有效 public intent，When 使用者按下 Preview，Then preview 顯示一行公開 `$devweave` command；When 使用者 Confirm and copy，Then clipboard 與 bundle chat text 相同，且不含 `python`、`--repo`、machine target 或 gate。

## AC-004: Bootstrap regression
- Requirement: REQ-004
- Scenario: Given 未初始化、已初始化、同 bytes、conflict、critical diagnostic、寫入失敗等 bootstrap fixtures，When 執行 initialize 流程，Then 既有 report status、created/adopted/skipped/conflicts/errors/rollback 行為保持通過。

## AC-005: 唯讀 projection 保留、內部入口移除
- Requirement: REQ-005
- Scenario: Given 有 work item 與 Wiki/evidence snapshot，When Dashboard render，Then read-only detail sections、Refresh、selector、open file 與 initialize 可見/可用，Doctor、Validate、Task、Knowledge、Evidence、Close、任意 JSON composer 與其 quick action 不可見。

## AC-006: Parser 拒絕 machine intents
- Requirement: REQ-006
- Scenario: Given public intent 的合法/非法欄位，以及 `doctor`、`commandSet`、`taskStart`、`knowledgePlan`、`close` 等 legacy machine intent，When 送入 Webview parser，Then 合法 public intent 被接受、extra/missing/legacy machine payload 被拒絕。

## AC-007: README 與實際流程一致
- Requirement: REQ-007
- Scenario: Given Extension README，When 使用者依照使用方式操作，Then 文件只描述直接初始化、八個公開命令、preview/copy 與 Refresh，不再指向 machine action composer。

## AC-008: 安全回歸
- Requirement: NFR-001
- Scenario: Given malformed Webview payload、absolute/traversal path、credential-like input 與 runtime source，When 執行 security tests，Then payload 被拒絕、敏感輸入被遮罩，且 source 仍沒有 process/network/direct command execution path。

## AC-009: 完整驗證通過
- Requirement: NFR-002
- Scenario: Given 完成 source/test/doc 變更，When 執行 `extension-tests`、`extension-typecheck`、`extension-package`、`extension-smoke` 與 `unit-tests`，Then 所有 configured commands 以預期結果完成且沒有 stale regression。

## 假設與限制

- `initialize` 是 Extension 唯一直接寫入 repository 的流程；公開 `$devweave` 命令仍由使用者在 Codex Chat 審閱與送出。
- 不新增資料夾選取或 workspace 切換；既有 `resolveRoot` 行為維持。
- `approve` 不把 Dashboard gate status 轉成 public command argument；gate 只作為唯讀資訊。
- 公開 prompt 的輸入仍沿用既有 sanitization 與 warning；不允許以表單繞過 Webview protocol 或 clipboard preview/copy boundary。
- Wiki context 已固定為 `wiki/index.md`、`wiki/overview.md`；overview placeholder gap 在 G3 再依實際 source diff 判斷是否需要 promotion。
