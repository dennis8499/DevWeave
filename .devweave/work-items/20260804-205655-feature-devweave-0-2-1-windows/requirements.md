# 需求與驗收條件：DevWeave 0.2.1 Windows 公開版發布強化

<!-- DEVWEAVE:artifact=requirements version=1 work=20260804-205655-feature-devweave-0-2-1-windows -->
## 假設與限制

1. 正式支援 Windows、VS Code 1.90+、Python 3.11+、Git 與 Codex；不包含 Marketplace、跨平台承諾或外部部署。
2. 保留既有 `$devweave` command text、Python CLI schema、engine lifecycle、bootstrap semantic adoption/non-overwrite 與既有 workspace compatibility。
3. `PreviewGate` 是 Extension 內部純 module，不新增 runtime dependency、第二套 lifecycle 或公共 CLI；host 是 copy safety 的最終 enforcement point。
4. `0.2.0` 與 `0.1.0` VSIX 必須在版本 bump 後仍可被 verifier 找到；本 work item 不執行 commit、push 或 Marketplace 發布。
5. Wiki 在 verification 前唯讀；verification 的 Knowledge Review 必須使用 `promote`，由 engine 管理最多五個 content pages、index/log coupling、seal 與 baseline 更新。

## 需求與驗收條件

## REQ-001: Preview-first copy safety
- Priority: must
- Acceptance: AC-001, AC-002, AC-003
- Description: Extension 必須以 typed intent、完整 prompt bundle、panel identity 與 snapshot revision 建立 preview ticket；host 只有在同一 panel、同一 intent、同一 revision 且 ticket 尚未 consume 時接受 copy，否則 fail closed。

## REQ-002: Preview lifecycle 與 retry
- Priority: must
- Acceptance: AC-002, AC-004
- Description: 初始化、refresh、work selection、snapshot revision 更新或新的 preview 必須使舊 ticket/result 失效；clipboard failure 不得遺失可重試的同一合法 ticket，但不得讓 stale ticket 重複 consume。

## REQ-003: Protocol intent parity
- Priority: must
- Acceptance: AC-005
- Description: `actionPreview` 必須回傳可被 Webview 直接辨識的 typed intent 與對應 bundle/revision；既有 `$devweave` command text、CLI schema 與 engine lifecycle 不變。

## REQ-004: Legacy copyNextAction safety
- Priority: must
- Acceptance: AC-006
- Description: 保留 `devweave.copyNextAction` command ID，但 command 只能開啟 Control Center/preview；單一 active work 可預選 next，多 active 或無 active work 必須要求明確選取，不得直接寫 clipboard。

## REQ-005: Wiki search result usability
- Priority: must
- Acceptance: AC-007
- Description: Wiki 搜尋 scheduler 套用 query/type/show-all 時，必須把搜尋結果與 metrics 真實 mount 到 `#wiki-results`，保留 Enter 套用、分類、顯示全部與輸入焦點。

## REQ-006: Multi-work intent clarity
- Priority: must
- Acceptance: AC-008
- Description: 多 active work 時，`next` 未選 work 不得產生可送出的模糊 intent；`status` 必須能明確查詢全部 active work；已有 active work 時不應以 empty-state 誤導建立新 work。

## REQ-007: Accessible and localized Control Center
- Priority: must
- Acceptance: AC-009, AC-010
- Description: 五個區域必須有完整 tab/tabpanel ARIA 關聯、selected/tabindex 語意、方向鍵/Home/End 操作與 focus restore；主要 CTA、native modal action、錯誤與 readiness status 使用繁體中文，技術 command 名稱可保留於 code/technical label。

## REQ-008: Versioned release artifact
- Priority: must
- Acceptance: AC-011, AC-012
- Description: package、lock、bundle metadata、verifier 與 tests 升至 0.2.1；bundle version 從 package version 產生；package verifier 必須驗證 0.2.1 並確認 0.2.0、0.1.0 artifact 保留。

## REQ-009: End-user release documentation
- Priority: must
- Acceptance: AC-013
- Description: root/extension README、使用手冊與 embedded help 必須描述 Windows 支援範圍、VSIX 安裝、首次初始化、合法 evolved workspace、conflict fail-closed、Refresh、Codex handoff、legacy command 與回退 artifact，且測試數字不可過時。

## REQ-010: Python/router contract coverage
- Priority: must
- Acceptance: AC-014
- Description: Python router/CLI 與既有 engine lifecycle 的 public surface、multi-work `next/status` semantics、state safety、bootstrap cancellation/failure no-partial-state contract 必須有 regression coverage；若 source 不需行為改寫，仍須以 tests/verification 證明未被 Extension release 變更破壞。

## NFR-001: Fail-closed mutation boundary
- Priority: must
- Acceptance: AC-001, AC-002, AC-003, AC-004, AC-006
- Description: 任何未經同一 preview、stale revision、不同 intent/panel、mutation-blocked snapshot、conflict 或初始化失敗的 mutation/copy path 都不得寫入 clipboard 或 workspace；錯誤需讓使用者知道下一步。

## NFR-002: Deterministic compatibility
- Priority: must
- Acceptance: AC-005, AC-011, AC-012, AC-014
- Description: 不新增 runtime dependency、不改 public CLI schema/command text、不要求 migration；PromptComposer、PreviewGate、bundle/version validation 與 work selection 對相同輸入產生 deterministic 結果。

## NFR-003: Windows release support
- Priority: must
- Acceptance: AC-015
- Description: 在 Windows trusted workspace 中完成 package、Extension Host smoke、typecheck、Extension tests、Python full suite 與四條 disposable walkthrough；任何 environment-only skip 必須有清楚、窄幅的替代證據或 waiver。

## NFR-004: High-risk review readiness
- Priority: must
- Acceptance: AC-016
- Description: final product/Wiki/baseline/diff/scope/evidence 穩定後，透過唯一 DevWeave router 產生 exactly one isolated read-only Independent Review；current result 必須為 `passed`，不得有未處理 advisory，critical/scope/security/data-loss finding 必須阻擋 G3 或有 exact narrow waiver。

## NFR-005: Reversible release
- Priority: must
- Acceptance: AC-012, AC-015
- Description: 0.2.1 失敗或回退時，既有 0.2.0、0.1.0 VSIX bytes 與既有合法 workspace bytes 不被覆寫；bootstrap cancellation/failure 不留下 partial control state。

## AC-001: Webview 未預覽不得複製
- Requirement: REQ-001, NFR-001
- Scenario: Given 一個可產生 mutation prompt 的 snapshot，When 使用者直接送出 `copyAction` 或 host 收到沒有 preview ticket 的 copy，Then host 拒絕並回傳繁中錯誤，clipboard 不變。

## AC-002: matching preview 才能一次 consume
- Requirement: REQ-001, REQ-002, NFR-001
- Scenario: Given 同一 panel、typed intent、snapshot revision 已完成 preview，When 使用者確認複製一次，Then 只 consume 該 ticket 並複製相同 bundle；再次複製相同 ticket 或使用不同 intent/panel/revision，Then 一律拒絕。

## AC-003: stale snapshot 必須重新預覽
- Requirement: REQ-001, REQ-002, NFR-001
- Scenario: Given prompt 已預覽，When refresh、初始化、work selection 或新的 snapshot revision 發生，Then 舊 preview/result 被清除或標示過期；When 使用者再次 copy，Then 必須先完成新的 preview。

## AC-004: clipboard failure 可安全 retry
- Requirement: REQ-002, NFR-001
- Scenario: Given合法 preview ticket，When clipboard write 失敗且 revision/panel 未變，Then顯示可重試錯誤並保留該 preview；When revision 已變，Then不可恢復舊 ticket。

## AC-005: host-launched preview intent parity
- Requirement: REQ-003, NFR-002
- Scenario: Given `copyNextAction` 或其他 host-launched preview，When Dashboard 收到 `actionPreview`，Then message 同時包含 typed intent、bundle 與 current revision，Webview 能以相同確認流程完成 copy；既有 prompt command text 與 CLI JSON schema regression 全通過。

## AC-006: legacy command 不再 bypass preview
- Requirement: REQ-004, NFR-001
- Scenario: Given只有一個 active work，When使用者執行 `devweave.copyNextAction`，Then開啟 Control Center 並顯示該 work 的 next preview；Given零個或多個 active work，When執行同一 command，Then不複製，要求使用者在 Control Center 明確選取 work。

## AC-007: Wiki DOM mount
- Requirement: REQ-005
- Scenario: Given Knowledge section 的搜尋結果，When使用者按 Enter 套用 query、切換分類或顯示全部，Then `#wiki-results` 的 DOM 內容與 model 結果一致，input DOM/focus 不被重建。

## AC-008: multi-work semantics
- Requirement: REQ-006
- Scenario: Given多個 active work 且未選取 work，When選擇 `next`，Then form 不允許產生模糊 preview；When選擇 `status`，Then可明確預覽查詢全部 active work；Work empty state 不提供誤導性的新增 work CTA。選定 work 後兩者皆只針對該 work。

## AC-009: tab ARIA and keyboard
- Requirement: REQ-007
- Scenario: Given五個 Control Center tabs，When以滑鼠、Tab、方向鍵、Home、End切換，Then selected tab、tabindex、tabpanel `aria-labelledby`/`aria-controls` 與 focus restore 一致；窄視窗與 high-contrast style check 通過。

## AC-010: Traditional Chinese primary UI
- Requirement: REQ-007
- Scenario: Given首次使用者從初始化、preview、copy、錯誤、readiness、refresh與help路徑操作，Then主要 CTA/native modal action/status均為繁體中文，技術 command 只在 code/technical label 保留英文。

## AC-011: 0.2.1 bundle provenance
- Requirement: REQ-008, NFR-002
- Scenario: Given package version 0.2.1，When執行package與verifier，Then VSIX名稱、manifest/bundle version與package version一致，且每個 bootstrap entry integrity/compatibility check 通過。

## AC-012: artifact retention and rollback
- Requirement: REQ-008, NFR-005
- Scenario: Given repository已有0.1.0與0.2.0 VSIX，When產出0.2.1，Then舊兩個artifact bytes仍存在且verifier明確檢查；package failure或回退不刪除/覆寫舊artifact。

## AC-013: end-user documentation
- Requirement: REQ-009
- Scenario: Given未接觸過 DevWeave 的 Windows/VS Code 使用者，When閱讀 root README、extension README、使用手冊或 embedded help，Then能找到 VSIX 安裝、首次初始化、evolved/conflict 行為、Refresh、Codex handoff、支援邊界與 legacy command；測試數字與0.2.1版本敘述一致。

## AC-014: Python and public contract regression
- Requirement: REQ-003, REQ-010, NFR-002
- Scenario: When執行 Python full suite，Then既有94項基線 plus 本工作新增 regression（含 multi-work、bootstrap cancel/failure、public command/schema）通過，Windows symlink privilege skip若仍存在則有既有窄幅說明；engine lifecycle沒有新增或改名。

## AC-015: Windows verification walkthrough
- Requirement: NFR-003, NFR-005
- Scenario: In disposable Windows workspaces，complete fresh install/init、合法 evolved workspace、reserved conflict fail-closed、multi-active work four walkthroughs；verify cancellation/failure leaves no partial state, prompt never copies without confirmation, and refresh invalidates old preview. Record commands/screenshots/logs or equivalent evidence.

## AC-016: Independent Review and G3 readiness
- Requirement: NFR-004
- Scenario: Given final source/Wiki/baseline/diff/scope/evidence fixed，When DevWeave router runs exactly one isolated read-only Independent Review，Then current review record is `passed` with no unresolved advisory；any critical/scope/security/data-loss finding blocks G3 unless exact narrow `review-critical` waiver names each finding。
