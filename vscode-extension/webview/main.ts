import { parseActionIntent } from "../src/protocol";
import type { HostToWebviewMessage, WebviewToHostMessage } from "../src/protocol";
import type { ActionIntent, WorkspaceSnapshot } from "../src/model";

declare function acquireVsCodeApi<T>(): { postMessage(message: T): void };

type AppApi = { postMessage(message: WebviewToHostMessage): void };
const api: AppApi = acquireVsCodeApi<WebviewToHostMessage>();
let snapshot: WorkspaceSnapshot | null = null;
let selectedWorkId: string | null = null;
let pendingIntent: ActionIntent | null = null;

window.addEventListener("message", (event) => {
  const message = event.data;
  if (!isHostMessage(message)) return;
  if (message.type === "snapshot") {
    snapshot = message.snapshot;
    selectedWorkId = snapshot.selectedWorkId ?? snapshot.workItems?.[0]?.id ?? null;
    render();
  }
  if (message.type === "bootstrapResult") {
    snapshot = message.snapshot;
    selectedWorkId = snapshot.selectedWorkId ?? snapshot.workItems?.[0]?.id ?? null;
    render();
    renderBootstrapResult(message.report);
  }
  if (message.type === "copyResult") {
    renderCopyResult(message);
  }
  if (message.type === "actionPreview") {
    renderActionPreview(message.bundle);
  }
  if (message.type === "protocolError") {
    setStatus(`Protocol warning: ${message.message}`, true);
  }
  if (message.type === "error") {
    setStatus(message.message, true);
  }
});

document.addEventListener("click", (event) => {
  const target = event.target as HTMLElement;
  const button = target.closest<HTMLElement>("[data-action]");
  if (!button) return;
  const action = button.dataset.action;
  if (action === "refresh") {
    api.postMessage({ type: "refresh" });
  } else if (action === "initialize") {
    api.postMessage({ type: "initialize" });
  } else if (action === "preview") {
    const intent = parseIntent(button.dataset.intent);
    if (intent) {
      pendingIntent = intent;
      api.postMessage({ type: "previewAction", intent });
    }
  } else if (action === "confirm-copy") {
    if (pendingIntent) {
      api.postMessage({ type: "copyAction", intent: pendingIntent });
      pendingIntent = null;
    }
  } else if (action === "cancel-preview") {
    pendingIntent = null;
    const panel = document.querySelector<HTMLElement>("#copy-preview");
    panel?.classList.add("hidden");
    setStatus("Preview cancelled.", false);
  } else if (action === "open") {
    const path = button.dataset.path;
    if (path) api.postMessage({ type: "openFile", path });
  } else if (action === "compose-json") {
    const input = document.querySelector<HTMLTextAreaElement>("#intent-json");
    if (!input) return;
    try {
      const intent = parseIntent(input.value);
      if (!intent) {
        setStatus("Action JSON 格式錯誤或不符合 DevWeave contract。", true);
        return;
      }
      pendingIntent = intent;
      api.postMessage({ type: "previewAction", intent });
    } catch {
      setStatus("Action JSON 格式錯誤。", true);
    }
  }
});

document.addEventListener("change", (event) => {
  const target = event.target as HTMLSelectElement;
  if (target.id === "work-select") {
    selectedWorkId = target.value || null;
    api.postMessage({ type: "selectWork", workId: selectedWorkId });
    render();
  }
  if (target.id === "action-template") {
    const input = document.querySelector<HTMLTextAreaElement>("#intent-json");
    if (input) input.value = target.value;
  }
});

function render(): void {
  const app = document.querySelector<HTMLElement>("#app");
  if (!app || !snapshot) return;
  const current = snapshot;
  const resolvedSelection = selectedWorkId && current.workItems?.some((item: any) => item.id === selectedWorkId)
    ? selectedWorkId
    : current.workItems?.length === 1 ? current.workItems[0].id : null;
  selectedWorkId = resolvedSelection;
  const work = resolvedSelection ? current.workItems?.find((item: any) => item.id === resolvedSelection) ?? null : null;
  app.innerHTML = `
    <header class="topbar">
      <div>
        <p class="eyebrow">DEVWEAVE CONTROL CENTER</p>
        <h1>${escapeHtml(current.rootName ?? "Repository workspace")}</h1>
        <p class="muted">唯讀 filesystem snapshot · ${escapeHtml(current.capturedAt ?? "unknown")}</p>
      </div>
      <div class="toolbar">
        <button class="secondary" data-action="refresh" aria-label="重新整理 snapshot">↻ Refresh</button>
        ${quickIntentButton({ type: "doctor" }, "Doctor")}
      </div>
    </header>
    ${renderDiagnostics()}
    ${renderRepositoryState()}
    ${renderWorkSelector()}
    ${work ? renderWork(work) : renderEmptyWork()}
    ${renderActionComposer(work)}
    <div id="copy-status" class="status-line" aria-live="polite"></div>
    <section id="copy-preview" class="preview hidden" aria-label="Codex Chat action preview"></section>
  `;
}

function renderDiagnostics(): string {
  if (!snapshot) return "";
  const current = snapshot;
  const diagnostics = current.diagnostics ?? [];
  const blocked = current.mutationBlocked ? `<div class="notice critical"><span class="status-icon">!</span><div><strong>Read-only diagnostic state</strong><p>Mutation actions are disabled until the contract is repaired or confirmed through Codex Chat.</p></div></div>` : "";
  if (!diagnostics.length && !blocked) return "";
  return `<section class="notice-stack" aria-label="Repository diagnostics">${blocked}
    ${diagnostics.map((item: any) => `<div class="notice ${item.severity}"><span class="status-icon">${icon(item.severity)}</span><div><strong>${escapeHtml(item.code)}</strong><p>${escapeHtml(item.message)}</p>${item.path ? `<code>${escapeHtml(item.path)}</code>` : ""}</div></div>`).join("")}
  </section>`;
}

function renderRepositoryState(): string {
  if (!snapshot) return "";
  const current = snapshot;
  const managed = current.managed === true ? "Managed" : current.managed === false ? "Explicit activation required" : "Not initialized";
  const action = current.mutationBlocked
    ? quickIntentButton({ type: "doctor" }, "Copy diagnostic prompt", "primary")
    : current.projectExists
      ? quickIntentButton({ type: "status", all: true }, "Copy status refresh", "primary")
      : `<button class="primary" data-action="initialize">Initialize DevWeave</button>`;
  return `<section class="hero-card">
    <div><span class="pill ${current.managed === true ? "success" : "warning"}">${escapeHtml(managed)}</span><h2>${current.projectExists ? "DevWeave is ready to inspect" : "Start with DevWeave initialization"}</h2><p class="muted">${current.projectExists ? "既有 workflow action 仍會先 preview 並由 Codex Chat 執行。" : "確認後由 Extension 直接建立 DevWeave runtime、project、baseline 與 Wiki starter。"}</p></div>
    ${action}
  </section>${renderRepositoryMetadata(current)}`;
}

function renderRepositoryMetadata(current: WorkspaceSnapshot): string {
  const profiles = Object.entries(current.verificationProfiles ?? {}).map(([name, ids]) => `${name}: ${(ids as string[]).join(", ") || "none"}`).join(" · ") || "none";
  const freshness = current.engineObservedAt && current.capturedAt > current.engineObservedAt
    ? `<div class="notice warning"><span class="status-icon">•</span><div><strong>Snapshot may be newer than engine-observed state</strong><p>請在 Codex Chat 執行 status/validate，再重新整理；Extension 不自行重建 fingerprint。</p></div></div>`
    : "";
  return `<section class="section-card repository-meta"><div class="metric-grid"><div class="metric"><span>Project</span><strong>${escapeHtml(current.projectPath)}</strong></div><div class="metric"><span>Snapshot</span><strong>${escapeHtml(current.capturedAt)}</strong></div><div class="metric"><span>Last engine-observed</span><strong>${escapeHtml(current.engineObservedAt ?? "not observed")}</strong></div><div class="metric"><span>Source</span><strong>Filesystem snapshot</strong></div></div><div class="meta-line"><span class="pill ${current.hookPresent ? "success" : "warning"}">${current.hookPresent ? "hook present" : "hook missing"}</span><span class="pill ${current.skillPresent ? "success" : "warning"}">${current.skillPresent ? "skill present" : "skill missing"}</span><span class="muted">verification profiles: ${escapeHtml(profiles)}</span></div>${freshness}</section>`;
}

function renderWorkSelector(): string {
  if (!snapshot) return "";
  const items = snapshot.workItems ?? [];
  if (!items.length) return "";
  const placeholder = items.length > 1 && !selectedWorkId ? `<option value="" selected>選擇 work item（required）</option>` : "";
  return `<section class="section-card compact"><label for="work-select">${items.length > 1 ? "Select work item" : "Active work item"}</label><select id="work-select" aria-label="選擇 DevWeave work item">${placeholder}${items.map((item: any) => `<option value="${escapeAttr(item.id)}" ${item.id === selectedWorkId ? "selected" : ""}>${escapeHtml(item.title)} · ${escapeHtml(item.phase)}</option>`).join("")}</select></section>`;
}

function renderWork(work: any): string {
  if (!snapshot) return "";
  const current = snapshot;
  const taskDone = (work.tasks ?? []).filter((task: any) => task.status === "completed").length;
  const evidencePassed = (work.evidence ?? []).filter((item: any) => item.status === "passed" && !item.stale).length;
  return `<section class="section-card">
    <div class="section-heading"><div><p class="eyebrow">WORK ITEM</p><h2>${escapeHtml(work.title)}</h2><p class="muted mono">${escapeHtml(work.id)}</p></div><div class="pill-row"><span class="pill">${escapeHtml(work.kind)}</span><span class="pill ${work.risk === "high" ? "danger" : "info"}">${escapeHtml(work.risk)} risk</span><span class="pill">${escapeHtml(work.status)}</span></div></div>
    <div class="gate-grid">${gateCard(work, "scope", "G1 Scope", current)} ${gateCard(work, "build", "G2 Build", current)} ${gateCard(work, "acceptance", "G3 Acceptance", current)}</div>
    <div class="metric-grid"><div class="metric"><span>Phase</span><strong>${escapeHtml(work.phase)}</strong></div><div class="metric"><span>Tasks</span><strong>${taskDone}/${(work.tasks ?? []).length}</strong></div><div class="metric"><span>Evidence</span><strong>${evidencePassed}/${(work.evidence ?? []).length}</strong></div><div class="metric"><span>Knowledge</span><strong>${escapeHtml(work.knowledge?.health ?? "unknown")}</strong></div></div>
    ${work.blocker ? `<div class="notice danger"><span class="status-icon">!</span><div><strong>Blocker · ${escapeHtml(work.blocker.task ?? "task")}</strong><p>${escapeHtml(work.blocker.reason ?? "")}</p></div></div>` : ""}
    <div class="action-row">${quickIntentButton({ type: "instructions", workId: work.id }, "Copy next action", "primary")} ${quickIntentButton({ type: "validate", workId: work.id, gate: currentGate(work) }, "Copy validate")}</div>
  </section>
  ${renderNextAction(work, current)}
  ${renderArtifacts(work)}
  ${renderRequirementsDesign(work)}
  ${renderKnowledge(work, current)}
  ${renderTasksEvidence(work)}
  ${renderVerification(work, current)}
  ${renderAcceptance(work, current)}
  ${renderAudit(work)}`;
}

function gateCard(work: any, gate: string, label: string, current: WorkspaceSnapshot): string {
  const value = work.gates?.[gate] ?? { status: "pending" };
  const status = value.status ?? "pending";
  const intent = { type: "approve", workId: work.id, gate };
  const approvalNote = status !== "approved" && work.phase !== "closed" ? `<small class="approval-note">人工 gate · 複製不代表已核准</small>` : "";
  return `<article class="gate-card ${escapeAttr(status)}"><div class="gate-title"><span class="status-icon">${icon(status)}</span><span>${label}</span></div><strong>${escapeHtml(status)}</strong><p class="muted">${value.approvedAt ? escapeHtml(value.approvedAt) : "等待目前 phase 的 engine validation"}</p>${approvalNote}${!current.mutationBlocked && status !== "approved" && work.phase !== "closed" ? quickIntentButton(intent, `Review ${label}`) : ""}</article>`;
}

function renderNextAction(work: any, current: WorkspaceSnapshot): string {
  const next = nextSafeAction(work, current);
  return `<section class="next-action"><div><p class="eyebrow">NEXT SAFE ACTION</p><h2>${escapeHtml(next.title)}</h2><p class="muted">${escapeHtml(next.detail)}</p></div>${quickIntentButton(next.intent, "Copy to Codex Chat", "primary")}</section>`;
}

function nextSafeAction(work: any, current: WorkspaceSnapshot): { title: string; detail: string; intent: Record<string, unknown> } {
  if (work.status === "closed" || work.phase === "closed") {
    return { title: "Work item closed", detail: "這個 work item 僅供唯讀 audit；不提供版本控制或重新開啟操作。", intent: { type: "status", workId: work.id } };
  }
  if (work.blocker) {
    return { title: "Review the current blocker", detail: `${work.blocker.task ?? "Task"}: ${work.blocker.reason ?? "需要在 Codex Chat 處理 blocker。"}`, intent: { type: "instructions", workId: work.id } };
  }
  if (work.gates?.scope?.status !== "approved") {
    return work.phase === "requirements" || work.phase === "scope_review"
      ? { title: "完成 requirements 並 request G1", detail: "先確認 scope、risk 與 Wiki-first context，再由 engine 驗證 G1。", intent: { type: "instructions", workId: work.id } }
      : { title: "Request G1 Scope", detail: "這是人工核准；送出前請確認 current validation summary。", intent: { type: "approve", workId: work.id, gate: "scope" } };
  }
  if (work.gates?.build?.status !== "approved") {
    return work.phase === "design" || work.phase === "build_review"
      ? { title: "完成 design 並 request G2", detail: "確認 DEC、plan、task dependency 與 high-risk analysis。", intent: { type: "instructions", workId: work.id } }
      : { title: "Request G2 Build", detail: "G2 approval 會解鎖 implementation；複製不代表已核准。", intent: { type: "approve", workId: work.id, gate: "build" } };
  }
  if (work.phase === "implementation") {
    const pending = (work.tasks ?? []).find((task: any) => task.status === "pending");
    if (pending) {
      return { title: `Start ${pending.id}`, detail: "依 plan dependency 執行下一個 task，完成後以 evidence 回填。", intent: { type: "taskStart", workId: work.id, taskId: pending.id } };
    }
    return { title: "Run the next implementation instruction", detail: "所有已投影 task 已啟動或完成；請由 engine instructions 決定下一步。", intent: { type: "instructions", workId: work.id } };
  }
  if (work.phase === "verification" || work.phase === "acceptance_review") {
    return { title: "Verify and request G3", detail: "重新執行 configured commands，確認 evidence current、Wiki 與 baseline，再 request acceptance。", intent: { type: "validate", workId: work.id, gate: "acceptance" } };
  }
  return { title: "Follow current DevWeave instructions", detail: "Extension 只呈現 disk snapshot；請在 Codex Chat 執行 engine 指令後 Refresh。", intent: { type: "instructions", workId: work.id } };
}

function renderArtifacts(work: any): string {
  return `<section class="section-card"><div class="section-heading"><div><p class="eyebrow">TRACEABILITY</p><h2>Artifacts</h2><p class="muted">Requirements → design → plan → acceptance，保留標準 Markdown editor 開啟。</p></div><span class="muted">唯讀開啟</span></div><div class="artifact-list">${(work.artifacts ?? []).map((artifact: any) => `<button class="artifact" data-action="open" data-path="${escapeAttr(artifact.path)}" ${artifact.exists ? "" : "disabled"}><span class="file-icon">${artifact.exists ? "▤" : "—"}</span><span><strong>${escapeHtml(artifact.path.split("/").at(-1) ?? artifact.path)}</strong><small>${artifact.exists ? `${artifact.text.length} chars${artifact.truncated ? " · truncated" : ""}` : "missing"}</small></span></button>`).join("")}</div></section>`;
}

function renderRequirementsDesign(work: any): string {
  const groups = [
    { label: "Requirements", names: ["brief.md", "requirements.md"], hint: "REQ / NFR → AC" },
    { label: "Design", names: ["design.md"], hint: "DEC trace and high-risk decisions" },
    { label: "Plan", names: ["plan.md"], hint: "TASK dependency graph" }
  ];
  const artifacts = work.artifacts ?? [];
  return `<section class="section-card"><div class="section-heading"><div><p class="eyebrow">WORK DETAIL</p><h2>Requirements · Design · Plan</h2></div><span class="muted">ID trace projection</span></div><div class="trace-grid">${groups.map((group) => {
    const items = artifacts.filter((artifact: any) => group.names.includes(artifact.path.split("/").at(-1)));
    return `<article class="trace-card"><strong>${group.label}</strong><small>${group.hint}</small>${items.map((artifact: any) => `<div class="trace-row"><span>${artifact.exists ? icon("active") : icon("warning")}</span><span><b>${escapeHtml(artifact.path.split("/").at(-1))}</b><small>${artifact.exists ? traceIds(artifact.text).join(" · ") || "No trace IDs detected" : "missing"}</small></span></div>`).join("")}</article>`;
  }).join("")}</div></section>`;
}

function renderKnowledge(work: any, current: WorkspaceSnapshot): string {
  const knowledge = work.knowledge ?? current.knowledge;
  const pages = knowledge.pages ?? [];
  const categoryCounts = pages.reduce((counts: Record<string, number>, page: any) => { counts[page.type] = (counts[page.type] ?? 0) + 1; return counts; }, {});
  const categories = Object.entries(categoryCounts).map(([type, count]) => `<span class="pill">${escapeHtml(type)} ${escapeHtml(count)}</span>`).join("");
  return `<section class="section-card"><div class="section-heading"><div><p class="eyebrow">WIKI-FIRST KNOWLEDGE</p><h2>Knowledge health</h2></div><span class="pill ${knowledge.health === "healthy" ? "success" : "warning"}">${escapeHtml(knowledge.health ?? "unknown")}</span></div><div class="notice info"><span class="status-icon">i</span><div><strong>G1 fixed read order</strong><p><code>wiki/index.md</code> first, followed by at most five related pages. Raw sources are only for recorded gaps.</p></div></div><div class="pill-row">${categories || `<span class="muted">No Wiki categories detected.</span>`}</div><div class="metric-grid"><div class="metric"><span>Pages</span><strong>${pages.length}</strong></div><div class="metric"><span>Placeholder</span><strong>${(knowledge.placeholderPages ?? []).length}</strong></div><div class="metric"><span>Stale</span><strong>${(knowledge.stalePages ?? []).length}</strong></div><div class="metric"><span>Pending refresh</span><strong>${(knowledge.pendingRefresh ?? []).length}</strong></div></div><div class="page-list">${pages.slice(0, 12).map((page: any) => `<button class="page-row" data-action="open" data-path="${escapeAttr(page.path)}"><span>${icon(page.status)}</span><span><strong>${escapeHtml(page.title)}</strong><small>${escapeHtml(page.path)} · ${escapeHtml(page.status)}${page.parseErrors?.length ? " · parse warning" : ""}</small></span></button>`).join("")}</div><div class="action-row">${quickIntentButton({ type: "knowledgeStatus", workId: work.id }, "Copy knowledge status")} ${!current.mutationBlocked ? quickIntentButton({ type: "knowledgeContext", workId: work.id, pages: ["wiki/index.md"], gaps: [] }, "Copy G1 context") : ""}</div></section>`;
}

function renderTasksEvidence(work: any): string {
  return `<section class="section-card"><div class="section-heading"><div><p class="eyebrow">IMPLEMENTATION</p><h2>Task board</h2></div><span class="muted">pending · in progress · completed · blocked</span></div><div class="task-list">${(work.tasks ?? []).map((task: any) => `<div class="task-row"><span class="status-icon">${icon(task.status)}</span><span><strong>${escapeHtml(task.id)}</strong><small>${escapeHtml(task.status)}${task.note ? ` · ${escapeHtml(task.note)}` : ""}${task.evidence?.length ? ` · evidence ${escapeHtml(task.evidence.join(", "))}` : ""}</small></span></div>`).join("") || `<p class="muted">G2 approval will create the machine task ledger.</p>`}</div></section>`;
}

function renderVerification(work: any, current: WorkspaceSnapshot): string {
  const commands = current.commands ?? [];
  const profiles = Object.entries(current.verificationProfiles ?? {}).map(([name, ids]) => `<span class="pill info">${escapeHtml(name)}: ${escapeHtml((ids as string[]).join(", ") || "none")}</span>`).join("");
  const evidence = work.evidence ?? [];
  return `<section class="section-card"><div class="section-heading"><div><p class="eyebrow">VERIFICATION</p><h2>Commands and evidence</h2><p class="muted">只顯示 command metadata、exit code 與 raw-log path；不把 raw log 內容放入 Webview 或 clipboard。</p></div><div class="pill-row">${profiles || `<span class="pill warning">profiles unavailable</span>`}</div></div><div class="command-list">${commands.map((command: any) => `<div class="command-row"><span class="status-icon">⌘</span><span><strong>${escapeHtml(command.id)}</strong><small>${escapeHtml(command.argv.join(" "))} · cwd ${escapeHtml(command.cwd)} · timeout ${escapeHtml(command.timeoutSeconds)}s</small></span></div>`).join("") || `<p class="muted">No verification command configured.</p>`}</div><div class="evidence-list">${evidence.map((item: any) => `<article class="evidence-card"><div class="section-heading"><strong>${escapeHtml(item.id)} · ${escapeHtml(item.kind)}</strong><span class="pill ${item.status === "passed" && !item.stale ? "success" : item.stale ? "warning" : "danger"}">${escapeHtml(item.status)}${item.stale ? " · stale" : ""}</span></div><p>${escapeHtml(item.summary)}</p><small>covers ${escapeHtml(item.covers.join(", ") || "—")} · tasks ${escapeHtml(item.tasks.join(", ") || "—")} · command ${escapeHtml(item.commandId ?? "—")} · exit ${escapeHtml(item.exitCode ?? "—")}</small>${item.rawLog ? `<code class="raw-log-path">raw log: ${escapeHtml(item.rawLog)}</code>` : ""}</article>`).join("") || `<p class="muted">No evidence recorded.</p>`}</div></section>`;
}

function renderAcceptance(work: any, current: WorkspaceSnapshot): string {
  const planned = work.knowledge?.planned;
  const waivers = work.waivers ?? [];
  const declaredBaseline = work.baselineTargets ?? [];
  const coupled = planned && Array.isArray(planned.coupled) ? (planned.coupled as string[]) : [];
  const sealed = planned && Array.isArray(planned.sealed) ? (planned.sealed as string[]) : [];
  return `<section class="section-card"><div class="section-heading"><div><p class="eyebrow">ACCEPTANCE</p><h2>AC · TASK · evidence matrix</h2><p class="muted">G3 前確認 current source fingerprint、baseline targets、Wiki promotion 與 waivers。</p></div><span class="pill ${work.gates?.acceptance?.status === "approved" ? "success" : "warning"}">${escapeHtml(work.gates?.acceptance?.status ?? "pending")}</span></div><div class="acceptance-grid"><div><strong>Baseline targets</strong><ul>${declaredBaseline.map((path: string) => `<li><code>${escapeHtml(path)}</code></li>`).join("") || "<li>none declared yet</li>"}</ul><small>${escapeHtml(work.baselineRationale || "")}</small></div><div><strong>Wiki promotion</strong><ul><li>affected: ${escapeHtml(work.knowledge?.affectedPages?.join(", ") || "none")}</li><li>pending refresh: ${escapeHtml(work.knowledge?.pendingRefresh?.join(", ") || "none")}</li><li>planned upsert/delete: ${escapeHtml(planned ? `${(planned.upserts as string[] ?? []).join(", ")} / ${(planned.deletes as string[] ?? []).join(", ")}` : "none")}</li><li>coupled index/log: ${escapeHtml(coupled.join(", ") || "not planned")}</li><li>sealed: ${escapeHtml(sealed.join(", ") || "not sealed")}</li></ul></div></div><div class="waiver-list"><strong>Waivers</strong>${waivers.map((waiver: any) => `<div class="task-row"><span class="status-icon">!</span><span><b>${escapeHtml(waiver.kind)} · ${escapeHtml(waiver.target)}</b><small>${escapeHtml(waiver.reason)}${waiver.gate ? ` · gate ${escapeHtml(waiver.gate)}` : ""}</small></span></div>`).join("") || `<p class="muted">No waivers recorded.</p>`}</div></section>`;
}

function renderAudit(work: any): string {
  const events = work.events ?? [];
  return `<section class="section-card"><div class="section-heading"><div><p class="eyebrow">AUDIT</p><h2>Governance event log</h2></div><span class="muted">唯讀 · no compare/revert/branch operations</span></div><div class="audit-list">${events.slice(-12).map((event: string) => `<code>${escapeHtml(event)}</code>`).join("") || `<p class="muted">No events recorded.</p>`}</div></section>`;
}

function traceIds(text: string): string[] {
  return [...new Set(text.match(/\b(?:REQ|NFR|AC|DEC|TASK)-\d{3}\b/g) ?? [])].slice(0, 12);
}

function renderEmptyWork(): string {
  if (snapshot?.workItems?.length && snapshot.workItems.length > 1) {
    return `<section class="empty-card"><span class="empty-icon">⌁</span><h2>Select a work item</h2><p class="muted">目前有多個 eligible work items；請先在上方選擇 work ID，Extension 不會猜測目前 work。</p></section>`;
  }
  return `<section class="empty-card"><span class="empty-icon">＋</span><h2>No work item selected</h2><p class="muted">建立或選擇 work item 後，這裡會顯示 phase、gate、artifact、task、evidence 與 Wiki 狀態。</p>${quickIntentButton({ type: "start", kind: "feature", title: "在此輸入功能名稱", risk: "standard", rationale: "請在 Codex Chat 中補充需求、範圍與風險理由。" }, "Copy feature start prompt", "primary")}</section>`;
}

function renderActionComposer(work: any): string {
  const id = work?.id ?? "<work-id>";
  const templates = [
    ["init", JSON.stringify({ type: "init", goal: "建立第一個可驗證的 DevWeave work item" }, null, 2)],
    ["doctor", JSON.stringify({ type: "doctor" }, null, 2)],
    ["project", JSON.stringify({ type: "project" }, null, 2)],
    ["command list", JSON.stringify({ type: "commandList" }, null, 2)],
    ["command set", JSON.stringify({ type: "commandSet", id: "extension-tests", cwd: "vscode-extension", argv: ["npm", "test"], timeout: 240, requiredFor: ["high", "standard"] }, null, 2)],
    ["command remove", JSON.stringify({ type: "commandRemove", id: "extension-tests" }, null, 2)],
    ["start feature", JSON.stringify({ type: "start", kind: "feature", title: "輸入功能名稱", risk: "standard", rationale: "請補充風險與範圍理由。" }, null, 2)],
    ["status", JSON.stringify({ type: "status", workId: id }, null, 2)],
    ["instructions", JSON.stringify({ type: "instructions", workId: id }, null, 2)],
    ["validate", JSON.stringify({ type: "validate", workId: id, gate: currentGate(work) ?? "scope" }, null, 2)],
    ["bind", JSON.stringify({ type: "bind", workId: id }, null, 2)],
    ["risk", JSON.stringify({ type: "risk", workId: id, level: "standard", rationale: "請在 Codex Chat 中補充風險理由。" }, null, 2)],
    ["scope", JSON.stringify({ type: "scope", workId: id, paths: ["vscode-extension/**"], rationale: "限制在 approved scope。" }, null, 2)],
    ["baseline", JSON.stringify({ type: "baseline", workId: id, targets: [".devweave/baseline/architecture.md"], rationale: "請補充 accepted architecture boundary。" }, null, 2)],
    ["knowledge status", JSON.stringify({ type: "knowledgeStatus", workId: id }, null, 2)],
    ["knowledge context", JSON.stringify({ type: "knowledgeContext", workId: id, pages: ["wiki/index.md"], gaps: [] }, null, 2)],
    ["knowledge plan", JSON.stringify({ type: "knowledgePlan", workId: id, upserts: [], deletes: [], rationale: "請在 verification 中補充 knowledge targets。" }, null, 2)],
    ["knowledge seal", JSON.stringify({ type: "knowledgeSeal", workId: id, pages: ["wiki/index.md"] }, null, 2)],
    ["task start", JSON.stringify({ type: "taskStart", workId: id, taskId: "TASK-001" }, null, 2)],
    ["task complete", JSON.stringify({ type: "taskComplete", workId: id, taskId: "TASK-001", evidence: [], note: "請補充完成摘要。" }, null, 2)],
    ["task block", JSON.stringify({ type: "taskBlock", workId: id, taskId: "TASK-001", note: "請補充 blocker。" }, null, 2)],
    ["evidence add", JSON.stringify({ type: "evidenceAdd", workId: id, kind: "review", status: "passed", summary: "請在 Codex Chat 中補充 evidence summary。", covers: ["AC-001"], tasks: ["TASK-001"], observedResult: "success" }, null, 2)],
    ["verify", JSON.stringify({ type: "verify", workId: id, command: "unit-tests", kind: "test", covers: ["AC-001"], tasks: ["TASK-001"], expect: "zero" }, null, 2)],
    ["waiver add", JSON.stringify({ type: "waiverAdd", workId: id, kind: "risk", target: "AC-001", reason: "請補充 narrow waiver reason。", gate: "build" }, null, 2)],
    ["approve", JSON.stringify({ type: "approve", workId: id, gate: currentGate(work) ?? "scope" }, null, 2)],
    ["revise", JSON.stringify({ type: "revise", workId: id, from: "design", reason: "請說明需要重新規劃的原因。" }, null, 2)],
    ["close", JSON.stringify({ type: "close", workId: id }, null, 2)]
  ];
  return `<section class="section-card composer"><div class="section-heading"><div><p class="eyebrow">ACTION COMPOSER</p><h2>Preview any DevWeave action</h2></div><span class="muted">先 preview，再由使用者 confirm copy</span></div><label for="action-template">Template</label><select id="action-template" aria-label="選擇 DevWeave action template">${templates.map(([label, value]) => `<option value="${escapeAttr(value)}">${escapeHtml(label)}</option>`).join("")}</select><label for="intent-json">ActionIntent JSON</label><textarea id="intent-json" rows="9" spellcheck="false">${escapeHtml(templates[0][1])}</textarea><button class="primary" data-action="compose-json">Preview action</button></section>`;
}

function quickIntentButton(intent: any, label: string, style = "secondary"): string {
  return `<button class="${style}" data-action="preview" data-intent="${escapeAttr(JSON.stringify(intent))}">${escapeHtml(label)}</button>`;
}

function renderActionPreview(bundle: any): void {
  const panel = document.querySelector<HTMLElement>("#copy-preview");
  if (!panel) return;
  const intentType = pendingIntent?.type ?? "action";
  const targets = (bundle.targetPaths ?? []).map((path: string) => `<li><code>${escapeHtml(path)}</code></li>`).join("") || "<li>engine-owned state inferred from work ID</li>";
  panel.classList.remove("hidden");
  panel.innerHTML = `<div class="preview-heading"><div><p class="eyebrow">ACTION PREVIEW</p><h2>Review before copy</h2></div><span class="pill ${bundle.mutation ? "warning" : "info"}">${bundle.mutation ? "mutation · manual send" : "read-only"}</span></div><p class="muted">${escapeHtml(intentType)} · ${escapeHtml(bundle.workId ?? "repository action")}${bundle.gate ? ` · gate ${escapeHtml(bundle.gate)}` : ""}</p><div class="notice warning"><span class="status-icon">!</span><div><strong>此 Extension 不會執行</strong><p>確認後只會複製到 clipboard；仍需由使用者在 Codex Chat 審閱並送出。</p></div></div><h3>Expected state effect</h3><p class="muted">Extension 不會改變 repository bytes。送出後由既有 DevWeave engine 更新其 state/event/evidence 或宣告的 Wiki/baseline targets。</p><h3>Target paths</h3><ul>${targets}</ul><h3>Codex Chat text</h3><pre>${escapeHtml(bundle.chatText ?? "")}</pre>${bundle.machineCommand ? `<h3>Machine command</h3><pre>${escapeHtml(bundle.machineCommand)}</pre>` : ""}${(bundle.warnings ?? []).length ? `<div class="notice warning"><strong>Review warnings</strong><ul>${bundle.warnings.map((warning: string) => `<li>${escapeHtml(warning)}</li>`).join("")}</ul></div>` : ""}<div class="action-row"><button class="primary" data-action="confirm-copy">Confirm and copy</button><button class="secondary" data-action="cancel-preview">Cancel</button></div>`;
  setStatus("請審閱完整 preview，再確認複製到 Codex Chat。", false);
  panel.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
}

function renderCopyResult(message: any): void {
  const panel = document.querySelector<HTMLElement>("#copy-preview");
  if (!panel) return;
  if (!message.ok) {
    panel.classList.remove("hidden");
    panel.innerHTML = `<div class="notice danger"><strong>Copy failed</strong><p>${escapeHtml(message.message ?? "Unknown error")}</p></div>`;
    return;
  }
  const bundle = message.bundle ?? {};
  panel.classList.remove("hidden");
  const targets = (bundle.targetPaths ?? []).map((path: string) => `<li><code>${escapeHtml(path)}</code></li>`).join("") || "<li>engine-owned state inferred from work ID</li>";
  panel.innerHTML = `<div class="preview-heading"><div><p class="eyebrow">ACTION PREVIEW</p><h2>已複製到 clipboard</h2></div><span class="pill ${bundle.mutation ? "warning" : "info"}">${bundle.mutation ? "mutation · manual send" : "read-only"}</span></div><p class="muted">${escapeHtml(bundle.workId ?? "repository action")}${bundle.gate ? ` · gate ${escapeHtml(bundle.gate)}` : ""} · Extension 不會自行執行。</p><h3>Target paths</h3><ul>${targets}</ul><h3>Codex Chat text</h3><pre>${escapeHtml(bundle.chatText ?? "")}</pre>${bundle.machineCommand ? `<h3>Machine command</h3><pre>${escapeHtml(bundle.machineCommand)}</pre>` : ""}${(bundle.warnings ?? []).length ? `<div class="notice warning"><strong>Review before sending</strong><ul>${bundle.warnings.map((warning: string) => `<li>${escapeHtml(warning)}</li>`).join("")}</ul></div>` : ""}`;
  setStatus("Prompt 已複製；請在 Codex Chat 審閱並送出。", false);
  panel.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
}

function renderBootstrapResult(report: any): void {
  const panel = document.querySelector<HTMLElement>("#copy-preview");
  if (!panel) return;
  const list = (values: string[]) => values?.length ? `<ul>${values.map((value) => `<li><code>${escapeHtml(value)}</code></li>`).join("")}</ul>` : "<p class=\"muted\">none</p>";
  const conflicts = (report.conflicts ?? []).map((item: any) => `<li><code>${escapeHtml(item.path)}</code> · ${escapeHtml(item.reason)}</li>`).join("");
  const errors = (report.errors ?? []).map((item: any) => `<li><code>${escapeHtml(item.path)}</code> · ${escapeHtml(item.reason)}</li>`).join("");
  panel.classList.remove("hidden");
  panel.innerHTML = `<div class="preview-heading"><div><p class="eyebrow">DEVWEAVE BOOTSTRAP</p><h2>${report.ok ? "Initialization complete" : "Initialization not completed"}</h2></div><span class="pill ${report.ok ? "success" : "danger"}">${escapeHtml(report.status ?? "failed")}</span></div><p class="muted">這次操作未經 Codex Chat；Extension 只寫入固定 bootstrap manifest 目標。</p><h3>Created</h3>${list(report.created ?? [])}<h3>Adopted</h3>${list(report.adopted ?? [])}<h3>Skipped</h3>${list(report.skipped ?? [])}${conflicts ? `<h3>Conflicts</h3><ul>${conflicts}</ul>` : ""}${errors ? `<h3>Errors</h3><ul>${errors}</ul>` : ""}${(report.rolledBack ?? []).length ? `<h3>Rolled back</h3>${list(report.rolledBack)}` : ""}`;
  setStatus(report.ok ? "DevWeave bootstrap 完成。" : "DevWeave bootstrap 未完成，請先處理 conflict/error。", !report.ok);
  panel.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
}

function setStatus(message: string, error: boolean): void {
  const status = document.querySelector<HTMLElement>("#copy-status");
  if (status) {
    status.textContent = message;
    status.className = `status-line ${error ? "error" : "success"}`;
  }
}

function currentGate(work: any): string | undefined {
  if (!work) return undefined;
  if (["requirements", "scope_review"].includes(work.phase)) return "scope";
  if (["design", "build_review"].includes(work.phase)) return "build";
  if (["verification", "acceptance_review"].includes(work.phase)) return "acceptance";
  return undefined;
}

function parseIntent(value: string | undefined): ActionIntent | null {
  if (!value) return null;
  try { return parseActionIntent(JSON.parse(value)); } catch { return null; }
}

function isHostMessage(value: unknown): value is HostToWebviewMessage {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const type = (value as { type?: unknown }).type;
  return type === "snapshot" || type === "bootstrapResult" || type === "actionPreview" || type === "copyResult" || type === "protocolError" || type === "error";
}

function icon(status: string): string {
  if (["approved", "passed", "completed", "healthy", "active", "success"].includes(status)) return "✓";
  if (["failed", "blocked", "critical", "danger"].includes(status)) return "!";
  if (["stale", "warning", "placeholder", "pending", "in_progress"].includes(status)) return "•";
  return "·";
}

function escapeHtml(value: unknown): string {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function escapeAttr(value: unknown): string {
  return escapeHtml(value).replaceAll("\n", "&#10;");
}
