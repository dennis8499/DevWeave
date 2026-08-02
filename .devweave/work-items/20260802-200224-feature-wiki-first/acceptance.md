# 功能驗收：整合 Wiki-first 探索與知識提升

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260802-200224-feature-wiki-first -->

## 交付摘要

DevWeave 現在以單一 router 提供 Wiki-first G1 探索與 verification/G3 知識提升：目標 repo 會非破壞性取得 root `wiki/` 骨架；頁面以 frontmatter、current-source SHA-256、work provenance、index、wikilink 與 append-only log 驗證。Product source、living baseline 與 knowledge 使用獨立 fingerprint；只有本 work item 實際影響的既有頁面需要刷新或刪除。

公開 chat verbs、schema version 1、JSON envelope、Codex-only surface 與單一 PreToolUse hook 均維持相容。本次依核准假設沒有替 DevWeave framework repository 自身建立 root `wiki/`；目前 work 因建立於功能上線前而走 legacy compatibility，不接受追溯性 knowledge blocker。

## 驗證矩陣

| AC | 驗收結果 | Tasks | Current evidence |
| --- | --- | --- | --- |
| AC-001 | Bootstrap 重跑冪等；相容 Wiki 採用且不覆寫；缺 index 或同名 starter 衝突 fail closed 並由 doctor 回報。 | TASK-001, TASK-005 | EVID-003, EVID-004, EVID-005 |
| AC-002 | G1 強制 index-first、最多五頁、gap fallback 與 context fingerprint；status/instructions 顯示 health。 | TASK-002, TASK-004, TASK-005 | EVID-003, EVID-004, EVID-005 |
| AC-003 | Source overlap 只標記 affected pages；未 plan/refresh 阻擋，合法 upsert/delete/index/log/seal 通過，無命中不要求理由。 | TASK-002, TASK-004, TASK-005 | EVID-003, EVID-004, EVID-005 |
| AC-004 | `new` profile 的 overview 必須 active、有 sources、current fingerprint 與 current work provenance。 | TASK-002, TASK-005 | EVID-003, EVID-004, EVID-005 |
| AC-005 | 11 種 page type、必要欄位、status、type path 與 decision/dependency 附加欄位均由 deterministic lint 檢查。 | TASK-001, TASK-005 | EVID-003, EVID-004, EVID-005 |
| AC-006 | File、directory、tracked、non-ignored untracked、dirty、rename、delete 與 symlink/path escape 邊界使用 current-content fingerprint。 | TASK-001, TASK-005 | EVID-003, EVID-004, EVID-005 |
| AC-007 | Broken/ambiguous wikilink、index completeness/section、source mismatch 與 log rewrite 的 critical/warning 分界符合契約。 | TASK-001, TASK-004, TASK-005 | EVID-003, EVID-004, EVID-005 |
| AC-008 | `knowledge status/context/plan/seal` 維持單一 UTF-8 JSON、既有 exit code 與 engine-only ledger mutation。 | TASK-002, TASK-003, TASK-005 | EVID-003, EVID-004, EVID-005 |
| AC-009 | Wiki 排除於 product fingerprint；Wiki-only drift 保留 evidence current 但使已核准 G3 stale。 | TASK-002, TASK-005 | EVID-003, EVID-004, EVID-005 |
| AC-010 | Guard 在 G2 前與 implementation 拒絕 Wiki；verification/acceptance 只允許 planned paths 與 coupled index/log。 | TASK-003, TASK-005 | EVID-003, EVID-004, EVID-005 |
| AC-011 | 缺 knowledge fields 的 schema v1 state 可載入且無追溯 blocker；project 只在明確 mutation 補齊，舊 Wiki 漸進 seal。 | TASK-001, TASK-002, TASK-004, TASK-005 | EVID-003, EVID-004, EVID-005 |
| AC-012 | Repository 仍只有 `devweave` skill；metadata、phase references、contracts、AGENTS 與 README 同步，公開 verbs 未增加。 | TASK-004, TASK-005 | EVID-003, EVID-004, EVID-005 |
| AC-013 | Runtime 僅用 Python standard library；paths 正規化為 repo-relative POSIX，commands 維持 `shell=false`。 | TASK-001, TASK-005 | EVID-003, EVID-004, EVID-005 |
| AC-014 | Traversal、中間 symlink escape、root 外 target、conflict、未授權 seal 與 log rewrite 均 fail closed；atomic temp writes 有回歸覆蓋。 | TASK-001, TASK-003, TASK-005 | EVID-003, EVID-004, EVID-005 |
| AC-015 | 原 48 項與新增 12 項共 60 項通過；skill quick validation、diff check 與完整暫存 fixture lifecycle 通過。 | TASK-004, TASK-005 | EVID-003, EVID-004, EVID-005 |

## Profile 證據

- EVID-003（regression）：`python -B -m unittest discover -s tests -v`，60/60 通過，exit code 0，source fingerprint `2f1ad5eebab7465ddc28bb0fffdab7cf09095bd82c621db334df0b270a1a463b`。
- EVID-004（acceptance）：暫存 Git fixture 完成 `init → feature → G1/G2 → source change → affected Wiki refresh/seal → G3 → close`；skill quick validation 通過。
- EVID-005（review）：完成 migration、rollback、path/symlink security、schema v1 legacy、fingerprint separation、single-hook boundary、performance 與 G3 reconciliation review。
- EVID-001 與 EVID-002 綁定較早 source fingerprints，已由 engine 標記 stale；不作為本次 G3 判定依據。

## Wiki 知識提升

此 framework work item 沒有 `base_knowledge`，`knowledge status` 明確回報 `legacy_work: true` 與 `bootstrap_pending`。依核准假設，本次不在 framework root 建立 Wiki，也不建立空的 knowledge plan 或「無更新」machine rationale。完整 knowledge promotion 已在暫存 fixture 中驗證；下一個新 work item 會於 `start` 非破壞性補齊 skeleton 並啟用完整 G1/G3 contract。

## 基線更新

- `.devweave/baseline/product.md`：記錄 Wiki-first exploration、verified promotion、baseline/Wiki 分工與 non-goals。
- `.devweave/baseline/architecture.md`：記錄 knowledge core、state/CLI/guard 邊界、三個 fingerprint domains 與 additive compatibility。
- `.devweave/baseline/quality.md`：記錄 determinism、path safety、60 項 suite、skill validation、hook 限制與 performance 約束。

三個路徑已透過 `baseline --target` 完整宣告，沒有未宣告或宣告但未變更的 baseline target。

## Waivers

無。本工作沒有 missing-command、out-of-scope 或其他 waiver。

## 殘餘風險

- Hook 仍是 Codex guardrail，不是 OS sandbox；外部 editor 或停用 hook 的寫入只能在 G3 完整 diff/lint reconciliation 被偵測。
- Wiki 的語意矛盾與模組重要性需要 Agent／人類判斷；deterministic lint 只負責結構、來源與 provenance。
- 大型 directory source 可能增加 hashing 時間；初版以單次 Git listing、sorted paths、streaming hash、最多五個 sources 與 bounded health payload 控制，暫不加入 cache。
- Windows 完整 suite 在本環境約 164 秒；`unit-tests` timeout 已調整為 240 秒以保留執行餘裕。

## 驗收結論

AC-001～AC-015、TASK-001～TASK-005、feature acceptance/regression 與 high-risk review 均有 current evidence；required command、scope、baseline declaration、legacy knowledge policy與文件契約皆通過。此變更已具備提交 G3 人工核准的條件，但尚未自行核准或關閉工作項。
