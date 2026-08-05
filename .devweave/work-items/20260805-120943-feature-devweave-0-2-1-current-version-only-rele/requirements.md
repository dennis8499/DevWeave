# 需求與驗收條件：DevWeave 0.2.1 current-version-only release contract

<!-- DEVWEAVE:artifact=requirements version=1 work=20260805-120943-feature-devweave-0-2-1-current-version-only-rele -->
## 假設與限制

- 使用者已決定只處理、驗收與交付 0.2.1；0.1.0／0.2.0 不屬於 release contract。
- 放行政策為零已知缺陷，不接受以時程為由的 waiver。
- 本次認證只涵蓋 Windows x64 build 10.0.26200／25H2、VS Code 1.131.0、Python 3.14.6、Git 2.51.0.windows.1 與目前 Codex host；其他組合不是本次已認證環境。
- `engines.vscode` 與 Python minimum 可保留為技術安裝／執行條件，但文件必須區分「技術門檻」與「本次實測認證」。
- 發布事故不提供舊 binary downgrade；處理方式是停止散布並停用或解除安裝 0.2.1，且保留 `.devweave`、Wiki、workspace snapshot 與 logs。
- 任何 final HEAD 或 VSIX byte 變更都使 release evidence stale，必須完整重跑。
- 非發布 `debug.log` 的移除屬於 approved release cleanup；四個 source-affected Wiki pages（overview、knowledge workflow、Knowledge Engine、VS Code Extension）必須在 G3 refresh／seal，不以 scope 或 knowledge waiver 略過。

## 需求與驗收條件

## REQ-001: 唯一 current release artifact
- Priority: must
- Acceptance: AC-001, AC-002
- Description: 0.2.1 release 只要求、產生、驗證與交付 `devweave-control-center-0.2.1.vsix`；0.1.0／0.2.0 缺席不得造成 test 或 package 失敗。

## REQ-002: Current artifact integrity
- Priority: must
- Acceptance: AC-002, AC-003
- Description: Verifier 必須從 `package.json` 的 0.2.1 驗證 VSIX metadata、bootstrap manifest version、必要 entries，以及每個 bundled source 的 byte length／SHA-256；不得只驗證檔案存在。

## REQ-003: 公開說明一致
- Priority: must
- Acceptance: AC-004
- Description: README、使用手冊、Extension README／Help、accepted baseline 與 promoted Wiki 必須一致描述 current-version-only 交付、認證環境與無舊 binary rollback 的事故處理。

## REQ-004: 既有公開介面不變
- Priority: must
- Acceptance: AC-005
- Description: Chat verbs、Machine CLI、schema version 1、Gate lifecycle、Hook contract、Wiki lifecycle、五個 Extension command IDs 與 bootstrap destinations/policies 不得因 release-policy 調整而變更。

## REQ-005: 安全事故處理
- Priority: must
- Acceptance: AC-006
- Description: 0.2.1 必須可在認證環境安裝、重裝、停用與解除安裝；停用或解除安裝不得自動刪除或覆寫 workspace、`.devweave`、Wiki 或使用者資料。

## NFR-001: 決定性與可追溯性
- Priority: must
- Acceptance: AC-003, AC-007
- Description: 相同 clean HEAD 的兩次 0.2.1 build 必須產生相同 SHA-256；所有 release evidence 必須綁定 final HEAD、環境版本與該 artifact hash。

## NFR-002: 零已知缺陷 Gate
- Priority: must
- Acceptance: AC-007, AC-008
- Description: 最終放行要求零 failed、blocked、todo、stale evidence、未補驗 skip、open defect 與規格矛盾。

## NFR-003: 文件與知識一致性
- Priority: must
- Acceptance: AC-004, AC-008
- Description: Test counts、認證範圍、交付物與 incident response 在 source、baseline、Wiki 與內嵌 UI 文案間必須可機械搜尋並一致。

## AC-001: 舊版缺席 regression
- Requirement: REQ-001
- Scenario: Given repository 沒有 0.1.0／0.2.0 VSIX，When 執行 Extension unit suite，Then current-version package test 通過且沒有 legacy artifact filesystem assertion。

## AC-002: 0.2.1 package verification
- Requirement: REQ-001, REQ-002
- Scenario: Given final source 與 package version 0.2.1，When 執行 `npm.cmd run package`，Then 只產生 0.2.1 VSIX，並驗證 package/manifest version、58 個 bootstrap files、118 個 VSIX entries、required entries 與 source hashes；計數包含必要的 `native-question-contract.md`。

## AC-003: 可重現 artifact
- Requirement: REQ-002, NFR-001
- Scenario: Given 同一 clean final HEAD，When 連續建置兩次，Then 兩次 0.2.1 VSIX SHA-256 完全一致，且發布檔 hash 與 evidence 相同。

## AC-004: Current-only 文案契約
- Requirement: REQ-003, NFR-003
- Scenario: Given 所有 public docs、Help、baseline 與 promoted Wiki，When 執行 repository contract 與 bounded text audit，Then 不存在現行 0.2.1 必須保留／回退 0.1.0／0.2.0 的規範文字，並一致記錄 98 項 Python suite 與本次認證環境；append-only Wiki 歷史 log 不改寫。

## AC-005: 公開介面 regression
- Requirement: REQ-004
- Scenario: When 執行 Python full suite、repository contract、Extension 73 tests、typecheck 與 smoke test，Then 所有既有 chat/CLI/schema/hook/bootstrap/command contracts 維持通過。

## AC-006: Current version lifecycle
- Requirement: REQ-005
- Scenario: Given final 0.2.1 VSIX，When 在認證環境安裝、重裝、停用與解除安裝，Then Extension lifecycle 正常且 workspace、`.devweave`、Wiki 與使用者檔案 bytes 不變。

## AC-007: Release evidence currentness
- Requirement: NFR-001, NFR-002
- Scenario: When 完成 doctor、status、Python suites、Extension tests/typecheck/package/smoke、`git diff --check` 與 artifact hash，Then 每項 evidence 綁定 final source fingerprint，且 worktree 只包含 approved scope changes（含移除 `debug.log`、刷新四個 affected Wiki pages）與唯一 0.2.1 artifact。

## AC-008: 零缺陷放行
- Requirement: NFR-002, NFR-003
- Scenario: Given G3 acceptance review，When 檢查 task/evidence、scope、baseline、Wiki、independent review 與手動 walkthrough，Then 零失敗、零未補驗 skip、零 stale／unresolved finding；否則保持 No-Go。
