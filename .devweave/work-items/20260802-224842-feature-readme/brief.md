# 工作摘要：補充 README 與繁體中文使用手冊

<!-- DEVWEAVE:artifact=brief version=1 work=20260802-224842-feature-readme kind=feature -->

## 問題與目標

DevWeave 目前的 `README.md` 已涵蓋核心流程、Wiki-first、內部 CLI 與 repository contract，
但資訊集中在單一入口文件，第一次使用者與維護者仍需從多個 source、phase reference、
contracts 與測試推導完整操作方式。此次工作要重整 README 為清楚的專案入口，並新增
`docs/使用手冊.md`，讓使用者能從前置需求一路完成初始化、建立 work item、通過 G1/G2/G3，
維護者也能查到完整 machine CLI、state、evidence、Wiki 與 hook 行為。

主要使用者包括：

- 初次在 Git repository 導入 DevWeave 的開發者。
- 使用 Codex CLI 或 VS Code Codex Extension 執行日常變更的開發者。
- 維護 DevWeave skill、CLI、project contract 與 companion skills 的 repository 維護者。

成功訊號是 README 能在短篇幅內說明「這是什麼、如何開始、下一步去哪裡」，而使用手冊能
以實際程式與 CLI help 為依據，完整描述目前可用命令、生命週期、限制、驗證與故障排除，
且不改變任何 runtime 或 machine contract。

## 現況證據

本 work item 的 G1 Wiki-first context 依序為 `wiki/index.md`、`wiki/overview.md`、
`wiki/log.md`。`wiki/overview.md` 仍是 bootstrap placeholder，沒有可直接引用的模組、
runtime、dependency 或 operational knowledge，因此已記錄 gap 並回溯 raw source；現行
程式碼、`AGENTS.md`、baseline、phase references、contracts、測試與 CLI help 為本次文件的
事實來源。

已確認的 repository facts：

- `.devweave/project.json` 已啟用 managed mode、`locale` 為 `zh-TW`，目前設定一個
  `unit-tests` 驗證命令，使用 Python unittest discover。
- runtime 位於 `.agents/skills/devweave/`，由 `devweave.py`、`devweave_core.py`、
  `knowledge_core.py` 與 `guard.py` 組成，僅使用 Python standard library。
- 公開 Codex surface 為 `new`、`feature`、`refactor`、`bug`、`next`、`status`、
  `revise`、`approve`；machine CLI 額外提供 lifecycle、knowledge、task、evidence、
  verification、waiver、doctor、project 與 command 管理命令。
- 生命週期為 requirements → design → implementation → verification → acceptance_review
  → closed，並由 scope、build、acceptance 三道人工 gate 控制。
- Codex PreToolUse hook 會檢查 active work、session binding、G2、scope 與 verification-only
  Wiki policy；它是 guardrail，不是作業系統 sandbox。
- 現有完整測試套件在文件工作開始前為 62/62 通過；文件工作不應新增產品行為或測試需求。

## 範圍

本工作項只包含兩個使用者文件：

- 重寫根目錄 `README.md`，保留正確的核心概念並重新編排為專案介紹、前置需求、快速開始、
  核心流程、結構與驗證入口。
- 新增 `docs/使用手冊.md`，以繁體中文提供使用者與維護者的完整操作、CLI、lifecycle、
  Wiki、hook、companion skills、測試與故障排除參考。

文件中的命令、路徑、schema key、phase、gate、exit code 與 machine protocol 必須與目前
實際介面一致；README 與手冊互相連結，並連到既有的 `AGENTS.md` 與 contracts reference。

## 非目標

- 不修改 `.agents/skills/` 下的 runtime、phase reference、asset 或 companion skill。
- 不修改 `tests/`、`fixtures/`、`.devweave/project.json`、任何 baseline、`wiki/`、hook、
  dependencies、build 或 CI。
- 不新增第二套 router、公開 chat verb、CLI 命令、schema、installer、database、RAG 或
  remote integration。
- 不建立或更新 `.devweave` JSON/JSONL machine ledger；工作項 artifacts 只透過 DevWeave
  正規流程維護。
- 不建立 branch、worktree、commit、push、PR 或 deployment。

## 風險

風險等級：standard

主要風險是文件若與可執行 CLI 或 guard 行為不一致，會造成使用者誤操作；因此所有範例以
CLI `--help`、現行 source、contracts、測試與 `doctor` 結果交叉核對。變更僅限 Markdown，
可由 Git 復原，不涉及資料遷移、安全邊界或 runtime compatibility。驗證基線為既有 62 項
unittest、CLI smoke checks、Markdown link/path checks 與 `git diff --check`。

## Profile 補充

此工作採 `feature` profile：新增面向使用者與維護者的文件能力，既有 runtime 行為、公開
router、CLI JSON envelope、schema version 1、三道 gate 與 Wiki lifecycle 都必須維持相容。
第一個可驗證成果是 README 與使用手冊完成且互相連結；G3 需同時具備文件 acceptance 與
regression evidence。
