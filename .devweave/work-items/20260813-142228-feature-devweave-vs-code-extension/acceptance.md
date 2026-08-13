# 功能驗收：強化 DevWeave VS Code Extension 治理、驗證與效率

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260813-142228-feature-devweave-vs-code-extension -->

## 驗證基線

- Work Item：`20260813-142228-feature-devweave-vs-code-extension`；G1 scope 與 G2 build 均已核准且仍 current。
- Git HEAD：`40823cf6e448da9a69667cdf74b2da2923d687d4`。
- Current product/source fingerprint：`4e652d235dc9017ae862bd146885cba7160c1b5788a0d607533b615635243985`。
- Final Knowledge fingerprint：`7880b7876a58c8d2a396755671543e0aed76a14cc3f274325252640695774220`。
- High profile batch：`VB-322c90e4dc04`，9/9 selected commands passed、0 skipped；selective batch：`VB-506cbd547ad4`，2 selected、7 skipped，0 dependency closure。

## 驗證矩陣

| Acceptance | 結果與 current evidence |
| --- | --- |
| AC-001 Path kind regression | 通過但受環境限制：EVID-085、EVID-086、EVID-090、EVID-091 覆蓋 path kind、bootstrap conflict、typecheck 與 guard boundary；Windows symlink privilege 造成 1 項 skip，列為 reviewer F-005 advisory。 |
| AC-002 Authority-safe readiness | 通過：EVID-085、EVID-087、EVID-090；snapshot/readiness 維持 projection-only，沒有把 filesystem projection 當成 engine Gate passed。 |
| AC-003 Summary-first snapshot | 基本情境通過：EVID-085、EVID-087 覆蓋 summary/detail lazy read、單檔 bounded artifacts 與 refresh concurrency；reviewer F-003 指出 aggregate detail count/bytes 與 I/O-level bound 尚未建立，列為 advisory。 |
| AC-004 Wiki traceability | 已覆蓋既有 stale/missing-frontmatter 診斷：EVID-085、EVID-092 通過；reviewer F-004 指出 unsupported frontmatter field types 仍可能被丟棄而沒有 parse diagnostic，列為 advisory。 |
| AC-005 Reproducible package | 通過：EVID-084、EVID-085、EVID-089；0.2.3 candidate 305154 bytes／119 entries，manifest SHA-256 `8a3ea557bc791fc0984aeec9e678387f5b75f585aa96b481f6ab16a4c01cfe51`，VSIX SHA-256 `f883dc2a85d95c963501bb3b913e67d31d0769f815fd5bfa878f66644dbbcad1`，驗證後才 promotion，current/retained artifact failure tests 通過。 |
| AC-006 Pinned smoke | 通過：EVID-087；使用 cache-only VS Code 1.131.0 Extension Host，activation 結束 code 0，未下載或 fallback。 |
| AC-007 Impact-based verification | 通過：EVID-093、EVID-094；`--path vscode-extension/src/filesystem.ts` 只選 Extension tests/typecheck，selected=2、skipped=7，package 為 release-only，smoke 因 release-only dependency 被排除；EVID-084..EVID-092 的 high profile 仍完整執行。 |
| AC-008 Metrics availability | 能力與 normalization regression 通過：EVID-088、EVID-089、EVID-090、EVID-093、EVID-094 覆蓋 bounded schema、selection 與 unavailable normalization；但本輪 EVID-084..EVID-094 的實際 metrics 只有 duration/verification，未寫入 context/tool/explicit unavailable usage，依 reviewer F-001 收窄為 residual advisory，不宣稱 current run 已保存 exact usage。 |
| AC-009 Bootstrap readiness | 通過：EVID-085、EVID-087、EVID-090；fresh bootstrap commands 空集合顯示 setup handoff，Extension 不直接執行 command set。 |
| AC-010 Single reviewer dual axis | 通過但帶 advisory：唯一 reviewer 以 isolated/read-only context 執行，EVID-095 由 machine-only `review record` 寫入，覆蓋全部 AC/TASK，結果 `passed`／advisory，無 critical finding。 |
| AC-011 Security boundary regression | 通過：EVID-085、EVID-086、EVID-087、EVID-091；Extension 無 process、shell、network、Git/Codex API 或 arbitrary write path，bootstrap write 維持 explicit confirmation/rollback。 |
| AC-012 Evidence reconciliation | 通過待人工 G3：EVID-084..EVID-095 全部 current/pass；version 0.2.3、58 bootstrap files、119 VSIX entries、88 Extension tests、Python 111 tests（1 symlink skip）、Git HEAD、source fingerprint、baseline、scope、Wiki promote 與 current review 已對齊。 |
| AC-013 Efficiency benchmark | 部分達成且不宣稱未測量的百分比：EVID-093/094 證明 affected-path selection 將本次代表性檢查縮為 2/9，high profile 保留 9/9；但 repository 沒有同一 commands/evals 的歷史 context-byte、snapshot-latency 與 low-risk wall-time baseline，因此不能誠實宣稱 30%／25%／30% 改善，原因與 residual risk 已記錄。 |

## Profile 證據

- Evidence ledger accounting：`EVID-075`、`EVID-076`、`EVID-077`、`EVID-078`、`EVID-079`、`EVID-080`、`EVID-081`、`EVID-082`、`EVID-083`、`EVID-084`、`EVID-085`、`EVID-086`、`EVID-087`、`EVID-088`、`EVID-089`、`EVID-090`、`EVID-091`、`EVID-092`、`EVID-093`、`EVID-094`、`EVID-095`、`EVID-096` 均已納入本 acceptance；其中 EVID-075..083 為 superseded history，EVID-084..096 為 final/current 或 acceptance/review record。
- Superseded pre-final evidence：EVID-075..EVID-083 是 Wiki final source coverage 完成前的 high-profile run，已由 seal 後的 EVID-084..EVID-092 取代 current verification；它們保留在 evidence ledger 作為歷史 provenance，未用於 current pass 判定。
- High regression：`VB-322c90e4dc04` → EVID-084 `extension-package`、EVID-085 `extension-tests`、EVID-086 `extension-typecheck`、EVID-087 `extension-smoke`、EVID-088 `unit-tests-cli`、EVID-089 `unit-tests-contract`、EVID-090 `unit-tests-core`、EVID-091 `unit-tests-guard`、EVID-092 `unit-tests-knowledge`；全部 `passed`、current、source-bound，high full-set 無 skipped command。
- Standard affected-path：`VB-506cbd547ad4` → EVID-093 `extension-tests`、EVID-094 `extension-typecheck`；全部 `passed`，selected=2、skipped=7、dependency closure=0。
- Independent Review：EVID-095，reviewer `019ffb2b-cfd3-7582-9de5-8e3e5b69735e`，`isolated_read_only`，`passed`／`advisory`，report SHA-256 `7cf62de9a0668da48183d42d6fd756beba4e8be3a5b9384e6aa8627db1fbf609`；findings F-001..F-005 均為 advisory，無 waiver、無 critical block。
- Python full suite：111 tests，1 項 Windows symlink privilege skipped；Core 45 tests 同樣 1 skipped，CLI 22、contract 16、guard 12、knowledge 16 均通過。
- Extension：88/88 unit tests、typecheck 通過；pinned VS Code 1.131.0 cache-only smoke 通過。

## 基線更新

已更新 `.devweave/baseline/quality.md`，以最小必要 diff 固化：0.2.3 candidate-first package/verifier/atomic promotion/retained-artifact failure contract、affected-path profile selection 與 release-only exclusion、bounded metrics 上限（250,000 bytes／10,000,000 numeric）及 usage unavailable/null semantics、88 項 Extension 測試、現行命令與 accepted runtime。沒有修改其他 baseline、state、event 或 evidence ledger。

## Wiki 知識提升

- Knowledge Review disposition：`promote`；rationale 為本次形成可跨工作重用的 summary-first projection、typed path/conflict semantics、candidate-first VSIX provenance transaction、affected-path verification selection 與 bounded metrics/usage unavailable 邊界。
- Affected pages：`wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/vscode-extension.md`。
- Planned upserts：上述四頁；coupled：`wiki/index.md`、`wiki/log.md`；未刪除頁面。已記錄單一 work-attributed promote entry，並由 engine seal 六個 targets。
- Durable coverage：final `knowledge status` 為 `health=healthy`、`pending_refresh=[]`、`stale_pages=[]`、`uncovered_changed_paths=[]`、`unsealed_pages=[]`、`warnings=[]`；三個初始 uncovered engine test paths 與 repository contract test 已納入 `knowledge-engine` page 的五個 source 上限內。
- Wiki 不含 placeholder/template token，未建立新 lifecycle、ledger 或 alternate planning document。

## 獨立 Review

- 狀態：已完成唯一 router 啟動的 isolated read-only reviewer；EVID-095 為 current `passed`／advisory。沒有 critical security、data-loss、irreversible 或 scope finding，G3 可在 advisory warning 下等待人工核准。
- Reviewer scope：只讀 approved artifacts、完整 diff、scope、baseline、Wiki context、Git HEAD 與 current EVID-084..EVID-094；未修改 source/Wiki/ledger/cache log，未 delegate，也未執行 approve、revise 或 close。
- Advisory findings：F-001（current evidence 未含 context/tool/explicit unavailable usage）、F-002（`usage.cost` ceiling 文件與實作邊界不一致）、F-003（detail aggregate count/bytes/I/O bound）、F-004（unsupported frontmatter type diagnostics）、F-005（symlink privilege skip）。這些 advisory 未以 waiver 偽裝解除，已於矩陣與 residual risks 明確保留。

## 殘餘風險與限制

- Python full suite 有 1 項 Windows symlink privilege skip；這是認證環境權限限制，不解讀為產品 failure；若要宣稱完整 symlink coverage，需在具權限的同一 build 補驗。
- Codex host 未提供 exact token/cost usage；證據使用 unavailable/null，Extension 不估算 Token 或 cost。
- Reviewer F-001：本輪 governed evidence 的實際 metrics 未含 context/tool/explicit unavailable usage；normalization 與 projection contract 有測試，但 current evidence 不宣稱已提供精確 usage。
- Reviewer F-002：`usage.cost` 目前只保證 finite/non-negative，與 baseline 對 numeric metrics 的 10,000,000 ceiling 存在文件／實作差異；未在本 Work Item 內擴張 G2 scope 修正。
- Reviewer F-003/F-004：Work Item detail aggregate I/O bound 與 Wiki unsupported frontmatter typed-field diagnostics 尚未完整；目前保留既有 per-file/stale diagnostics，後續需另行 revise/feature 才能修改。
- Reviewer F-005：symlink privilege skip 已由 EVID-090 與本 acceptance 明確揭露；未宣稱完整 symlink coverage。
- AC-013 的百分比改善目標未宣稱達成，因缺乏同一 commands/evals 的歷史 baseline；目前只證明 selective selection 與 high coverage preservation。
- 認證範圍限 Windows x64／VS Code 1.131.0／Python 3.14.6／Git 2.51.0.windows.1／目前 Codex host；不延伸 Marketplace、跨平台或舊版 binary rollback 承諾。
- 目前 artifact 發布採 current/retained bytes preservation；事故處理是停止散布、停用或解除安裝並以新版本修復，不自動刪除 workspace、Wiki 或 `.devweave` 資料。

## 驗收結論

G1/G2 核准範圍內的 TASK-001 至 TASK-006 已實作並完成 current high/standard verification，產品、baseline、declared Wiki promote 與唯一 Independent Review 已穩定。EVID-095 無 critical block，但保留五項 advisory 與一項 symlink skip；目前只等待使用者對這份 G3 acceptance 與 residual warnings 作明確核准，核准前本 Work Item 不可 close。
