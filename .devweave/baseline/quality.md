# Quality Baseline

此文件保存已驗收的非功能需求、驗證命令與品質政策。由 DevWeave 工作項在 G3 前更新。

## Quality Attributes

- Determinism：stdlib-only frontmatter、canonical JSON、sorted paths、streaming SHA-256、exclusive canonical scaffold 與 atomic per-file writes。
- Safety：所有 knowledge paths 固定在 root `wiki/`；source 禁止進入 Wiki、`.devweave`、`.git` 或 repo 外；中間 symlink escape fail closed。
- Compatibility：schema version 1 additive migration、既有 Wiki 不覆寫、custom-only Wiki 可補齊 reserved starters、缺少 review marker 的 legacy active work 不追溯阻擋、既有 verbs 與 JSON envelope 不變。
- Traceability：G1 context records、G3 Knowledge Review/plan/seal、work provenance、index/log coupling、baseline 與獨立 fingerprints 均進入 machine validation。
- Independent Review safety：report 只可從 work-item incoming containment 讀取，受 fixed JSON、UTF-8、size bound、AC/TASK validation、secret redaction、SHA-256、source fingerprint 與 Git HEAD provenance 保護；critical finding 必須 exact named `review-critical` acceptance waiver。
- Review compatibility：schema version 1 additive nested review metadata；legacy evidence 可讀但不能冒充 current high-risk review，standard/low risk 不產生 reviewer requirement。
- Bounded knowledge：G1 固定 index 加最多五個內容頁，每個 Wiki page 最多五個 sources，每次 promotion 最多五個 content targets；不加入 vector/FTS/token measurement runtime。
- Instruction safety：repository contract 固定唯一 `devweave` router、精確五個 companion allowlist、folder/frontmatter identity、local-link containment、root precedence policy，並將 `writing-great-skills` 標記為 maintenance-only exclusion。
- Skill predictability：repository contract 檢查六個受治理 Skill 的 frontmatter/metadata、`devweave` implicit invocation、`grill-me` disabled implicit invocation 與必要 `disable-model-invocation` 欄位；UTF-8 quick validation、隔離 forward-test 與 stale-reference scan 檢查 phase routing、G1/G2 stop、public seam、independent oracle、red-capable loop 與 completion criteria。
- Supply-chain traceability：`skills-lock.json` 記錄每個 upstream source、skillPath 與 computed hash；更新只能在新的 DevWeave feature 中人工觸發與檢閱。
- Extension bootstrap safety：manifest destinations/source 必須 repo-relative 且不重複；每個 bundled source 驗證 SHA-256/byte length；ancestor symlink、非預期 type、content conflict 與 malformed bundle 均在寫入前拒絕。所有 repository write 只存在於確認後的 VS Code filesystem adapter，rollback 只刪除本次建立的 files；semantic adoption 只限七個明確資料 contract。
- Extension bootstrap compatibility：同 bytes 採用、合法 evolved project/baseline/Wiki bytes 列 adopted、重跑回報 idempotent、Windows/POSIX relative paths canonicalize 成相同 targets；既有合法或 critical-diagnostic project 不會由 initialize 自動修復。
- Preview-first copy safety：未有 matching preview、不同 panel/intent/revision、stale snapshot、mutation-blocked state 或 clipboard retry 超過一次時，host 不得寫入 clipboard；初始化取消、conflict 與 failure 不得留下 partial control state。
- Plan Mode preflight safety：`request_user_input` visibility 是唯一 host capability 證據；所有 pre-G2 mutation entry 在 Work Item mutation 前先停止或完成 preflight，未取得 capability 不建立 Work Item，只有明確 compatibility 才能 fallback。Extension guidance 不提供 host mode adapter，且 `chatText` 維持既有 command prompt。
- Windows public release certification：本次提供 0.2.3 VSIX，並保留 0.2.2 與 0.2.1 artifacts；認證範圍限定為 Windows x64 build 10.0.26200／25H2、VS Code 1.131.0、Python 3.14.6、Git 2.51.0.windows.1 與目前 Codex host。VS Code 1.90+、Python 3.11+ 僅為技術門檻，不提供 Marketplace、跨平台或舊版 binary rollback 承諾。
- Windows launcher contract：根 `.codex/hooks.json` 的 exact matcher、POSIX/Windows dual launcher、handler 的 .NET UTF-8 console input/output normalization、UTF-8 deny output、Git-root path resolution 與 30 秒 timeout 必須由 repository contract、`doctor` 的 CMD/PowerShell 5.1/PowerShell 7 probes，以及 root/nested cwd matrix 共同驗證；launcher failure 必須與 guard policy deny 分開呈現，且不得以 shell-scoped `$OutputEncoding` 取代 handler 的 explicit console setup。
- Windows walkthrough bar：fresh install/init、合法 evolved adoption、reserved conflict/failure fail-closed 與 multiple active work 四條 disposable fixture walkthrough 必須通過；取消/失敗不得留下 partial state，未確認 prompt 不得複製，Refresh 後舊 preview 必須重新預覽。
- VSIX release transaction：production package 先以 `package-vsix.mjs --output <candidate>` 建立同目錄唯一 candidate，再以 `verify-package.mjs --artifact <candidate>` 驗證 provenance；只有成功後才 atomic rename promotion current。verify、promotion 或 cleanup failure 必須保留 current/retained bytes，builder/verifier 缺少 artifact 參數時 fail closed。
- Verification impact selection：command metadata 可宣告 affected paths、write class、outputs、release-only 與 dependencies；low/standard 的 `verify --profile --path` 只執行受影響且可安全閉包的命令，會保存 selected/skipped/closure reasons，high profile 仍執行完整集合。
- Evidence metrics boundary：verification evidence 可保存 bounded duration、context/tool/selection metrics；Codex host 未提供 exact usage 時必須保存 `usage.status=unavailable` 與 null token/cost 欄位，不以 bytes 估算 Token、不保存 prompt 或 secrets。
- Projection efficiency boundary：Extension 初次 refresh 使用 summary-first work-item read，selected detail 才載入 artifacts/evidence/events；Wiki body 受 bounded byte limit 並保存 content hash/truncation/parse diagnostics，projection 不得推導 engine Gate passed。

## Verification Commands

- `python -B -m unittest discover -s tests -v`：111 項通過，另有一項因 Windows symlink privilege 不可用而 skipped；涵蓋 Wiki reserved preflight、bootstrap G1→G3、review/no-update、context currentness、coverage、九種 scaffold、seal、CLI/guard、legacy 與 repository contract coverage。該 skip 是環境權限限制，不能解讀為產品失敗。
- Repository contract tests：目前契約測試全部通過，包含 single-router Codebase Wiki 閉環、Windows hook launcher matrix、current-only release contract、maintenance-only exclusion、metadata 與 invocation policy 契約。
- `npx skills@latest list -a codex`：只列出唯一 local `devweave` router 與五個 `mattpocock/skills` companions。
- `python -X utf8 -B <skill-creator>/scripts/quick_validate.py`：`devweave`、`codebase-design`、`diagnosing-bugs`、`grilling`、`tdd` 通過；`grill-me` 保留必要的 `disable-model-invocation`，由 repository contract 補驗目前 validator 未支援的欄位。
- Isolated forward-test：通過 managed Wiki-first feature、G1 one-question grilling、G2 interface/seam/adapter design、bug red-capable/G2 regression boundary 與 TDD public-seam independent-oracle vertical-slice scenarios。
- `git diff --check`：無 whitespace error；Windows checkout 僅回報既有 LF/CRLF conversion warnings。
- `python -B -m unittest discover -s tests -p test_cli.py -v`：22 項通過，涵蓋 malformed metrics、metadata fail-closed、affected-path selection、dependency closure、release-only skip 與 high full-set policy。
- `python -B -m unittest discover -s tests -p test_devweave_core.py -v`：45 項通過，另有一項因 Windows symlink privilege 不可用而 skipped；涵蓋 bounded metrics、evidence compatibility、state/gate/review 與 repository-safe validation。
- `vscode-extension/npm.cmd run test`：88 項通過，涵蓋 PlanModeGuidance mapping、overview/preview/copy handoff、PreviewGate 的結構化 typed-intent 比較與控制字元拒絕、actionPreview protocol、Wiki DOM mount、ARIA/keyboard、legacy/multi-work、shared semantic validator、BootstrapInstaller、candidate release transaction、bounded metrics projection、prompt 與 security regression。
- `vscode-extension/npm.cmd run typecheck`：通過；`npm.cmd run package` 先建立並驗證 candidate，再 promotion 0.2.3 current artifact。manifest 具 58 個 bootstrap files、119 個 VSIX entries，root/embedded hook、source hash/length、package／bundle version、required entries、compatibility declarations 與 candidate/current artifact SHA-256 全數匹配，0.2.2 與 0.2.1 retained artifacts 保留；verify/promotion failure transaction tests 會確認 current bytes 不變。
- `vscode-extension/npm.cmd run test:smoke`：Windows VS Code Extension Host activation、Activity Bar view 與公開 commands 通過。
- Metrics limits：canonical metrics payload 上限 250,000 bytes；數值欄位必須是有限、非負且不超過 10,000,000。未提供 exact host usage 時只保存 `usage.status=unavailable` 與 null token/cost，禁止以 bytes 推算 Token 或保存 prompt/secrets。
- Independent Review targeted coverage：Python/CLI 覆蓋 passed、unavailable、advisory、critical、timeout/malformed-shaped fallback、waiver、stale source、report containment/size/redaction/hash/provenance；Extension 覆蓋 missing、passed、advisory、unavailable、critical 與 legacy projection。
- High-risk DevWeave verification：`extension-package`、`extension-smoke`、`extension-tests`、`extension-typecheck` 與 root `unit-tests` 均由 CLI verify 登錄為 current passing evidence。

## Operational Constraints

- Python 3.11+、Git repository、UTF-8、無第三方 runtime dependencies。
- Source pages 預期維持 1–5 個核心 sources；health payload 限制 page/finding summaries 數量。
- Repository 必須信任 hook；外部 editor 或停用 hook 的修改只能在 G3 reconciliation 被偵測。
- 完整 111 項 current Windows suite 的 `unit-tests` verification timeout 為 600 秒；本 work item 的 current full-suite run 以 299.633 秒通過並有一項因 Windows symlink privilege 不可用而 skipped。若要宣稱完整 symlink coverage，須在同一 build、具 symlink 權限的隔離執行中補驗並保存 current evidence。
- Companion Skills 僅增加 Markdown、YAML 與一個未自動執行的 Bash template；Node.js／npx 與 network 只在人工安裝或更新時需要，不是 DevWeave runtime dependency。
- Extension bootstrap 的 VSIX package source 是 build-time source-derived；runtime 僅使用內嵌 manifest/resource reader 與 VS Code workspace API，不啟動 Python、shell、Git、network 或任意 child process。

Skill overlay provenance：`20260805-081842-feature-skills-writing-great-skills`（待 G3 核准）；上游五 companion 的 source/path/hash 仍以未修改的 `skills-lock.json` 為準。

Provenance: `20260802-200224-feature-wiki-first`（待 G3 核准）。

Companion Skills provenance: `20260802-215810-feature-matt-pocock-skills`（待 G3 核准）。

Bootstrap provenance: `20260803-112312-feature-vs-code-devweave`（待 G3 核准）。

Codebase LLM Wiki provenance: `20260803-161041-feature-codebase-llm-wiki`（待 G3 核准）。

Independent Review provenance: `20260804-122803-feature-g3-review-agent`（待 G3 核准）。

## Verification Policy v2 Quality Contract

- Read-only policy 是 typed argv allowlist；shell operator、command substitution、redirection、unknown/output-producing flag、quoted/relative executable、wrapper、非 canonical cwd 與 PowerShell/CMD/POSIX 等價 injection 均 fail closed。Configured command 不能以相同 argv 直接 Bash 執行。
- 每個 execution 前後比較 repository/filesystem/Git state；writes:none 的任何 effect、writer 的 undeclared output、scope 外變更、snapshot/postcondition/promotion failure、timeout 或 execution error 都形成 failed、`gate_eligible=false` evidence，且不得 promotion。
- `expect=nonzero` 與 `expect=any` 可以保存 reproduction/diagnostic result，但永遠不滿足 required command、AC coverage、regression evidence 或 G3 acceptance。G3 只接受 frozen Effective Verification Plan 中 current、zero-only、engine-eligible evidence。
- Command definition 的 argv、cwd、writes、outputs、depends_on、timeout 或 release policy 改變會改變 command/policy digest，使舊 plan、G2/G3 與 evidence stale。Runner 與 G3 必須回報相同 plan digest 與 selected/skipped/not-applicable 集合。
- High-risk verification 的 controlled profile 應保留 release-only command 與依賴的明確 skip reason；本 Work Item 的 current profile 為 7 selected、2 release-only skipped。每筆 machine state 仍只能由 atomic typed mutation 寫入，不直接編輯 state/events/evidence ledger。

## DevWeave V2 certification candidate（等待 G3）

- V2 Python suite：64/64 通過；repository contract：16/16 通過。
- Extension unit/DOM/security suite：113/113 通過；TypeScript typecheck 與 production build 通過。
- 真實 VS Code `1.131.0` Extension Host smoke 通過；Control Center evidence 為 9/9 assertions、1 張 screenshot，綁定 commit `c82c9e8023b209a7a063bf15eee69e4a67334ae2`、Codex `0.149.0-alpha.4.3` 與 schema hash `def4a7e9c01d3eaf697ad5a8ada283e6733c9b54892bc4e6928eb1132320d85a`。
- Codex executable SHA-256 為 `21f44f04e70d41d011268863d5109f5d7fc2862c14f390083e39ca3398b5ca47`；doctor 讀取 291 個 schema files 並通過 10 MiB aggregate bound。實際 local app-server/MCP probe 已完成 initialize、thread start 與 exact tool inventory，不包含 model turn。
- 2.0.0 VSIX candidate 已通過 source/provenance/entry verification；最終 artifact 必須在最後 source commit 後重建，並保持未追蹤。
- Disposable-clone cutover rehearsal 已通過 V2 public check、V2 tests、forbidden V1 path/command scan、schema-v2、base-ref 與 clean-tree assertions。
- 尚未通過的 release blocker 是會使用既有 Codex login/network 並傳送工作區相關內容的 live model-turn／detached-review E2E，以及其後 exactly-one isolated high-risk review 與 human G3。未完成前 AC-001、AC-014、AC-021 不得標示通過，Windows certification 也維持 blocked。

V2 candidate provenance: `20260825-163914-feature-devweave-v2-app-server-harness`（等待 G3 核准與 finalizer cutover）。
