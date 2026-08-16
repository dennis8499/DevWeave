# 功能驗收：建立 Guard Policy Engine v2 並修正 Side-effect Command Policy

<!-- DEVWEAVE:artifact=acceptance version=1 work=20260814-233520-bug-guard-policy-engine-v2-side-effect-comma -->

## 驗證矩陣

本 Work Item 的 current source fingerprint 為 `456257ee90768f009e0e5bfc3f38c0dca635ae2b241393fb17a05c2f475a724e`；G2 凍結的 plan ID/digest 為 `plan-89c8008325b6bae1` / `sha256:147af180d37ae67586d55739749ccd1c985c1a03535302133bda0adff78c940b`；project policy digest 為 `sha256:386702adf1c510b07cd9a99cf79c22d34fcf0d189a1969dcef7f025ddfa1e945`。

| AC | 驗證結果 | Current evidence |
| --- | --- | --- |
| AC-001、AC-002、AC-003、AC-004、AC-008、AC-009、AC-010、AC-011、AC-024、AC-027 | G2/phase、release、cwd、executable trust、typed read-only grammar、cross-shell injection deny、configured direct Bash deny 與 malformed policy fail closed | EVID-023、EVID-024、EVID-026 |
| AC-005、AC-006、AC-007、AC-012、AC-022、AC-023、AC-026、AC-028、AC-029、AC-030、AC-031、AC-032 | controlled executor、snapshot、writer barrier、atomic state、undeclared effect 與 evidence 欄位通過 | EVID-021、EVID-023、EVID-024、EVID-025 |
| AC-013、AC-014、AC-015、AC-016、AC-017、AC-018、AC-019、AC-020、AC-021、AC-025 | full policy regression、shared evaluator、frozen plan、digest stale、expectation eligibility、profile/G3 parity、mutation stale 與 Doctor | EVID-023、EVID-024、EVID-025、EVID-027 |
| AC-001 至 AC-032 的 high-risk review readiness | 唯一 isolated read-only reviewer 已經由 Router 記錄，但因 timeout 為 unavailable；沒有 returned finding，不能視為 passed evidence | EVID-028 |

以上列出 AC-001 至 AC-032 全部 acceptance IDs；current product verification evidence 為 EVID-021 至 EVID-027，其 `status=passed`、`stale=false`、`gate_eligible=true`、`execution_channel=devweave_executor` 與 plan/source digest 均由 engine 計算。EVID-028 是 current 但 `status=failed`、`gate_eligible=false` 的 independent-review unavailable warning。EVID-001 為舊流程的 failed reproduction；EVID-002 至 EVID-009 是 G1 machine reproduction，雖然其中 observed result 明確保存原始 failure，但其 `gate_eligible=false`，不被 G3 當成修正證據；EVID-010 至 EVID-020 是 final source fix 前的歷史證據，已由 engine 標為 stale。

本 acceptance artifact 明確 account 的 evidence IDs 為：EVID-001、EVID-002、EVID-003、EVID-004、EVID-005、EVID-006、EVID-007、EVID-008、EVID-009、EVID-010、EVID-011、EVID-012、EVID-013、EVID-014、EVID-015、EVID-016、EVID-017、EVID-018、EVID-019、EVID-020、EVID-021、EVID-022、EVID-023、EVID-024、EVID-025、EVID-026、EVID-027、EVID-028。

## 原始 Bug reproduction 與 root cause

- BUG-01 Read-only Prefix Bypass：EVID-003 在舊 Guard 讓 `git status & echo`、`$(...)`、backtick、`git diff --output`、unsafe Git flag、CMD expansion 與 PowerShell expression payload 通過；修正後 typed parser matrix 由 current EVID-026 與 EVID-023 通過。payload 只作 Guard 字串輸入，未執行副作用。
- BUG-02 Configured Command Direct Bash Bypass：EVID-004 重現 post-G2 configured write/release/output command 與 wrong cwd/direct Bash 放行；修正後強制 executor channel、binding、canonical cwd 與 policy context，由 current EVID-026、EVID-023 驗證。
- BUG-03 Command Policy Drift：EVID-005 重現同一 command ID 修改 argv 後舊 evidence 仍 current；修正後 command definition/policy digest 改變會使 plan、gate 與 command evidence stale，由 current EVID-023、EVID-025 驗證。
- BUG-04 Non-zero／Any Expectation Evidence：EVID-006 重現 nonzero/any expectation match 被記成 passed 並進入 raw G3 set；修正後 engine 仍可保存診斷結果，但 `gate_eligible=false`，由 current EVID-025 驗證 G3 rejection。
- BUG-05 Profile Runner/G3 Required Set：EVID-007 重現 selective runner 與 G3 reconstructed required set 不一致；修正後 Runner/G3 只讀同一 frozen plan，同一 selection 為 7 selected，release-only 與其 smoke dependency 共 2 skipped，由 current EVID-023、EVID-024、EVID-025 驗證。
- BUG-06 Parallel Write Evidence State：EVID-008 重現 writer 與 writes:none test 同批平行，test 讀到 writer 前 state；修正後 writer stage serial、candidate fingerprint freeze、read-only barrier 與 exclusive group 由 current EVID-025 驗證。
- BUG-07 Undeclared Writes：EVID-009 重現宣告 `dist/` 卻修改 `src/` 仍形成 passed evidence；修正後 snapshot 計算 `actual_changed_paths`/`undeclared_paths`，failure 不 promotion 且不 gate-eligible，由 current EVID-025 驗證。

共同 root cause 是原本 Guard、Runner 與 G3 分別維護 argv/prefix、profile metadata、raw passed evidence 與 project required set；command identity、execution context、observed effects、policy digest 與 lifecycle currentness 沒有同一個 deep module 串接。

## Profile 證據

bug profile 已完成「G1 failing reproduction → G2 approval → TDD regression → controlled high profile」閉環。final high frozen-plan batch `VB-f45b737d5c9e` 的 selected 集合為 `extension-tests`、`extension-typecheck`、`unit-tests-cli`、`unit-tests-contract`、`unit-tests-core`、`unit-tests-guard`、`unit-tests-knowledge`；skipped 為 `extension-package`（release-only）與 `extension-smoke`（release-only dependency: extension-package）。EVID-021、EVID-022、EVID-023、EVID-024、EVID-025、EVID-026、EVID-027 全部 exit code 0、未 timeout、無 changed/undeclared paths、current source/plan digest 與 `gate_eligible=true`。

受控執行命令與結果：

- `python -B -m unittest discover -s tests -v`：129 tests、1 skipped、OK。
- `python -B -m unittest discover -s tests -p test_command_policy.py -v`：14/14 OK；新增 `release-only-dependency` G3 skip parity 測試先 Red，再 Green。
- high profile：EVID-021、EVID-022、EVID-023、EVID-024、EVID-025、EVID-026、EVID-027，Extension tests 88 pass、typecheck pass、CLI 23 pass、contract 16 pass、core 45 pass/1 skipped、Guard 15 pass、Knowledge 16 pass。
- `unit-tests-contract` TASK-006 verification：EVID-020，16 pass。
- `devweave doctor`：Python/Git/hook/launcher、policy v2/digest、trusted executables、metadata、active plans、Wiki 全部 checks true。
- `git diff --check`：通過；只有既有 LF/CRLF conversion warnings，無 whitespace error。

TASK-001/TASK-002 已由 EVID-011 完成；TASK-003/TASK-004 已由 EVID-012 完成；TASK-005 已由 EVID-013～EVID-019 完成；TASK-006 已由 EVID-020 完成。上述 task evidence 均是 final source fix 前的歷史 machine evidence，現在由 engine 標為 stale；current task/profile evidence 是 EVID-021～EVID-027。

## 基線更新

已透過 Router `baseline` 登錄兩個 declared targets：`.devweave/baseline/architecture.md` 與 `.devweave/baseline/quality.md`。Architecture baseline 新增 shared evaluator、G2 frozen plan、controlled executor、writer stage/candidate promotion 與 engine-derived evidence；Quality baseline 新增 typed read-only fail-closed、cross-shell adversarial policy、digest stale、expectation ineligibility、selected/skipped parity、undeclared-write failure 與 atomic machine-state contract。

## Wiki 知識提升

Knowledge Review disposition 為 `promote`，理由是本 Work Item 改變架構與操作 contract。Router 記錄的 current change fingerprint 為 `456257ee90768f009e0e5bfc3f38c0dca635ae2b241393fb17a05c2f475a724e`；四個 content upsert 是 `wiki/overview.md`、`wiki/architecture/devweave-knowledge-workflow.md`、`wiki/modules/knowledge-engine.md`、`wiki/modules/command-policy-engine.md`，並精確耦合 `wiki/index.md` 與 append-only `wiki/log.md`。六頁均已由 Router seal，current source fingerprints 與 `verified_by` 已寫入 frontmatter；Wiki health 為 healthy、stale/placeholder/critical lint warnings 為 0。`tests/test_command_policy.py` 與 `tests/test_guard.py` 為未納入長期 Wiki source 的 test-only paths，保留在 coverage projection 的 uncovered list，並不影響 source-bound code evidence 或 G3 command coverage。

## 獨立 Review

唯一 high-risk isolated read-only reviewer 已由 Router 啟動，reviewer ID 為 `01a009f2-d49b-7e13-bd16-bf1e07723159`。它在等待窗口內 timeout，沒有輸出 report，隨後被安全關閉；Router 以 generated unavailable report 記錄 `EVID-028`。其 current source fingerprint 為 `456257ee90768f009e0e5bfc3f38c0dca635ae2b241393fb17a05c2f475a724e`，`context_mode=isolated_read_only`、`result=unavailable`、`severity=none`、`findings=[]`、`gate_eligible=false`。這是 Engine 定義的 warning，不是 passed review；沒有可處理的 Critical finding，也沒有 waiver，但人工 G3 必須注意 review 未完成。

## 殘餘風險

- 本批沒有 waiver；EVID-028 未回傳 finding，因此沒有已知未處理 Critical finding，但 independent review unavailable 仍是 G3 warning。Network policy 仍是 engine boundary，不宣稱完整 OS network sandbox，完整 OS sandbox 是非目標。
- release-only `extension-package` 與依賴它的 `extension-smoke` 未在本次無 release context 的 high profile 啟動；Router 已明確標示兩者 skipped。正式 release stage 需另以 explicit release context 執行並產生 current evidence。
- Windows symlink/reparse 測試因目前帳號沒有建立 symlink 的權限而 skipped 1 項；其他 Windows launcher、root/nested cwd、UTF-8 與 policy matrix 通過，若要宣稱 symlink coverage 需在具權限 host 補跑。
- 本 Codex host 未向 Router/PreToolUse hook 暴露 session ID，`devweave bind` 保持 `awaiting_hook`；沒有偽造 binding。這是 host integration limitation，需在 hook confirmation 可用時重新 bind。
- full-tree snapshot 刻意排除 `.git`、dependency/cache 目錄與 Python/pytest caches 以維持 bounded execution；tracked source、declared outputs、Wiki、baseline 與 work scope 仍受 reconciliation，非目標路徑不被宣稱完整 fingerprint 覆蓋。

## 驗收結論

Implementation、regression、controlled profile、Doctor、baseline、Wiki promote/seal 與 machine-only review record 已完成；independent review 的 result 是 unavailable warning，並非通過。這份 acceptance report 可供人工 G3 Double Check，但本 artifact 不自行表示 G3 approval，也不執行 close。
