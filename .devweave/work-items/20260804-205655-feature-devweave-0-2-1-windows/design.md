# 系統設計：DevWeave 0.2.1 Windows 公開版發布強化

<!-- DEVWEAVE:artifact=design version=1 work=20260804-205655-feature-devweave-0-2-1-windows -->

## 設計摘要

本設計把「先預覽再複製」集中成一個 Extension 內部的深 module `PreviewGate`，由 `DashboardPanel` 作為唯一 host enforcement seam。它不執行 CLI、engine、shell、Git 或 network，只管理 typed intent、已組成的 `PromptBundle`、panel identity、snapshot revision、一次性 consume 與安全 retry。

關鍵不變量：

1. Webview 仍只送既有 public `previewAction`/`copyAction` intent；`$devweave` command text、Python CLI schema、engine lifecycle、bootstrap installer 與 workspace migration contract 不變。
2. Host 只在同一 panel、同一 typed intent、同一 snapshot revision 且存在未 consume preview ticket 時接受 copy；所有其他情況 fail closed。
3. `WorkspaceSnapshot` 不增加權威 revision 欄位；revision 是 Dashboard host message 的 additive metadata，由 `DashboardPanel` 在會改變可用 prompt context 的事件中單調遞增。
4. Wiki 搜尋的 model/filter contract 不變；只補上局部 DOM mount seam，不觸發 repository scan 或 Wiki write。
5. 0.2.1 是 package/build metadata 與 derived bundle 的版本變更；既有 0.2.0、0.1.0 VSIX 保留原 bytes 作為回退。

## 選項比較

| 設計選項 | 選定 | 取捨 |
| --- | --- | --- |
| 在每個 Webview CTA 自己記錄「已預覽」 | 否 | 可以少改 host，但 command palette、legacy command 與 malformed message 仍可繞過，無法形成安全 enforcement。 |
| 在 `DashboardPanel` 內直接保存 bundle/intent | 否 | 比 UI gate 強，但 state、一次性 consume、retry、revision invalidation 會散落在 panel handler，測試與 failure recovery 較淺。 |
| `PreviewGate` 純 module + Dashboard host adapter | 是 | 多一個小型 interface，但把安全不變量集中到可獨立測試的 seam，所有 copy caller 共用同一規則。 |
| 將 revision 寫入 Python snapshot/schema | 否 | 可由 engine 提供 revision，但會擴大 CLI/schema/legacy compatibility 影響；本需求只需要 host-local freshness。 |
| `DashboardPanel` 擁有 monotonic revision，display-mode resend 不失效 | 是 | 不改權威 snapshot；host 可精確區分 refresh/selection/bootstrap 與單純偏好更新。 |
| copy 時重新用 intent compose bundle | 否 | 可保留舊 callback 形狀，但 refresh 或選取變更後可能 compose 出不同內容，違反 preview/copy parity。 |
| copy callback 接受已 staged `PromptBundle` | 是 | host 必須檢查 mutationBlocked，但可確保複製的 bytes 就是使用者看到的 preview。 |
| `copyNextAction` 繼續直接 copy | 否 | 會持續繞過 preview-first；不可接受。 |
| `copyNextAction` 開啟 Dashboard，單一 active work 自動 stage preview | 是 | 保留 command ID 與便利性；多 work/無 work 仍由 UI 明確選取，沒有 silent choice。 |
| 直接在 `main.ts` 事件 callback 寫 `#wiki-results` | 否 | 立即修 bug，但 DOM mount 難以單獨測試，render 與 side effect 混合。 |
| 保留純 markup renderer，增加小型 `mountWikiResults` adapter | 是 | markup 與 DOM side effect 分離；能用 fake document 驗證實際 mount，且不引入 jsdom/runtime dependency。 |
| 引入 UI framework/ARIA library | 否 | 超出 release scope、增加 bundle/runtime 風險；現有 vanilla Webview 已有 focus/CSP/theme seams。 |
| package/esbuild 所有地方手動同步版本 | 否 | 容易再漂移；由 esbuild 讀取 package.json 產生 bundle version，verifier 驗證 artifact version。 |

## 介面與資料流

### `PreviewGate` interface

`vscode-extension/src/preview-gate.ts` 提供小而深的純 interface：

```ts
interface PreviewTicket {
  id: number;
  panelId: string;
  revision: number;
  intent: PublicCommandIntent;
  bundle: PromptBundle;
}

class PreviewGate {
  stage(panelId, intent, revision, bundle): PreviewTicket;
  take(panelId, intent, revision): PreviewTicket | null;
  restore(ticket): boolean;
  invalidate(): void;
}
```

`stage` 會取代舊 ticket 並建立新的 epoch/id；`take` 只在 panel、revision 與 canonical typed intent 全部相同時一次性移除 ticket；`restore` 只在沒有較新 ticket、沒有 invalidate 且仍是同一 epoch 時恢復，供 clipboard failure retry；`invalidate` 清除 ticket 並增加 epoch。Module 不知道 clipboard、VS Code 或 DOM。

### Dashboard host adapter

`DashboardCallbacks.preview(intent)` 保持 intent-based composition；`copy(bundle)` 改為接受已 preview 的 bundle。`DashboardPanel` 保存 `panelId`、`revision` 與 `PreviewGate`：

- `show` 初次建立/重新顯示、`refresh`、`initialize` 結果、work selection 與新的 snapshot publish 呼叫 `invalidate` 並將 revision 加一。
- `setDisplayMode` 只重送同一 snapshot 與 revision，不清除 preview。
- `previewAction` 先呼叫 composer callback，成功後 stage ticket，再送 `{ type: "actionPreview", intent, bundle, revision }`。
- `copyAction` 先 `take`；沒有 ticket 時直接回傳繁中錯誤。取到 ticket 後呼叫 `copy(bundle)`；成功送 `copyResult`，失敗 `restore(ticket)` 並送錯誤。
- `snapshot` 與 `bootstrapResult` message 加入同一個 additive `revision` 欄位；Webview inbound parser 的 public intent schema 不變。

### Controller/legacy flow

`ExtensionController.copyNextAction()` 不再呼叫 clipboard。它解析 workspace root、refresh、開啟 Dashboard；只有一個 active work 時呼叫 `dashboard.previewAction({ type: "next", workId })`。零個或多個 active work 只顯示 Dashboard，讓使用者明確選取；selected closed work 不可被當成 next target。一般 native `wikiBootstrap` modal 仍保留既有「先顯示完整 prompt、再由使用者確認」流程，並統一繁中 action labels。

### Webview state and DOM flow

Webview 保存 `snapshotRevision` 與 preview intent。收到不同 revision 的 snapshot/bootstrap result 時清除 `pendingIntent`、preview/copy/bootstrap transient result，再 render；收到 `actionPreview` 時從 message 回填 intent、bundle、revision，讓 host-launched preview 和表單 preview 共用確認按鈕。copy success 清除 ticket representation；copy failure 保留可 retry preview。

`renderKnowledgeResults()` 繼續只產生 markup；`mountWikiResults()` 尋找 `#wiki-results` 並設定 `innerHTML`，由 `knowledgeRenderScheduler` 呼叫。五個 tab 會有穩定 tab id、tabpanel id、`aria-controls`/`aria-labelledby`、active `tabindex=0`，其他 tab `-1`；方向鍵/Home/End 更新 selected section、重 render 後 restore focus。

### Multi-work and presentation flow

`next` 在 active work 超過一個且未選取時不產生 intent；selected active work 才帶 `workId`。`status` 在 selected work 時可選擇該 work，未選取時提供明確「查詢全部進行中的 work」選項並產生不帶 ID 的既有 `$devweave status`。Work empty card 只在 active count 為零時顯示建立新 work CTA。`presentStatus` 增補 readiness labels，主要 CTA、native modal action、error/readiness status 與 release help 統一繁中，technical command 僅留在 `<code>`/technical label。

### Version/build flow

`package.json`/lock 升至 0.2.1；`esbuild.mjs` 讀 package.json version 形成 `dist/bootstrap/manifest.json` bundle metadata；`verify-package.mjs` 以 package version 作 current expected，要求 current 0.2.1 VSIX、既有 0.2.0 與 0.1.0 VSIX，並檢查 current manifest/version/entries。package script 只建立新 artifact，不刪除舊 artifact。

## 失敗模式與回復

| 情境 | 行為 | 可觀察結果/回復 |
| --- | --- | --- |
| malformed/unknown Webview message | parser reject；不呼叫 callback | `protocolError` 與 output channel；clipboard/workspace 不變。 |
| 沒有 preview、intent/panel/revision 不符 | `PreviewGate.take` 回傳 null；host 拒絕 copy | Webview 顯示「請先重新預覽」；不寫 clipboard。 |
| snapshot/selection/initialize/refresh 更新 | host invalidate、revision +1；Webview 清 transient preview | 使用者必須重新預覽，舊 ticket 無法 restore。 |
| compose 遇 critical diagnostic | callback throw；不 stage ticket | error/status 顯示 read-only next step，既有 mutationBlocked contract 保留。 |
| clipboard 失敗 | host restore 仍 current 的 ticket；新 revision/新 ticket 時 restore 失敗 | 同一 preview 可 retry；不會重複 consume stale ticket。 |
| 多 work 執行 legacy command | 開 Dashboard，不自動選取或 copy | UI 顯示明確選 work；保持 `status --all`/指定 ID 的 engine contract。 |
| bootstrap cancel/conflict/write failure | 沿用 BootstrapInstaller preflight/rollback，refresh projection | 既有 bytes 不覆寫；report 顯示取消、conflict、error、rolledBack。 |
| package/verifier failure | 不觸碰 0.2.0/0.1.0；0.2.1 不宣稱可交付 | 以 verifier 與 artifact listing 判定，必要時回退舊 VSIX。 |

## 高風險分析

### Migration

不適用。revision、PreviewGate 與 host message metadata 是 Extension 內部/additive；不改 `.devweave` schema、Python CLI schema、Work Item state 或既有 workspace bytes，不需 migration。

### Rollback

保留並驗證 0.2.0、0.1.0 VSIX；0.2.1 package 失敗不刪除舊 artifact。Runtime bootstrap 仍只走既有 allowlist、non-overwrite、semantic adoption 與 atomic rollback。若 0.2.1 需回退，使用舊 VSIX，不反向修改 workspace control state。

### Security and compatibility

PreviewGate 是 mutation/copy safety 的最後 host seam；PromptComposer 既有 path/credential sanitization 保持不變。Panel/revision/intent 三重匹配避免 cross-panel、stale 或 forged copy；Webview 只傳 public intent，不暴露 ticket/engine command。既有 command ID、prompt text、CLI envelope、CSP、no-process/no-network/no-engine boundary 保持相容。

### Performance

不增加 runtime dependency、filesystem scan、network 或 Python process。PreviewGate `stage/take/restore/invalidate` 為常數時間；revision 是 host-local integer；Wiki scheduler 只更新既有結果區；ARIA/focus 操作只影響目前 Webview DOM。package build 由既有 esbuild pipeline 完成。

### Observability and verification

Dashboard host 以 `protocolError`/`error` message 與既有 Extension output channel 呈現拒絕原因；Webview status line 使用 `status`/`alert`。測試跨越同一 interface：PreviewGate unit tests、protocol additive contract、Dashboard handler/security assertions、Wiki mount fake-document、multi-work/presentation、ARIA static checks、package/version verifier 與完整 Windows smoke。

## 設計決策

## DEC-001: Host-enforced deep PreviewGate seam
- Requirements: REQ-001, REQ-002, NFR-001
- Decision: 在 `src/preview-gate.ts` 建立純 module，由 `DashboardPanel` 持有並 enforce；不把 gate 只放在 Webview。
- Rationale: 集中同一 panel/intent/revision/one-shot/retry invariant，讓 legacy、malformed message 與一般 UI 共用安全規則。
- Consequences: Dashboard callback 需要改為 copy staged bundle；增加一個小型 interface 與 ticket lifecycle，但降低 caller duplication。

## DEC-002: Dashboard-owned additive snapshot revision
- Requirements: REQ-001, REQ-002, REQ-003, NFR-002
- Decision: `DashboardPanel` 在 invalidating snapshot boundary 維護 monotonic revision；只在 host messages 帶 revision，不改 `WorkspaceSnapshot` 或 Python schema。
- Rationale: freshness 是 projection/client concern，避免把 Extension UI lifecycle 擴散到 engine/CLI。
- Consequences: refresh/selection/bootstrap 必須經由同一 send path；display-mode resend 要明確保留 revision。

## DEC-003: Copy exact staged bundle
- Requirements: REQ-001, REQ-002, NFR-001
- Decision: copy callback 接受 `PromptBundle`，不在 copy 時重新 compose intent。
- Rationale: 使用者確認的 bytes 與最後 clipboard bytes 必須完全相同，避免 snapshot drift。
- Consequences: controller 需額外檢查目前 mutationBlocked；clipboard failure 必須交回 gate restore。

## DEC-004: Legacy command routes into Dashboard preview
- Requirements: REQ-004, REQ-006, NFR-001
- Decision: 保留 `devweave.copyNextAction` command ID，但改為 open/reveal Dashboard，單一 active work host-stage preview，多/無 work 不作 implicit selection。
- Rationale: 保留使用者熟悉的 command surface，同時消除直接 clipboard side effect。
- Consequences: command execution 變成非同步 UI flow；多 work 使用者需要一次明確選取。

## DEC-005: Pure Wiki markup plus mount adapter
- Requirements: REQ-005, NFR-002
- Decision: 保留 `renderKnowledgeResults` pure string output，增加可 fake document 測試的 `mountWikiResults` seam，由 scheduler 真正寫入 `#wiki-results`。
- Rationale: 修正實際 DOM bug 並維持 Enter/type/show-all/search model 與 focus locality。
- Consequences: local render 在離開 Knowledge tab 時可能 no-op，下一次 full render 會使用最新 model state；不引入 DOM framework。

## DEC-006: Vanilla ARIA/focus hardening
- Requirements: REQ-007, NFR-002
- Decision: 以原生 `role=tab`/`role=tabpanel`、stable ids、roving tabindex、方向鍵/Home/End 與既有 focus restore 完成五區 tab；用現有 theme/forced-colors CSS。
- Rationale: 只增加必要語意與 keyboard behavior，不引入視覺框架或全面重整。
- Consequences: `main.ts` render shell 與 keydown delegation 需一起更新，static/unit tests 要鎖定五 tab contract。

## DEC-007: Package-derived 0.2.1 bundle version
- Requirements: REQ-008, NFR-002, NFR-005
- Decision: package.json 是 current version source；esbuild read package JSON，verifier 要求 current 0.2.1 與保留的 0.2.0/0.1.0 artifacts。
- Rationale: 消除 hardcoded bundle drift，讓 rollback artifact 可被明確驗證。
- Consequences: package-lock/bootstrap contract/verifier/docs/help tests 需同步更新；舊 VSIX 必須維持 tracked bytes。

## DEC-008: UI-only multi-work guard with stable public commands
- Requirements: REQ-006, REQ-010, NFR-002
- Decision: UI 在 ambiguous `next` 阻止 preview，`status` 提供 all-active 明確選項；Python router/CLI public command/schema 不新增選項或改名。
- Rationale: 既有文件與 engine 已有 explicit ID/`status --all` contract，這次修正 Extension 的誤導與 implicit selection 即可。
- Consequences: multi-work regression 放在 Extension/presentation 與 Python contract suite；產品仍可用既有 `$devweave status` 查全體、`$devweave next <id>` 指定 work。
