# DevWeave

DevWeave 是一套 repo 內建、AI-driven、語言中立的 SDLC workflow。它讓 Codex CLI 與 VS Code Codex Extension 共用同一組工作項、需求、設計、任務、驗證證據與三道人工作業關卡，不依賴 OpenSpec CLI、schema 或 artifact 格式。

## 核心流程

```text
new / feature / refactor / bug
              │
              ▼
       需求探索與 AC ── G1 範圍核准
              │
              ▼
       系統設計與計畫 ── G2 開發核准
              │
              ▼
          逐項實作與驗證
              │
              ▼
         功能驗收報告 ── G3 驗收核准 ── Closed
```

上游 artifact、核准後計畫或驗證後程式碼發生變化時，引擎會依 fingerprint 將受影響的 gate 與 evidence 標成過期，回到最早需要重新確認的階段。

## 使用條件

- Git repository
- Python 3.11 以上
- Codex CLI 或 VS Code Codex Extension
- 第一次使用專案 hook 時，需在 Codex 中信任 repo 的 `.codex/hooks.json`

未初始化的 repo 不會隱式啟動 DevWeave。請先在 Chat 中明確呼叫：

```text
$devweave new <目標>
$devweave feature <需求>
$devweave refactor <目標與預期結果>
$devweave bug <症狀>
```

後續操作：

```text
$devweave next [work-id]
$devweave status [work-id]
$devweave revise [work-id] <決策變更>
$devweave approve [work-id]
```

Codex 會把這些對話命令路由到 `.agents/skills/devweave/scripts/devweave.py`。初始化後，產品程式、測試、schema、dependency、build 或 CI 相關修改必須先綁定 active work item，且實作前必須具備仍有效的 G2 核准。

## 內部 CLI

CLI 永遠輸出 UTF-8 JSON，適合 Codex 與其他自動化讀取：

```powershell
python .agents/skills/devweave/scripts/devweave.py --repo . init
python .agents/skills/devweave/scripts/devweave.py --repo . start --kind feature --title "新增查詢能力" --rationale "標準風險"
python .agents/skills/devweave/scripts/devweave.py --repo . status --all
python .agents/skills/devweave/scripts/devweave.py --repo . instructions --work <work-id>
python .agents/skills/devweave/scripts/devweave.py --repo . validate --work <work-id> --gate scope
```

設定多個 scope 路徑時要在同一次呼叫重複 `--path`；每次 `scope` 呼叫都會取代完整集合：

```powershell
python .agents/skills/devweave/scripts/devweave.py --repo . scope `
  --work <work-id> --path src --path tests --rationale "產品程式與測試"
```

語言中立的驗證命令以 argv array 儲存，不經 shell 解譯：

```powershell
python .agents/skills/devweave/scripts/devweave.py --repo . command set `
  --id full-tests --cwd . --timeout 900 `
  --required-for standard high -- project-test-command --all
```

初始化時 Codex 應從 README、manifest、CI 與既有 scripts 提議實際的 build、test、lint 或 typecheck 命令。缺少必要命令時 G3 會被阻擋，除非留下範圍明確且有核准人的 waiver。

## Repository contract

```text
.agents/skills/devweave/       standalone router、references、templates、engine
.codex/hooks.json              Codex PreToolUse guard
AGENTS.md                      repo activation 與治理規則
.devweave/project.json         專案設定與語言中立驗證命令
.devweave/work-items/<id>/     state、events、artifacts、evidence summaries
.devweave/baseline/            accepted product、architecture、quality、capabilities
.devweave/cache/               session bindings 與 raw logs（gitignored）
```

DevWeave 只觀察 branch、HEAD 與 diff，不會自行建立 branch、worktree、commit、push、PR 或部署。Hook 是 Codex guardrail，不是作業系統 sandbox；停用 hook 或使用外部編輯器時，它無法阻止修改。

`bind` 由 PreToolUse hook 取得真正的 Codex session ID。若 CLI 顯示 `status: awaiting_hook`，且 Codex 沒有回傳已綁定的 additional context，就只能視為「已提出綁定請求」，不可宣稱 guard 已生效；請先確認 repo hook 已信任且未被停用。

詳細 machine contract 請見 [contracts.md](.agents/skills/devweave/references/contracts.md)。

## 驗證框架

全部測試只使用 Python 標準函式庫：

```powershell
python -B -m unittest discover -s tests -v
python C:\path\to\skill-creator\scripts\quick_validate.py .agents\skills\devweave
```

`fixtures/devweave/` 提供 `new`、`feature`、`refactor`、`bug` 四種端到端情境；測試也涵蓋非法 transition、核准失效、timeout、log 截斷、多工作項歧義與 guard allow/deny。
