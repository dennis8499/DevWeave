# 功能驗收：補充 README 與繁體中文使用手冊

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260802-224842-feature-readme -->

## 驗證矩陣

本次驗收使用同一個 current source fingerprint：
`6bd2e70ffb563a416c7ef2da677877b49d9f7a331ce3e0ab01c2688944377a6a`。

| Acceptance | Requirement | 結果 | Current evidence | Tasks |
| --- | --- | --- | --- | --- |
| AC-001 | REQ-001 | 通過；README 說明定位、價值、讀者、前置需求、managed 行為與限制。 | EVID-002 | TASK-001、TASK-003 |
| AC-002 | REQ-002 | 通過；README 提供 hook trust、初始化、公開 `$devweave` 命令與 G1/G2/G3 操作路徑。 | EVID-002 | TASK-001、TASK-003 |
| AC-003 | REQ-003 | 通過；手冊同時涵蓋一般使用者與維護者的日常操作、CLI、Wiki、測試與故障排除。 | EVID-002 | TASK-002、TASK-003 |
| AC-004 | REQ-004 | 通過；CLI help、`doctor`、`project`、`status --all` 與完整 unittest 均以現行介面核對。 | EVID-001、EVID-002 | TASK-002、TASK-003、TASK-004 |
| AC-005 | REQ-005 | 通過；README、手冊與所有 repository-relative links 均解析至存在的檔案或目錄。 | EVID-002 | TASK-001、TASK-002、TASK-003 |
| AC-006 | NFR-001 | 通過；使用者說明為繁體中文，命令、路徑、JSON keys、phase、gate、risk 與 exit code 保留原格式。 | EVID-002 | TASK-001、TASK-002 |
| AC-007 | NFR-002 | 通過；變更限於兩份文件與本 work item 的正規 artifacts/evidence，未改產品 source、tests、Wiki 或 baseline。 | EVID-001、EVID-002 | TASK-003、TASK-004 |
| AC-008 | NFR-003 | 通過；README 聚焦入口與快速開始，詳細命令與維護內容集中於使用手冊，並已做一致性檢查。 | EVID-001、EVID-002 | TASK-001、TASK-002、TASK-003、TASK-004 |

所有 evidence 均為 `status: passed`、`stale: false` 且 `binds_current_source: true`。

## Profile 證據

本 work item 為 `feature`，符合 profile 所需的 acceptance + regression：

| Evidence | Kind | 執行結果 | 覆蓋範圍 |
| --- | --- | --- | --- |
| EVID-001 | `regression` | `unit-tests` exit code `0`；62 tests 全部 `OK`，耗時 109.610 秒。 | AC-004、AC-007、AC-008；TASK-004 |
| EVID-002 | `acceptance` | 文件人工 review、CLI smoke check、連結、scope 與空白檢查均通過。 | AC-001～AC-008；TASK-001～TASK-004 |

EVID-001 由下列 project command 產生：
`python -B -m unittest discover -s tests -v`。
本次另完成 33 組有效 CLI `--help` 檢查，以及 `doctor`、`project`、
`status --all` smoke check；三者 exit code 均為 `0`。

## 基線更新

未更新 `.devweave/baseline/`。已透過 DevWeave CLI 記錄空 targets：

```text
本 work item 僅更新 README.md 與 docs/使用手冊.md；未改變 accepted product、
architecture 或 quality truth，因此不更新 .devweave/baseline。
```

沒有 declared baseline target，也沒有未宣告的 baseline diff。

## Wiki 知識提升

無 Wiki 變更。verification 的 `knowledge status --work` 結果為：

- `affected_pages: []`
- `changed_paths: []`
- `pending_refresh: []`
- `stale_pages: []`
- 沒有 upsert、delete、coupled index/log 或 seal target，因此不建立空的 promotion plan。

Wiki health 仍為 `warning`，唯一 warning 是既有的 `wiki/overview.md` bootstrap
placeholder；此頁不受本次 README 與使用手冊變更影響，故保留現況且不建立 promotion。

## 殘餘風險

無本 work item 產生的 waiver 或阻礙。已知限制是 Wiki 的既有 `wiki/overview.md`
placeholder warning 尚未由本工作補實；這是獨立的知識維護工作，不影響本次文件交付。
文件描述若未來 CLI、phase 或 contract 改變，應透過新的 DevWeave feature work item
同步更新 README 與手冊。

## 驗收結論

README.md 已重整為繁體中文專案入口，`docs/使用手冊.md` 已新增為一般使用者與
維護者共用的詳細參考。兩份文件只保留實際命令與 machine terminology，並通過連結、
CLI smoke、scope、空白與完整 62 項 unittest 驗證。

AC-001～AC-008 全部由 current passing evidence 覆蓋；G1、G2 仍為 current，
baseline 不需更新，Wiki 無 affected page。此 work item 已準備提交 G3 acceptance
review，待使用者明確核准後即可執行 `close`。
