# 系統設計：DevWeave 0.2.1 current-version-only release contract

<!-- DEVWEAVE:artifact=design version=1 work=20260805-120943-feature-devweave-0-2-1-current-version-only-rele -->

## 設計摘要

選定方案是在既有 `verify-package.mjs` package-verification **Module** 內收斂 current-version-only policy。它的 **Interface** 維持 `npm.cmd run package`：caller 只需知道 package 會從 `package.json` 導出版本、產生同版 VSIX，對 bootstrap manifest/source integrity 與 archive entries fail closed，成功時輸出版本、entry counts 與 current artifact SHA-256。

**Seam** 分成兩層但不增加 public surface：`package-version.test.ts` 對 source contract 做快速 regression，實際 `verify-package.mjs` 對剛產生的 VSIX bytes 做 integration verification。單一 package implementation 不需要 Adapter。這個設計保留深度與 locality：版本導出、檔案型別、archive parsing、metadata、bootstrap hashes 與必要 entries 仍集中在 verifier；docs/help/baseline/Wiki 只投影同一產品決策。

關鍵不變量：只處理 `package.json.version === 0.2.1`；舊 `.vsix` 完全不讀取；current VSIX 必須是 non-empty regular file；archive 與 bootstrap integrity 驗證不得放寬；public chat/CLI/schema/hook/bootstrap command contracts 零變更；Wiki 到 verification 前唯讀。

## 選項比較

### 選項 A：由 current package version 驅動單一 verifier（選定）

- `packageJson.version` 同時決定 output path、bundleVersion、VSIX metadata 與 verifier target。
- 移除 legacy artifact array，但對 current VSIX 增加 explicit regular-file／non-empty／SHA-256 observation。
- Unit test 檢查 source policy 不含 legacy list，integration verifier 檢查真實 archive。
- 優點：最小 interface、單一真實來源、unit 與 package 可各自診斷；符合 current-only 決策。

### 選項 B：舊版 artifact 存在時才選擇性驗證（淘汰）

- 缺檔不失敗，但存在時仍驗 legacy hash。
- 淘汰原因：保留已被使用者排除的 release policy，並讓驗收結果依工作目錄殘留檔而變動，降低 determinism。

### 選項 C：新增支援版本矩陣／設定檔（淘汰）

- 將 current 與 legacy versions 放入可配置 manifest。
- 淘汰原因：目前只有一個實作與一個交付版本，新增淺層 Adapter／configuration seam 沒有第二個真實 consumer，增加維護與誤設風險。

## 介面與資料流

1. `package.json.version` 由 esbuild 讀取，產生 `dist/bootstrap/manifest.json.bundleVersion` 與 current bootstrap source hashes。
2. `package-vsix.mjs` 以同一 version 組出 `devweave-control-center-${version}.vsix`，排除任何 `.vsix` 輸入並使用固定排序／ZIP metadata。
3. `verify-package.mjs` 驗證 version 為 0.2.1、current path 是 non-empty regular file、bootstrap hook／destinations／compatibility/source hashes 正確，再解析 current VSIX 檢查 package metadata、manifest version 與 required entries；最後計算並輸出 current SHA-256。
4. `package-version.test.ts` 不再依賴 prebuilt binary；它讀取 package、lock、esbuild 與 verifier source，正向檢查 current-derived seam，反向拒絕 `legacyArtifacts`／0.1.0／0.2.0 policy 回歸。
5. Repository contract test只掃描現行 public docs、Extension Help 與 accepted source-facing release文字；append-only `wiki/log.md` 歷史不納入禁止字串。Baseline 與 Wiki 在 G3 依 lifecycle 更新並由 acceptance text audit 對齊。
6. 公開文件把 VS Code 1.90+／Python 3.11+ 描述為技術門檻，把 Windows x64 build 10.0.26200／25H2、VS Code 1.131.0、Python 3.14.6、Git 2.51.0.windows.1 與目前 Codex host 描述為本次認證環境。

沒有新 API、JSON key、state transition 或 runtime data migration。唯一新增的可觀測輸出是 package verifier 的 current VSIX SHA-256。

## 失敗模式與回復

- Package version 不是 0.2.1、current VSIX 缺少／非 regular／空檔、ZIP 無法解析、metadata 或 required entry 缺失、bootstrap hash／length／policy 漂移：verifier nonzero fail closed，禁止發布。
- Unit regression 發現 legacy policy 或 version derivation 漂移：Extension suite 失敗，先修復 source contract，不以 skip／waiver 放行。
- Public docs、Help、baseline 或 Wiki 留下現行舊版回退承諾：repository contract／G3 bounded audit 失敗。
- Source 或 artifact bytes 在 evidence 後變動：fingerprint／SHA mismatch，丟棄 release evidence並完整重跑。
- 發布前回復方式是回復本工作 source diff並重新建置；發布後不提供舊 binary downgrade，只停止散布並停用或解除安裝 0.2.1，保留 workspace、`.devweave`、Wiki、snapshot 與 logs。
- GUI／symlink privilege 等環境驗證無法完成時保持 No-Go，不以 release deadline waiver。

## 高風險分析

- **Migration**：不適用。沒有 workspace、machine state、schema、bootstrap destination 或 user data migration。
- **Rollback**：source change 可逆；binary release 明確沒有 legacy downgrade。Incident procedure 是 withdraw／disable／uninstall current version且不動 repository data。
- **Security**：不得刪除 current archive、manifest、path containment、hook semantic、byte length 或 SHA-256 checks；unit regression與G3 Independent Review特別確認 verifier 沒有因移除 legacy checks 而變成 existence-only。
- **Compatibility**：`engines.vscode` 與 Python minimum 不修改，public commands／schema／Hook／bootstrap bytes的語意維持；只把實測 certification 與技術 minimum 分離。0.1.0／0.2.0 binary compatibility 明確不在 scope。
- **Performance**：Extension runtime 零變更。Build 只少兩次 legacy file reads並多一次 current SHA-256，對約數百 KB artifact 為可忽略線性成本；不新增 cache、network或dependency。
- **Independent Review**：final product/Wiki/baseline/diff/evidence 穩定後啟動 exactly one isolated read-only reviewer；critical security、data-loss、irreversible或scope finding 阻斷 G3。

## 設計決策

## DEC-001: 版本導出單一真實來源
- Requirements: REQ-001, REQ-002, NFR-001
- Decision: 只由 `package.json.version` 導出 current VSIX path、bundle version與metadata；verifier不接受legacy artifact清單。
- Rationale: 避免工作目錄殘留檔影響驗收，維持最小且深的package interface。
- Consequences: 0.1.0／0.2.0 完全不被讀取；每次 release version變更仍需更新現有 explicit version assertion。

## DEC-002: Unit policy seam與integration artifact seam分離
- Requirements: REQ-001, REQ-002, REQ-004
- Decision: Unit test驗source contract且不依賴prebuilt binary；`npm package` verifier驗實際 current artifact bytes。
- Rationale: 讓unit suite可先執行，並避免用static regex冒充真實package integrity。
- Consequences: 兩層測試各自有明確責任；final release仍必須執行package command。

## DEC-003: 認證與技術門檻分離
- Requirements: REQ-003, NFR-003
- Decision: 保留既有engine/runtime minimum，但所有公開說明只把目前實測stack稱為本次認證環境。
- Rationale: 不改安裝相容介面，也不對未實測組合做正式認證宣稱。
- Consequences: 文件需要一致的新措辭；未來擴大認證需新的work item與evidence。

## DEC-004: Current-only incident response
- Requirements: REQ-005, NFR-002
- Decision: 不提供舊binary rollback；事故時withdraw、disable或uninstall 0.2.1，保留全部repository資料與診斷證據。
- Rationale: 符合使用者排除舊VSIX的決策，避免自動資料回復造成損失。
- Consequences: 發布前驗收門檻更嚴格；修復需新版本而非覆寫0.2.1。

## DEC-005: Lifecycle-aware documentation consistency
- Requirements: REQ-003, NFR-003
- Decision: Implementation先更新source docs／Help與contract test；accepted baseline及四個affected Wiki pages（overview、knowledge workflow、Knowledge Engine、VS Code Extension）在verification依DevWeave policy更新，Wiki log只append。
- Rationale: 同時保證文字一致與G2前／verification前的write boundary。
- Consequences: Implementation期間Wiki仍顯示已記錄的gap，直到G3 promotion完成。
