---
title: DevWeave Public CI
type: module
sources: [.github/workflows/ci.yml, README.md, tests/test_repository_contract.py, vscode-extension/package.json]
last_updated: 2026-08-19
tags: [module]
status: active
source_fingerprint: "sha256:2ceaf9fdf8bd33b346ea8d5a8ac64e3f029e7604fb5f1a2166103c39baec6d7f"
verified_by: 20260819-115533-feature-deterministic-ci-baseline
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

## Behavior and Gaps

- Standard profile 最終選取 Extension tests/typecheck 與五組 Python suites；`extension-package` 以 `release-only`、`extension-smoke` 以 `release-only-dependency:extension-package` 合法跳過，沒有 waiver。
- Public workflow 不執行 smoke、package、release、部署、Codex review、自動 commit 或自動開 PR，也不使用 larger/self-hosted runner。
- Repository contract 固定已知結構與安全 invariant，但不是完整 YAML semantic parser。第一次 hosted execution 仍必須由人類 push／建立 PR 後觀察；在那之前不能宣稱遠端 matrix 已實際全綠。
- 完整 SHA 不會自動更新。若 GitHub runner 或 Action runtime 未來不相容，必須以新的受治理 Work Item 核對上游 release 後更新 SHA，不能改成浮動 tag。
