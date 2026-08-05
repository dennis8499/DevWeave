# 功能驗收：建立 Plan-first 原生問答流程

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260805-094544-feature-plan-first -->

## 驗證矩陣

本次驗證的 current product source fingerprint 為 `f284f8c090acc2f4bc99441611aeffec98ab4b35b355930ef7bba55f0eea52af`，Git HEAD 為 `2a9a33234cf212ed51b1a32b15a8cadf3836a05c`；Wiki knowledge fingerprint 為 `8ff5874df3bfd96df9b904d2affbcf61e09a91a0508c26bbd58164b8c35690d1`。

| 驗收條件 | 任務 | current evidence | 結果 |
| --- | --- | --- | --- |
| AC-001 G1 在 Plan Mode 使用原生問答 | TASK-001、TASK-004 | EVID-018、EVID-014 | 通過；current host 的 Plan Mode 可見 `request_user_input`，原生 round-trip 遵循單題與回答後才繼續的邊界。 |
| AC-002 G2 在 Plan Mode 使用原生問答 | TASK-001、TASK-004 | EVID-018、EVID-014 | 通過；G2 design decision 使用同一 shared contract，G2 approval 前不進入 product/tracked-test mutation。 |
| AC-003 Native payload contract | TASK-001、TASK-003、TASK-004 | EVID-018、EVID-014 | 通過；一題、二至三個互斥選項、第一項 `(Recommended)`、描述與 host `Other` 已由 host evidence 與 repository contract 驗證。 |
| AC-004 Native answer return 與 invalid safety | TASK-001、TASK-003、TASK-004 | EVID-019、EVID-014 | 通過；valid result 保留 question identity；cancel/timeout/malformed host callback 在本環境無 injection seam，EVID-019 以 compatibility limitation 記錄，contract tests 驗證 pending/no-guess/no-mutation。 |
| AC-005 Ordinary pre-G2 回到 Plan Mode | TASK-001、TASK-002、TASK-004 | EVID-018、EVID-014 | 通過；ordinary/Skill context 看不到工具時停止並回到 Plan Mode，不修改 artifact、不 approve、不開始 implementation。 |
| AC-006 Structured fallback compatibility | TASK-001、TASK-002、TASK-003、TASK-004 | EVID-018、EVID-014 | 通過；只有無法切換或明確 compatibility 才使用同格式 numbered fallback 與 custom answer。 |
| AC-007 Post-G2 ordinary implementation boundary | TASK-001、TASK-002、TASK-004 | EVID-018、EVID-014 | 通過；本 work 僅在 current G2 後執行 approved tasks；新 material decision 的規則是停止並 `revise`。 |
| AC-008 Gate answer safety | TASK-001、TASK-003、TASK-004 | EVID-018、EVID-014 | 通過；native answer 只是 intent，validation 與既有 `approve`/`revise` CLI contract 仍是權威，cancel/ambiguous 不推進 Gate。 |
| AC-009 Companion Skill consistency | TASK-002、TASK-003、TASK-004 | EVID-018、EVID-014、EVID-016 | 通過；五個 governed companion 共用 native-question contract，沒有 parallel router、question state、ledger 或 Extension UI。 |
| AC-010 Host capability 不被誤標 | TASK-001、TASK-004 | EVID-018、EVID-014、EVID-016 | 通過；ordinary/Skill native visibility 明確記錄為 unavailable compatibility，不把 policy 或 fallback 宣稱為 native support。 |
| AC-011 Existing contract compatibility | TASK-002、TASK-003、TASK-005 | EVID-018、EVID-014、EVID-015、EVID-016、EVID-017、EVID-012、EVID-013 | 通過；CLI/artifacts/state schema、Extension prompt handoff、no-direct-Codex-API 與既有 tests/typecheck/smoke 保持相容。 |
| AC-012 Verification coverage | TASK-003、TASK-004、TASK-005 | EVID-019、EVID-014、EVID-015、EVID-016、EVID-017、EVID-012、EVID-013 | 通過；Python/Extension checks、Plan Mode/manual capability、fallback、invalid-result safety、pre/post-G2 與 dirty artifact preservation 均有 current evidence。 |

EVID-001 至 EVID-011 是 package/dirty artifact 穩定前的早期 attempt，engine 已將受 fingerprint 影響的 evidence 標 stale，不作為 current passing coverage。EVID-009 是 sandbox 內 smoke 的環境失敗：esbuild 讀取既有 repository path 被拒絕；同一 command 在核准的 sandbox 外重跑為 EVID-010，最後穩定後再以 EVID-017 通過。EVID-011 的 package command 通過並驗證 58 bootstrap files/118 VSIX entries，但 package-vsix 改寫了使用者原有 dirty VSIX；原 bytes 已還原，故 EVID-011 因 source fingerprint 改變而 stale，並由 WAIVER-001 窄幅處理 current command requirement。EVID-007 沒有建立 evidence，不作為驗收依據。

## Profile 證據

本 Work Item 是 standard feature，已具備 feature profile 的 acceptance 與 regression evidence：

- `python -B -m unittest discover -s tests -v`：97 tests，1 個既有 skip，全部其餘通過（EVID-014）。
- `npm.cmd run typecheck`：通過（EVID-015）。
- `npm.cmd run test`：73/73 通過（EVID-016）。
- `npm.cmd run test:smoke`：在 sandbox 外完成 Extension build/host activation/smoke（EVID-017）。
- `npm.cmd run package`：產生並驗證 0.2.1 package 的 58 bootstrap files、118 VSIX entries（EVID-011）；因保護使用者 dirty VSIX，current command fingerprint 由 WAIVER-001 明確豁免，保存結果見 EVID-012。
- `git diff --check`：無 whitespace error，只有 Windows checkout 的 LF/CRLF conversion warnings（EVID-013）。

## 知識審查與 Wiki 提升

Knowledge Review 為 `promote`。理由是 Plan-first 入口、canonical `request_user_input` seam、ordinary/Skill host boundary、structured fallback、G2 後 `revise` 與 no-new-state boundary 會持續影響後續 work item，屬 durable reusable knowledge。

- affected pages：`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`。
- plan：三個 content upsert、零 delete；engine coupled `wiki/index.md` 與 `wiki/log.md`。
- 所有三個 affected pages 與 coupled pages 已 active、sourced、current、indexed、logged 並由 `knowledge seal` 以本 work ID 封存；沒有 placeholder、template token、critical lint、uncovered changed path 或 unsealed page。
- `knowledge status --work` 顯示 `health=healthy`、`bootstrap.complete=true`、`pending_refresh=[]`、`uncovered_changed_paths=[]`。

## 基線更新

沒有 baseline content 變更，也沒有 migration。既有 accepted baseline 已涵蓋 native-first/fallback、single router、G2 write boundary、Extension prompt handoff 與 no-new-state 治理語義；本 work 只將更精確的 Plan-first/host seam policy 落在 router、Skills、使用者文件與 Wiki。因沒有 baseline diff，不宣告 baseline target。

## 殘餘風險

- `WAIVER-001`（`missing-command`, acceptance, `extension-package`）只處理 package command 通過後為保護使用者 pre-existing dirty VSIX 而還原原 bytes 的 fingerprint 例外；不涵蓋其他 Extension source 或 behavior。
- 目前 Codex host 的 `request_user_input` 保證路徑是 Plan Mode；ordinary/Skill context 未暴露工具，因此本 work 不宣稱其 native support。host 後續支援普通模式時，仍需新的 current host integration evidence。
- cancel/timeout/malformed host result 在目前 host 沒有 callback injection seam，EVID-004 以 waived compatibility 記錄；shared contract 與 Python regression 已固定 invalid/no-guess/no-mutation 行為。
- sandbox 內的 EVID-009 是環境 access-denied warning，已由 sandbox 外 EVID-010 取代；不代表產品或 Extension behavior failure。

本 work 為 standard risk，不啟動 high-risk Independent Review Agent；這符合既有 G3 policy。

## 驗收結論

本 work 已完成 Plan-first native question contract、router/phase policy、五個 companion Skill、README/使用手冊同步、contract tests、host/manual evidence、完整 standard verification 與 Wiki promote/seal。工具可見時使用原生 Plan Mode 視窗；工具不可見時停止回 Plan Mode 或只在明確 compatibility 下 structured fallback；未回答或 invalid result 不得修改 artifact、approve Gate 或推進 phase。現在只等待使用者明確 G3 approval；在 approval 前不執行 close。
