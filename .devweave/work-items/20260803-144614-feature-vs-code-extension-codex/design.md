# 系統設計：收斂 VS Code Extension 至初始化與公開 Codex 命令

<!-- DEVWEAVE:artifact=design version=1 work=20260803-144614-feature-vs-code-extension-codex -->

## 設計摘要

選定在既有 `PromptComposer` seam 直接收斂 page-facing contract，而不是新增第二套 legacy composer。`PublicCommandIntent` 是 Webview、Dashboard callback、Extension controller 與 prompt composer 的唯一操作介面；`ActionIntent` 保留為相容名稱 alias，但不再包含 machine-only variants。

唯讀 snapshot、work/gate/task/evidence/Wiki projection、workspace root resolution 與 bootstrap adapter 不變。初始化仍由 `initialize` message 觸發既有 modal-confirmed bootstrap；公開命令則經表單建立 intent，走既有 `previewAction` → `actionPreview` → `copyAction` → `copyResult` 流程。

Prompt composer 只輸出一行 sanitized public chat command：

```text
$devweave <verb> <arguments>
```

不再產生 Python machine command、target paths 或 gate metadata。mutation public commands 在 critical diagnostic 下維持 fail-closed；`next`/`status` 等 read-only commands 仍可預覽。

## 選項比較

### 選項 A：只隱藏既有 UI，保留 broad ActionIntent（拒絕）

只移除畫面按鈕，但保留 Webview parser 與 composer 接受 doctor、task、knowledge、close 等 action。這會讓不受信任或舊版 Webview payload 仍能進入內部 seam，且 machine CLI 仍可能被複製，無法滿足 REQ-006 與 NFR-001。

### 選項 B：新增 PublicPromptComposer，與 legacy composer 並存（拒絕）

可降低現有程式碼變更量，但會形成兩個相近的 prompt seam、重複 sanitization/diagnostic policy，並使維護者必須決定每個 caller 使用哪個 adapter；這降低 locality，也保留錯誤接線風險。

### 選項 C：收斂既有 seam，保留 envelope/名稱相容性（採用）

以 `PublicCommandIntent` 取代 broad page-facing union，沿用 `PromptComposer`、`previewAction`/`copyAction` 與 clipboard adapter。這讓 caller interface 變小、驗證集中於單一深 module，並可保留既有 Webview host message envelope 與 `copyNextAction` command ID。

### 交付方式：preview/copy（採用） vs. 直接 clipboard（拒絕）

直接複製會跳過現有人工確認與 warning 展示；沿用 preview/copy 可維持既有安全與使用者控制，不改變 Extension 不直接執行 Codex 的邊界。

## 介面與資料流

### PublicCommandIntent interface

`src/model.ts` 定義下列 discriminated union；所有必要文字必須為非空字串：

```ts
type PublicCommandIntent =
  | { type: "new"; goal: string }
  | { type: "feature"; request: string }
  | { type: "refactor"; request: string }
  | { type: "bug"; symptom: string }
  | { type: "next"; workId?: string }
  | { type: "status"; workId?: string }
  | { type: "revise"; workId: string; change: string }
  | { type: "approve"; workId: string };
```

`ActionIntent` 以 type alias 指向 `PublicCommandIntent`，避免 repository 內既有名稱造成無意的 caller break；machine-only union members 不保留。`PromptBundle` 收斂為 `chatText`、public command name、optional workId、warnings 與 mutation flag，不再包含 `machineCommand`、`targetPaths` 或 `gate`。

`WebviewToHostMessage` 保留 `previewAction`/`copyAction` envelope，payload 改為 `PublicCommandIntent`。`parseWebviewMessage` 只呼叫 public intent parser；extra fields、missing required fields 與所有 legacy machine action 一律回傳 null 並透過既有 protocol warning 回報。

### UI state 與資料流

1. `WorkspaceSnapshot` 仍由 Extension Host 讀取並送入 Webview；既有 `work-select` 仍是 work context 的唯一來源。
2. Webview 維護小型 public command form state：目前 verb、goal/request/symptom/change 文字，以及 `next`/`status` 是否使用 current work。表單 state 不使用 JSON textarea，也不把 intent 透過 HTML `data-intent` 注入。
3. 單一 work 時沿用 `resolveSelection` 自動帶入；多 work 沒有選取時，`revise`/`approve` disabled，`next`/`status` 可選擇省略 work；切換 work 會重新驗證可用性。
4. Preview click 先做 client-side required-field check，再建立 typed intent 並送 `previewAction`。Host parser 再做 runtime validation，controller 呼叫 composer，回傳 `actionPreview`。
5. Confirm and copy 只把 `bundle.chatText` 寫入既有 clipboard adapter；Extension 不執行 command。`copyNextAction` 改為使用 public `next` intent，沒有 current work 時輸出 `$devweave next`。
6. Dashboard 保留 readonly sections、Refresh、selector、open file 與 initialize；移除 Doctor、Validate、Task、Knowledge、Evidence、Close、gate review 與任意 JSON composer 的操作按鈕。

### Public prompt mapping

| Intent | `chatText` | Mutation |
|---|---|---|
| `new` | `$devweave new <goal>` | yes |
| `feature` | `$devweave feature <request>` | yes |
| `refactor` | `$devweave refactor <request>` | yes |
| `bug` | `$devweave bug <symptom>` | yes |
| `next` | `$devweave next` 或附加 work id | no |
| `status` | `$devweave status` 或附加 work id | no |
| `revise` | `$devweave revise <work id> <change>` | yes |
| `approve` | `$devweave approve <work id>` | yes |

文字沿用既有 sanitization：移除 newline/control/shell-like separators、遮罩 absolute/traversal path 與 credential-like values，並以空白壓縮後產生 deterministic command。

## 失敗模式與回復

- Webview payload malformed 或包含 legacy machine type：parser reject，host 寫入既有 output channel protocol warning，Webview 收到 `protocolError`；不呼叫 callback。
- 表單必要欄位空白：Webview 顯示 inline/status error，不送 message；host parser 仍拒絕繞過 UI 的 invalid payload。
- `revise`/`approve` 沒有 current work：控制項 disabled，且 parser 不接受缺少 workId 的 intent。
- `next`/`status` 沒有 current work：合法產生不帶 work id 的 public command。
- snapshot 有 critical diagnostic 且 intent 是 mutation：composer/host 以 error 中止 preview/copy，不產生非 public blocked text；使用者可改用 `status` form 取得 read-only command。read-only intents 不受此 mutation block 影響。
- clipboard 寫入失敗：沿用既有 `error` message 與 status；不改 repository。
- initialization conflict、critical diagnostic、取消確認、bundle integrity error 或 write failure：完全沿用既有 `BootstrapReport`、fail-closed 與 rollback 實作。
- 回復策略：本變更沒有資料 migration 或 repository state migration；source rollback/rebuild VSIX 即可回復 Extension 行為，bootstrap 目標不受影響。觀測仍使用 output channel、Webview status 與既有 snapshot refresh，無新增 telemetry。

## 高風險分析

本 work 維持 standard risk；不涉及 authentication、privacy、destructive data、multi-service 或外部 process。Security treatment 仍適用：縮小 Webview parser、保持 CSP/clipboard-only seam、維持 input redaction 與 source security tests。Migration 不適用，因為沒有 persisted schema 或 repository data migration；performance 不適用，因為只縮小 UI/prompt path，不增加 snapshot traversal 或 hashing；rollback 以 source revert/repackage 完成。

## 設計決策

## DEC-001: 以單一 public command seam 取代 broad page-facing action seam
- Requirements: REQ-001, REQ-003, REQ-006, NFR-001
- Decision: `PublicCommandIntent` 成為 Webview 到 composer 的唯一 typed interface；`ActionIntent` 只作 public alias，不保留 machine-only variants。
- Rationale: 小介面承載完整 validation、mapping、sanitization 與 mutation policy，提供較深 module、較高 leverage 與較佳 locality；只藏 UI 不能防止 malformed/legacy Webview payload。
- Consequences: 需同步更新 model/protocol/host/UI/tests；舊 machine action 不能再由 Extension page 產生，符合公開 router contract。

## DEC-002: 保留 preview/copy envelope，移除 machine bundle fields
- Requirements: REQ-003, REQ-004, NFR-001, NFR-002
- Decision: 保留 `previewAction`、`copyAction`、`actionPreview`、`copyResult` message flow 與 clipboard adapter；`PromptBundle` 移除 machine command、target paths、gate，`chatText` 只存 public command。
- Rationale: 保留既有使用者控制、extension host wiring 與安全測試，避免不必要的 transport migration，同時使 machine CLI 不可能出現在預覽/clipboard。
- Consequences: core/security tests 與 README 需更新；現有依賴 machine preview metadata 的內部測試不再適用。

## DEC-003: 中央表單是唯一 workflow 操作入口
- Requirements: REQ-001, REQ-002, REQ-005, REQ-007
- Decision: Webview 使用 typed form state 與 current work selector；所有 non-public quick action/remove JSON composer，readonly detail 保留但不再產生 action。
- Rationale: 將使用者選擇、欄位驗證與 public command mapping 集中在單一操作區，減少分散 quick action 造成的 contract 漂移。
- Consequences: next-safe-action/gate/knowledge sections 需要改為 display-only；Refresh/open/select/initialize 等非 workflow UI 不受影響。
