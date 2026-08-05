# 工作摘要：DevWeave 0.2.1 Windows 公開版發布強化

<!-- DEVWEAVE:artifact=brief version=1 work=20260804-205655-feature-devweave-0-2-1-windows kind=feature -->

## 問題與目標

DevWeave 今日要交付 Windows 公開版。現有 0.2.0 Control Center 已具備 bootstrap、Wiki projection、公開 prompt 與 verification readiness，但發布前仍有數個會直接影響首次使用者理解、prompt 安全邊界與回退能力的缺口：Wiki 搜尋結果沒有 mount 到 DOM、legacy `copyNextAction` 可繞過 preview、host 沒有驗證 copy 前置條件、snapshot 更新後可能留下過期 prompt、五區 tab 的 ARIA/鍵盤語意不完整、主要 CTA 尚有英文，以及版本與安裝文件落後。

本工作目標是交付可回退的 `0.2.1` Windows release bundle，讓第一次使用者能在 VS Code 內完成初始化、選取 work、預覽並確認 prompt，再交給 Codex Chat；同時讓 stale state、multi-work、bootstrap conflict、版本 artifact 與文件都能被明確驗收。成功訊號是所有 core product surfaces、Python contract、VSIX build/package/smoke、文件與四條 Windows walkthrough 均有 current evidence，且 high-risk Independent Review 為 current `passed`、沒有未處理 advisory。

## 現況證據

### Wiki facts

- 本次 G1 已先讀 `wiki/index.md`，再記錄 `wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`；完整 path、status、content hash、stored/computed source fingerprint 已由 `knowledge context` 保存。
- Wiki 已說明 Extension 是唯讀 projection、PromptComposer 是 prompt-only seam、Wiki 搜尋應局部 render、bootstrap 採 semantic adoption、high-risk G3 需要 Independent Review；但現有頁面仍以 0.2.0 行為為基準，未覆蓋本次 0.2.1 的 PreviewGate、snapshot revision、legacy command、Windows 安裝與新 ARIA 細節。這些差異已先登錄為 G1 gaps，不能把 Wiki 推論當成新版本 source truth。

### Source-backed facts

- `vscode-extension/webview/main.ts` 的 `knowledgeRenderScheduler` 只執行回傳 markup 的函式，沒有把結果寫入 `#wiki-results`；現有測試只檢查 seam 存在，未證明 DOM mount。
- `vscode-extension/src/extension.ts` 的 `copyNextAction()` 直接呼叫 copy；`vscode-extension/src/dashboard.ts` 對合法 `copyAction` 直接呼叫 host callback，沒有 matching preview ticket、panel identity 或 snapshot revision gate。
- snapshot/bootstrap/copy message 目前沒有 revision contract；Webview 在 refresh、bootstrap 或 work selection 後未一致清除所有 transient prompt state，host-launched `actionPreview` 也沒有帶回 typed intent。
- 五個 section tab 已存在，但 `main.ts` 沒有完整 tab/tabpanel id、方向鍵/Home/End semantics，`styles.css` 仍以四欄作為主要 grid；主要 preview/初始化/複製 CTA 與 native modal action 仍有英文。
- `next` 在多個 active work 且未選取時仍可形成無 workId intent；Work empty projection 也可能在已有 active work 時引導建立新 work。`status` 需要保留明確查詢全部 active work 的能力。
- `package.json`、`package-lock.json`、esbuild bundle metadata、package verifier 與 bootstrap contract test 仍以 `0.2.0` 為現行版本；verifier 尚未要求同時保留 `0.2.0` 與 `0.1.0` artifact。`docs/使用手冊.md` 仍寫 62 項測試，README/help 缺少完整終端使用者 VSIX 安裝流程。
- accepted quality baseline 記錄的目前基線為 Python 94 tests（Windows symlink privilege 1 skip）、Extension 60 tests、typecheck/package/smoke 通過；本工作會在實作後重跑並更新實際數字與 0.2.1 artifact evidence。

### Inferences

- preview 必須由 host 最終 enforce；只在 Webview 隱藏按鈕不足以保護 command palette、舊 command 或任何其他 host-launched path。
- prompt bundle 應在 preview 與 copy 間以 typed intent、panel、snapshot revision 綁定，copy 使用已預覽 bundle，才能避免 refresh 或重組造成 drift。
- 0.2.1 應維持既有 `$devweave` command text、Python engine lifecycle、CLI schema 與 bootstrap non-overwrite contract；新行為只補強 Extension 邊界與必要的 Python/router contract regression。

### Unresolved gaps

- 目前尚未有本 work item 的實作後 regression、package/smoke、四條 disposable Windows walkthrough 或 current Independent Review evidence。
- Wiki、baseline 與 release acceptance 需在 verification 階段依 Knowledge Review `promote` 更新；在此之前保持唯讀。

## 範圍

包含：

- `PreviewGate` 純 module、Dashboard host enforcement、protocol `actionPreview` intent/revision、refresh/selection/bootstrap stale invalidation、clipboard failure retry，以及 `copyNextAction` 保留 command ID 但改為開啟 Control Center/preview。
- Wiki 搜尋結果實際 mount、五區 tab/tabpanel ARIA、方向鍵/Home/End/focus restore、窄視窗/高對比檢查、主要 CTA/native modal/error/readiness 的繁中化。
- 多 active work 的 `next` 明確選取與 `status` 全部查詢語意；既有 public command text、CLI schema 與 engine lifecycle 的相容性 regression。
- 0.2.1 package/bundle/verifier 與 VSIX artifact retention；文件、VSIX 安裝/初始化/Refresh/Codex handoff/Windows support 邊界；verification 需要的 Extension/Python tests、walkthrough evidence、Wiki promote 與必要 baseline 更新。

主要路徑為 `.agents/skills/devweave/scripts`、`tests`、`vscode-extension/src`、`webview`、`test`、`scripts`、package/build metadata、`README.md`、`docs/使用手冊.md`、`wiki` 與 `.devweave/baseline`。

## 非目標

不包含 Marketplace 上架、commit/push/branch/worktree/PR/deployment、外部協調、第二套 release lifecycle/router/CLI/engine、runtime dependency、Python schema breaking change、既有 workspace migration、macOS/Linux 支援承諾、完整 visual redesign 或新增 production instrumentation。

## 風險

風險等級：high

風險集中在「未確認就複製 prompt」可能觸發 mutation workflow、stale snapshot 造成錯誤 work/command、bootstrap/clipboard failure 的 partial state、release artifact 遺失與 accessibility regression。採 fail-closed：沒有 matching preview、intent 不一致、panel 不一致或 revision 過期時拒絕 copy；clipboard 失敗只在仍是同一 ticket/revision 時允許一次 retry；初始化沿用既有 allowlisted installer rollback/non-overwrite contract。

0.2.1 可透過保留且 verifier 驗證的 `devweave-control-center-0.2.0.vsix` 或 `0.1.0.vsix` 回退；不改 schema、不要求 migration。正式支援邊界為 Windows、VS Code 1.90+、Python 3.11+、Git 與 Codex。high-risk release 的 product/security/data-loss/core UX blocker 必須修正；environment-only evidence skip 必須有窄幅替代證據或 waiver，且 current Independent Review 必須 `passed` 並無未處理 advisory。

## Profile 補充

本工作採 feature profile：以現有 0.2.0 行為與測試作 baseline，透過小型可測試 seams（PreviewGate、protocol、DOM mount、presentation/accessibility）改善公開版體驗，保留既有公開 command、bootstrap 與 engine compatibility。

## 已回答的 material decisions

- 發布目標：本次正式支援 Windows first；VS Code 1.90+、Python 3.11+、Git、Codex；不宣稱 macOS/Linux。
- 交付形式：交付 VSIX 與 repository，不做 Marketplace 上架。
- 發布門檻：high-risk release 必須有 current isolated Independent Review `passed`，且 advisory 必須在 work item 中有明確 disposition；`unavailable` 不放行。
- 複製安全：host 強制 matching preview ticket；同 panel、同 typed intent、同 snapshot revision 才能 consume，一次性 consume；Refresh、初始化、selection、snapshot 更新會 stale。
- Legacy command：保留 `devweave.copyNextAction` ID，但改為開啟 Control Center/preview；單一 active work 可預選 next，多 work 或無 work 要求明確選取。
- UI 深度：完成核心 path hardening、ARIA/鍵盤/焦點/窄視窗/高對比與繁中 CTA；不做全面視覺重整。
- 版本與回退：升至 0.2.1，bundle version 由 package version 產生，保留 0.2.0 與 0.1.0 VSIX；既有 workspace 不需 migration。
