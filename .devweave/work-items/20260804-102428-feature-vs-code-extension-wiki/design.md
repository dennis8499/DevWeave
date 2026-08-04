# 系統設計：修正 VS Code Extension 效能、Wiki 搜尋與完整初始化

<!-- DEVWEAVE:artifact=design version=1 work=20260804-102428-feature-vs-code-extension-wiki -->

## 設計摘要

本次改動維持 Extension 的既有邊界：Host 只讀取 workspace snapshot、在使用者確認後套用固定 bootstrap bundle，Webview 只處理投影與 prompt handoff；不執行 engine、CLI、shell、process 或 network。設計拆成四個深層 module，並以 adapter 隔離既有實作：

- `WikiSearchModel` 是純狀態與篩選 module，保存 draft/applied query、精確 type filter 與 show-all 狀態。Webview controller 只把 input event 寫入 draft；Enter 才 commit，結果 renderer 只更新結果 seam。
- `RefreshCoordinator<Snapshot>` 是 single-flight module。watcher 與手動 Refresh 都只提交 request；coordinator 合併 debounce 後的 burst，在一次 read in-flight 時保留最新 pending request，完成後最多再跑一輪。
- `WorkspaceSnapshotReader` 保留現有 projection contract，將互不依賴的 filesystem read 平行化；每個 operation 使用 local diagnostics，最後依固定 path/id 順序 merge，避免 concurrency 改變輸出。
- `BootstrapInstaller` 先對 manifest 做 read-only inspection，再建立缺少且無 conflict 的檔案。manifest 的 control allowlist 由 build-time bundle contract 產生，Extension 以同一份 contract 做 completeness projection；不同 bytes 永遠不覆寫。

新增 `DashboardSection = "help"` 與 `WorkspaceSnapshot.bootstrap` projection。使用手冊在 build 時嵌入 Webview bundle，只有選取說明分頁時才產生 DOM，不會落地到 target workspace。

## 選項比較

### Wiki rendering

| 選項 | 結果 | 取捨 |
| --- | --- | --- |
| 每個 input event 重建 Knowledge section | 拒絕 | 會重建 input、破壞 selection，並把大型 Wiki 的每次按鍵成本放大。 |
| input event 只更新 draft，Enter 後局部更新結果 | 採用（DEC-001） | 搜尋結果不是即時更新，但游標穩定、DOM 工作量可預測，符合已核准需求。 |
| fuzzy ranking、全文索引或外部搜尋 | 拒絕 | 超出需求且增加排序、儲存、network／安全邊界；本次只做 case-insensitive contains。 |

### Refresh

| 選項 | 結果 | 取捨 |
| --- | --- | --- |
| 每個 watcher event 都直接建立 reader | 拒絕 | burst 時會重疊掃描，較慢的結果可能覆蓋使用者剛看到的 snapshot。 |
| 只關閉 watcher、自動 refresh 改成手動 | 拒絕 | 失去既有自動更新行為。 |
| debounce + single-flight + latest pending | 採用（DEC-002） | 仍保留自動 refresh，只在 burst 中保留必要的最後一輪 read。 |

### Bootstrap repair

| 選項 | 結果 | 取捨 |
| --- | --- | --- |
| 發現一個 conflict 就停止整個安裝 | 拒絕 | 使用者無法安全補齊其他獨立缺檔。 |
| 只建立 non-conflicting 缺檔，保留 conflict 並回報 partial | 採用（DEC-003） | workspace 可能暫時不完整，故 report 與 Dashboard 必須明確列出剩餘缺口；可重跑修復。 |
| 覆寫既有檔案以追求完整 | 拒絕 | 會破壞使用者治理設定，違反 non-overwrite 與安全邊界。 |

### Bundle scope

| 選項 | 結果 | 取捨 |
| --- | --- | --- |
| 複製 repository 的 README、docs、source、tests 與歷史 | 拒絕 | 產生與目標專案不相干的內容，也會擴大 VSIX 與寫入面。 |
| allowlist control suite + embedded help | 採用（DEC-004） | bundle 只包含 DevWeave 執行所需控制內容；完整手冊在 Extension 內讀取，不寫入 workspace。 |

### Snapshot concurrency

| 選項 | 結果 | 取捨 |
| --- | --- | --- |
| 共用 diagnostics array，在平行 callback 中直接 push | 拒絕 | 回報順序會依 timing 改變，測試與使用者診斷不穩定。 |
| operation-local result + deterministic merge | 採用（DEC-005） | 需要小型 result adapter，但可保持既有 projection 與診斷順序。 |

## 介面與資料流

### Webview module 與 seam

`vscode-extension/src/wiki-search.ts` 提供可在 Node unit test 中執行的深層 module：

```ts
interface WikiSearchDocument {
  path: string;
  title: string;
  type: string;
  bodyPreview: string;
}

interface WikiSearchState {
  draftQuery: string;
  appliedQuery: string;
  type: string;
  showAll: boolean;
}

class WikiSearchModel {
  updateDraft(value: string): WikiSearchState;
  submit(): WikiSearchState;
  setType(value: string): WikiSearchState;
  setShowAll(value: boolean): WikiSearchState;
  filter(documents: readonly WikiSearchDocument[]): WikiSearchDocument[];
}
```

`filter` 以 `toLowerCase()` 正規化 title、path、body preview 與 applied query，再以 `includes` 判斷；type 是 exact match，空 query 不限制文字。Webview 的 adapter 保留單一 `#wiki-query` element，input listener 只呼叫 `updateDraft`；keydown Enter 呼叫 `submit`，`wiki-type`、show-all 只更新結果／metric container。`requestAnimationFrame` scheduler 將同一 event loop 的 local render 合併，fallback 使用 queued callback，並不把 input DOM 放入 render output。

Snapshot 到 Webview 的資料流為 `WorkspaceSnapshot.knowledge.pages -> WikiSearchDocument[] -> WikiSearchModel.filter -> #wiki-results`。新 snapshot 只在 host refresh 完成後替換 model documents；輸入期間不重新送 host message，也不掃描 workspace。

`DashboardSection` 增加 `help`。Help adapter 使用 build-time 產生的 `help-content.ts`／靜態字串，按首次選取 help 時才 render；只允許既定 Markdown 的安全純文字／段落／清單投影，所有文字經 escape。CSP 仍為 no network、no inline script；不新增 workspace write 或 command。

### Refresh 與 snapshot seam

`vscode-extension/src/refresh-coordinator.ts` 提供：

```ts
interface RefreshCoordinator<T> {
  request(): Promise<T>;
  dispose(): void;
}

interface RefreshCoordinatorOptions<T> {
  read(): Promise<T>;
  publish(value: T): void;
  onError?(error: unknown): void;
}
```

Coordinator 只有一個 `read()` in-flight；第一次 request 啟動 drain，期間後續 request 只更新 pending generation。當 read 完成，若有 pending 就再跑一輪，並只 publish drain 中最後一個成功結果；所有同輪 caller 等待最新 settled snapshot。error 送到既有 output/error callback，coordinator 清除 running 狀態，下一個 request 仍可恢復。

`ExtensionController.refresh()` 只負責 resolve root、建立 current reader 與 publish snapshot，watcher 的 250ms timer 仍保留並把 event 送至 coordinator。workspace folder 變更會清空 active root、取消舊 coordinator，下一個 root 使用新的 reader，避免跨 repository publish。

`WorkspaceSnapshotReader` 的 read order 是：先取得 project existence、hook、核心 skill 與 manifest-derived bootstrap paths；baseline collection、Wiki collection 與 project JSON 可在無依賴區段平行；project parse 後 work item state/artifact/evidence/events 以 sorted entry 逐項建立 local result。每個 result 帶 `diagnostics`，最後按 `project -> baseline -> knowledge -> work item id -> artifact/evidence/event` 固定順序 merge。projection 的 work sort、Wiki sort、diagnostic order 與現有 contract 不變。

### Bootstrap contract 與狀態

`esbuild.mjs` 建立 schema 1、bundleVersion `0.2.0` 的 allowlist manifest：`.agents/skills/devweave`、`codebase-design`、`diagnosing-bugs`、`grill-me`、`grilling`、`tdd` 的全部 skill files，通用 `AGENTS.md`、`skills-lock.json`、`.codex/hooks.json`、`.devweave/project.json`、三份 baseline、Wiki starter 與必要目錄。source/docs、README、產品 source、tests、fixtures、work-items、history 不進 bundle。manifest 每個 file 保留 source、destination、transform、byteLength、SHA-256；版本與 package JSON 一起更新。

`BootstrapInstaller.inspect()` 是 read-only preflight，回傳 `BootstrapInspection`（expected、missing、conflicts、errors、complete）；`install()` 對同一 bundle 重新檢查，先寫與 conflict 無關的 missing directories/files，既有相同 bytes 為 adopted，不同 bytes 為 conflict。`BootstrapReport` 保留既有欄位，增加 `complete`、`missing`，status 增加 `repaired` 與 `partial`：空 workspace 成功為 initialized，既有 project 的完整補齊為 repaired；仍有 conflict/missing 為 partial，完整既有 bundle 為 already_initialized，integrity／IO／rollback failure 為 failed。`ok` 只有 complete 且無 error/conflict 時為 true。

若 file write 失敗，依反向順序刪除本輪建立的 files，再清理由本輪建立的 directories；既有檔案不動。rollback failure 會保留在 errors 與 rolledBack 中，report 不宣稱 complete。`WorkspaceSnapshot.bootstrap` 由 manifest destination projection 與 workspace stat/hash check 產生，至少包含 `complete`、`expected`、`missing`、`conflicts`，讓 Dashboard 不再用 `projectExists` 代替完整性判斷。初始化 action 會對 complete snapshot 顯示 already initialized，對 partial snapshot 顯示「初始化／補齊 DevWeave」並在確認後執行同一 installer。

### 相容性與資料流邊界

既有 `projectExists`、`hookPresent`、`skillPresent`、knowledge projection、public command 與 protocol message 保留；新增欄位由所有 local snapshot constructors 提供安全預設，舊 workspace 仍可唯讀顯示。`BootstrapWorkspace` 將維持 path normalization、manifest hash validation 與 adapter-only IO。Webview 不新增 Host message type，僅沿用 snapshot/bootstrapResult；Dashboard callback 的 `initialize` 回傳型別向後相容地擴充 report 欄位。

## 失敗模式與回復

| 失敗模式 | 行為 | 回復／降級 |
| --- | --- | --- |
| Wiki query/type renderer exception | 保留現有 input 與最後成功結果，scheduler 清除 pending；錯誤不觸發 Host scan。 | 使用者可重新 Enter 或切換 section；snapshot 不受影響。 |
| watcher burst 或 refresh read error | coordinator 不重疊 read；error 送既有 output channel，保留最後成功 snapshot。 | 下一個 watcher/manual request 重新嘗試；不使用 stale read 覆蓋成功結果。 |
| snapshot 個別檔案讀取或 parse error | operation-local diagnostic 依固定順序 merge，延續既有 critical/warning 語意。 | projection 保留可讀部分，critical 仍使 mutation blocked。 |
| manifest source missing/hash mismatch/path invalid | installer 在寫入前 failed closed；不寫入 target。 | report 列 error，修復 Extension bundle 後再重試。 |
| target parent/file 或不同 bytes | 只列 conflict，略過該 path；其他獨立缺檔繼續建立。 | report partial、Dashboard 顯示 `missing`/conflict；使用者自行處理後可重跑。 |
| file/directory write failure | 停止後續寫入，反向刪除本輪建立的 files/directories；既有 bytes 不變。 | report failed、errors、rolledBack；重新 Refresh 後再決定是否重試。 |
| embedded help unavailable | 不影響 workspace snapshot/bootstrap；顯示最小內建說明 fallback。 | package test 會在 build 時阻止缺檔，runtime 仍維持安全唯讀。 |

## 高風險分析

### Migration

不做 workspace schema migration，也不自動改寫既有 control files。0.2.0 是 additive bundle contract：現有 0.1.0 VSIX 與既有 workspace 皆可保留；Extension 以 inspection 判斷缺口，讓使用者確認後逐檔補齊。新增 `WorkspaceSnapshot.bootstrap` 與 report 欄位只在 Extension 內演進，不要求目標 repository 更新 schema。

### Rollback

Bootstrap write 以 created list 記錄本輪新增，任何 write exception 都反向刪除本輪 files/directories；同 bytes adopted 與既有 conflict 永不進 rollback。Refresh 與 Webview 無外部 durable mutation，因此只需保留最後成功 snapshot／結果。

### Security

維持 `normalizeRelativePath`、source manifest hash/length validation、target non-overwrite、CSP、no process、no shell、no network、no arbitrary public command 與 preview-first。bundle source 使用明確 allowlist，不以整個 repository glob 複製；embedded manual 經 escape，不執行 Markdown/HTML。bootstrap 仍由使用者 modal confirmation 觸發。

### Compatibility

保留 existing 0.1.0 VSIX bytes、public command 名稱、protocol action、snapshot legacy fields、path allowlist 與 no-engine runtime contract。manifest schema 維持 1，只提高 bundleVersion；舊 target 只讀取新檔案，conflict 不覆寫。新增 help section 與 bootstrap 欄位會更新所有 Extension fixtures 與 unavailable/default projections。

### Performance

輸入事件不再做 section-wide `innerHTML`，Enter/type/show-all 只更新結果 seam；scheduler 在 animation frame 合併 local render。watcher 250ms debounce 加 coordinator single-flight 限制 workspace scan；snapshot 以 `Promise.all` 平行獨立 reads，再 deterministic merge。以 call-count、max concurrent read、large-Wiki fixture 與 package smoke test 驗證，不加入 production telemetry。

### Not applicable

不新增 database、external service、network protocol、process execution、CLI schema、branch/worktree、migration script 或 production instrumentation，因此 database migration、network rollback 與 deployment rollback 不適用；上述 security／workspace rollback 足以涵蓋本工作寫入面。

## 設計決策

## DEC-001: Enter commit 與局部 Wiki render
- Requirements: REQ-001, REQ-002, NFR-001
- Decision: 採用 `WikiSearchModel` 的 draft/applied state；input 不 render，Enter 才套用 case-insensitive contains，結果與 metric 以 stable DOM seam 局部更新。
- Rationale: 同時消除 DOM replacement 造成的倒序／游標問題與大型 Wiki 每鍵全量 render 成本。
- Consequences: 使用者需按 Enter 才看到文字搜尋結果；分類與顯示全部仍可立即套用，測試可直接驗證 model 與 render target。

## DEC-002: Refresh single-flight coordinator
- Requirements: REQ-003, REQ-004, NFR-001
- Decision: watcher debounce 與 manual refresh 共用 `RefreshCoordinator`，單一 in-flight，pending 只保留最新 generation。
- Rationale: 保留既有自動 refresh，又避免 burst 重疊掃描與舊結果回退。
- Consequences: burst 期間 UI 會等最後一輪 snapshot；coordinator 必須處理 error/retry 與 workspace root replacement。

## DEC-003: Non-conflicting partial bootstrap repair
- Requirements: REQ-005, REQ-006, NFR-002
- Decision: read-only inspect 後只建立缺檔；same bytes adopted；different bytes、parent type conflict 不覆寫，其他 path 照常處理，report 以 partial 表示未完整。
- Rationale: 避免破壞使用者治理，同時讓不相干缺口可恢復，符合「只建立無衝突缺檔」決策。
- Consequences: 需要 `missing`／`conflicts` projection 與可重跑修復 CTA；install 不再以第一個 conflict 中止全部寫入。

## DEC-004: Allowlisted complete control bundle
- Requirements: REQ-005, REQ-007, REQ-008, NFR-002
- Decision: manifest 只打包六組核准 skills、AGENTS、skills lock、hook、project、baseline、Wiki starter；使用手冊只嵌入 Extension help。
- Rationale: 使新 workspace 具備完整 DevWeave 控制面，又排除 README/docs、source、tests、fixtures、work/history 與不必要 workspace writes。
- Consequences: build script 必須對 companion/AGENTS/lock 做明確來源與 manifest integrity 驗證；help 內容不會出現在 target repository。

## DEC-005: Local diagnostics with deterministic merge
- Requirements: REQ-004, NFR-001
- Decision: 平行 filesystem operation 各自回傳 projection/diagnostics，依固定 category/path/id merge；不共用可變 diagnostics array。
- Rationale: concurrency 降低 snapshot latency，同時保持現有排序與 diagnostic semantics 可重現。
- Consequences: reader 需要 operation result type 與較多 merge code；targeted test 需檢查 concurrency 與 exact ordering。

## DEC-006: Manifest-derived completeness projection
- Requirements: REQ-006, REQ-007, REQ-008
- Decision: snapshot reader 使用 build manifest 的 destination/hash contract（測試／無 bundle 時使用安全 default）計算 bootstrap expected/missing/conflicts/complete；`projectExists` 僅表示單一檔案存在。
- Rationale: dashboard 的完整性判斷必須與 installer 同一套 control contract，避免 project-only false positive。
- Consequences: reader options 增加 contract input，Extension 需懶載入並快取 manifest；legacy fixtures 提供 default projection。

## DEC-007: 0.2.0 additive package with preserved 0.1.0 artifact
- Requirements: REQ-008, NFR-002
- Decision: package.json、bundle manifest 與新 VSIX 使用 0.2.0；既有 dirty `0.1.0.vsix` 只讀保留，package verification 以不同 output path 產出新檔。
- Rationale: 可驗證新 package，又不破壞使用者現有 artifact 與未提交修改。
- Consequences: package/smoke test 要檢查 version、manifest、VSIX entries 與 old artifact hash／存在性。

## DEC-008: Embedded local help as lazy section
- Requirements: REQ-007, NFR-002
- Decision: 將既有使用手冊在 build 時轉成 Extension-local escaped content，help section 首次開啟才 render；不新增 workspace file 或 network request。
- Rationale: 使用者可在 Extension 內理解初始化、workflow、Wiki、Gate、companion 與安全邊界，而 target repository 不被 docs 汙染。
- Consequences: help content 是 package input，需在 package test 驗證存在；內容更新跟著 Extension release。
