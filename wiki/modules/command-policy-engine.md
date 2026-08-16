---
title: Command Policy Engine
type: module
sources: [.agents/skills/devweave/scripts/command_policy.py, .agents/skills/devweave/scripts/devweave_core.py]
last_updated: 2026-08-16
tags: [module]
status: active
source_fingerprint: "sha256:0eb9465a22d650df0c938b595e14e7a238c0d7f6979e25b69dd3b08639074925"
verified_by: 20260814-233520-bug-guard-policy-engine-v2-side-effect-comma
---

# Command Policy Engine

## Responsibility

提供 DevWeave 唯一的 Verification Policy v2 evaluator：canonicalize project command metadata、trusted executable/hash、argv/cwd、phase/risk/session/release context、dependency closure、writes/outputs 與 policy/command digests，並把不確定輸入轉成 fail-closed decision。

## Public Surface

- `normalize_project_policy`、`policy_digest` 與 `command_definition_digest` 建立可比較的 policy identity。
- `evaluate` 是 Guard、CLI runner、Doctor、mutation validation 與 G3 admission 共用的 decision seam。
- `build_effective_plan` 在 G2 凍結 required/selected/skipped 集合、dependency stage、write barrier、expected exits 與 eligibility policy。
- `derive_evidence_eligibility` 由 engine 計算 `gate_eligible`；caller 不能用 status 或 expectation 覆寫它。
- `evaluate_read_only` 僅允許 typed argv grammar；shell operator、substitution、redirection、unknown/output flag、wrapper 或不安全 parse 一律拒絕。

## Dependencies

此 module 只依賴標準 library 與 repository policy data，不擁有 Work Item ledger。`devweave_core.py` 是 lifecycle coordinator，`guard.py`、`devweave.py` 與 G3 是 adapters；副作用命令由 core 的 controlled executor 以 `shell=False`、固定 argv/cwd、bounded timeout 與 temporary candidate 執行。

## Behavior and Gaps

G2 前 `writes != none` 不得執行；configured command 不得直接由 Bash 取得執行權。writer 依 dependency/stage serial 執行，candidate fingerprint 凍結後才允許 writes:none parallel stage；shared output boundary 自動形成 exclusive group。pre/post snapshot 會把 writes:none effect、undeclared write、scope 外變更、timeout、postcondition/promotion failure 設為 failed/ineligible，並拒絕 promotion。

Formal G3 evidence 必須是 controlled executor 的 current zero-exit success，且 plan、project policy、command definition、source/input/output fingerprints 均 current。`expect=nonzero`、`expect=any`、reproduction、diagnostic、failed、stale digest/source 與 undeclared writes 僅可作診斷或 reproduction，不能滿足 required command、AC coverage 或 required evidence kind。policy mutation 透過 typed path 使既有 plan/evidence stale；本 module 不宣稱 OS-level network sandbox，`network` 僅是顯式 policy boundary。

Dependency skip reason 也是 plan data：當 dependency 是 release-only 且沒有 explicit release context，dependent command 保存 `release-only-dependency:<id>`，Runner 與 G3 都將它視為合法 not-required-for-this-context，不自行重建 required set。
