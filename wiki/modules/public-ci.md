---
title: DevWeave Public CI
type: module
sources: [.github/workflows/ci.yml, README.md, tests/test_repository_contract.py, vscode-extension/package.json, vscode-extension/scripts/run-unit-tests.mjs]
last_updated: 2026-08-19
tags: [module]
status: active
source_fingerprint: "sha256:e677ea2003878f8e7d7226d59b59794f7e787c4cd9cac9963007aad68a5426d2"
verified_by: 20260819-140802-bug-fix-node-20-and-posix-ci-regressions
---

# DevWeave Public CI

## Responsibility

`wiki/modules/public-ci.md` 描述 DevWeave 的公開、跨平台、deterministic development baseline。唯一執行模組是 `.github/workflows/ci.yml`：它把 repository event 轉成 Python、Node 與 hygiene checks，但不修改 DevWeave runtime、machine ledger、Git remote、release artifact 或部署環境。

這個 CI 是後續 P0 integrity／execution／trust 工作的共同回歸基準。CI pass 表示開發合約在指定 GitHub-hosted runner 組合通過，不代表 VS Code Extension Host smoke、VSIX package 或特定 Windows release certification 已完成。

## Public Surface

- Trigger：所有 `pull_request`，以及 push 到 `master`。
- Python check：`ubuntu-latest`、`windows-latest`、`macos-latest` × Python `3.11`、`3.12`、`3.13`、`3.14`；每個 cell 執行 `python -B -m unittest discover -s tests -v`。
- Node check：`ubuntu-latest`、`windows-latest` × Node `20`、`22`；在 `vscode-extension` 依序執行 `npm ci`、`npm run typecheck`、`npm test`、`npm run build`。
- Hygiene check：獨立執行 `git diff --check`。
- 兩個 matrix 都使用 `fail-fast: false`，job name 帶出 OS/runtime，任何非零 step 都保留為紅燈，沒有 `continue-on-error`。
- README badge 連到 `actions/workflows/ci.yml`，驗證章節提供 PowerShell、POSIX 與 Node 本機等價命令。

## Dependencies

- `actions/checkout` 固定為 commit `3d3c42e5aac5ba805825da76410c181273ba90b1`（v7.0.1）。
- `actions/setup-python` 固定為 commit `5fda3b95a4ea91299a34e894583c3862153e4b97`（v7.0.0）。
- `actions/setup-node` 固定為 commit `820762786026740c76f36085b0efc47a31fe5020`（v7.0.0）。
- Top-level permission 只有 `contents: read`；三次 checkout 都設定 `persist-credentials: false`。Workflow 不接收 repository secrets、Codex API key 或 write token。
- Node dependency 只由 committed `vscode-extension/package-lock.json` 與 `npm ci` 決定；CI 不改寫 lockfile。

## Verification Seam

`RepositoryContractTests` 是不依賴 GitHub API 或第三方 YAML parser 的本機 seam。它以 UTF-8 讀取 workflow，分離 Python、Node、hygiene job blocks，再以已核准的 literal matrix、SHA、permission 與 commands 作獨立 oracle；也固定 badge、本機命令與 certification caveat。

Doctor contract 在 Windows runner 實際驗證 `py-3`、CMD、Windows PowerShell、PowerShell 7、hook schema 與 launcher probe；非 Windows runner 必須回傳精確的 Windows-only skip detail。這能區分真實 capability observation 與 prerequisite skip，不把 unsupported host 假裝成正式認證。

P0-00 使用兩個 TDD slices：缺少 workflow 的 contract red 為 `EVID-001`，最小 workflow green 為 `EVID-002`；缺少 README badge 的 red 為 `EVID-003`，文件 green 為 `EVID-004`。最終 frozen standard profile 的 current regression evidence 為 `EVID-005` 至 `EVID-011`。

### 2026-08-19 Node 20／POSIX hardening

- Node 測試入口從 quoted glob 改為 `node scripts/run-unit-tests.mjs`。Runner 遞迴收集 `.test.ts`、以 repository-relative POSIX path deterministic sort，再以 `process.execPath` 執行 resolved `tsx/cli`；`shell: false` 且每個測試檔都是獨立 argv，因此不依賴 Bash、PowerShell、CMD 或 Node 20 的 glob 解讀。沒有測試、spawn error、signal、missing numeric status 與 child nonzero 都 fail closed。
- Runner 自身由新增的第 89 項 Extension unit test 覆蓋 deterministic discovery、explicit argv、zero/nonzero、spawn error、signal 與 empty-suite；release packager 明確排除 runner 與其 test，避免改變既有 VSIX 內容面。
- Python CLI contract 用 `Path(sys.executable).resolve()` 驗證 canonical executable；Guard 的 read-only fixture 改用平台原生 temporary repository。UTF-8 deny、malformed input、read-only silence 三個真實 Windows launcher tests 只在 `win32` 執行，其他 OS 以固定 prerequisite reason skip；一般 workflow、schema、permission 與 Doctor platform-truth assertions 仍在所有 runner 執行。
- PR #1 的 GitHub Actions run `32231940371` 在 head `036ca6b2cbaabe117a82420948e5b7c3bdbd2a83` 完成 17/17：12 個 Python matrix cells、4 個 Node matrix cells 與 repository hygiene 全部 passing。Node 20 Ubuntu／Windows 與先前失敗的 Python Ubuntu／macOS cells 均已轉綠。
- Hosted result 以手動、non-gate-eligible `EVID-024` 保存；current controlled standard batch `VB-1786ea0ecaff` 的 `EVID-050`～`EVID-056` 為 7/7 且逐筆追溯 AC-006／TASK-004，`EVID-057`～`EVID-060` 精確覆蓋 AC-001～AC-005 與 TASK-001～TASK-003。並行批次產生的 `.devweave` cross-write false negatives 與後續無 trace metadata 的 superseded records 都已由 official implementation revision 標為 stale，不作門檻證據。

## Behavior and Gaps

- Standard profile 最終選取 Extension tests/typecheck 與五組 Python suites；`extension-package` 以 `release-only`、`extension-smoke` 以 `release-only-dependency:extension-package` 合法跳過，沒有 waiver。
- Public workflow 不執行 smoke、package、release、部署、Codex review、自動 commit 或自動開 PR，也不使用 larger/self-hosted runner。
- Repository contract 固定已知結構與安全 invariant，但不是完整 YAML semantic parser。PR #1 run `32231940371` 已提供本次提交的真實 hosted 17/17 observation；未來 source、runner image、Action SHA 或 dependency 改變後，仍必須取得新的 hosted run，不能沿用這次結論。
- 完整 SHA 不會自動更新。若 GitHub runner 或 Action runtime 未來不相容，必須以新的受治理 Work Item 核對上游 release 後更新 SHA，不能改成浮動 tag。
