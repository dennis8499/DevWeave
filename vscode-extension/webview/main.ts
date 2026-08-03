import { parsePublicCommandIntent } from "../src/protocol";
import type { HostToWebviewMessage, WebviewToHostMessage } from "../src/protocol";
import type { PublicCommandIntent, PublicCommandName, WorkspaceSnapshot } from "../src/model";

declare function acquireVsCodeApi<T>(): { postMessage(message: T): void };

type AppApi = { postMessage(message: WebviewToHostMessage): void };
const api: AppApi = acquireVsCodeApi<WebviewToHostMessage>();
let snapshot: WorkspaceSnapshot | null = null;
let selectedWorkId: string | null = null;
let selectedCommand: PublicCommandName = "feature";
let pendingIntent: PublicCommandIntent | null = null;

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
  }
});

document.addEventListener("change", (event) => {
  const target = event.target as HTMLSelectElement;
  if (target.id === "work-select") {
    clearPendingPreview();
    selectedWorkId = target.value || null;
    api.postMessage({ type: "selectWork", workId: selectedWorkId });
    render();
  }
  if (target.id === "command-select") {
    if (isPublicCommandName(target.value)) {
      clearPendingPreview();
      selectedCommand = target.value;
      render();
    }
  }
});

document.addEventListener("submit", (event) => {
  const target = event.target as HTMLFormElement;
  if (target.id !== "public-command-form") return;
  event.preventDefault();
  const work = selectedWork();
  const intent = formIntent(target, work);
  if (!intent) {
    setStatus("請補齊必要欄位，並先選擇目前 work item。", true);
    return;
  }
  pendingIntent = intent;
  api.postMessage({ type: "previewAction", intent });
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
      </div>
    </header>
    ${renderDiagnostics()}
    ${renderRepositoryState()}
    ${renderWorkSelector()}
    ${renderPublicCommandForm(work)}
    ${work ? renderWork(work) : renderEmptyWork()}
    <div id="copy-status" class="status-line" aria-live="polite"></div>
    <section id="copy-preview" class="preview hidden" aria-label="Codex Chat public command preview"></section>
  `;
}

function renderDiagnostics(): string {
  if (!snapshot) return "";
  const current = snapshot;
  const diagnostics = current.diagnostics ?? [];
  const blocked = current.mutationBlocked ? `<div class="notice critical"><span class="status-icon">!</span><div><strong>Read-only diagnostic state</strong><p>Mutation public commands are disabled until the contract is repaired or confirmed through Codex Chat. The status command remains available.</p></div></div>` : "";
  if (!diagnostics.length && !blocked) return "";
  return `<section class="notice-stack" aria-label="Repository diagnostics">${blocked}
    ${diagnostics.map((item: any) => `<div class="notice ${item.severity}"><span class="status-icon">${icon(item.severity)}</span><div><strong>${escapeHtml(item.code)}</strong><p>${escapeHtml(item.message)}</p>${item.path ? `<code>${escapeHtml(item.path)}</code>` : ""}</div></div>`).join("")}
  </section>`;
}

function renderRepositoryState(): string {
  if (!snapshot) return "";
  const current = snapshot;
  const managed = current.managed === true ? "Managed" : current.managed === false ? "Explicit activation required" : "Not initialized";
  const action = current.projectExists
    ? `<span class="muted">公開命令表單可用；送出前會先預覽，Extension 不會直接執行 workflow。</span>`
    : `<button class="primary" data-action="initialize">Initialize DevWeave</button>`;
  return `<section class="hero-card">
    <div><span class="pill ${current.managed === true ? "success" : "warning"}">${escapeHtml(managed)}</span><h2>${current.projectExists ? "DevWeave is ready to inspect" : "Start with DevWeave initialization"}</h2><p class="muted">${current.projectExists ? "下方表單只產生公開 $devweave 對話命令；既有 gate、task、evidence 與 Wiki 僅供唯讀查看。" : "確認後由 Extension 直接建立 DevWeave runtime、project、baseline 與 Wiki starter。"}</p></div>
    ${action}
  </section>${renderRepositoryMetadata(current)}`;
}

function renderRepositoryMetadata(current: WorkspaceSnapshot): string {
  const profiles = Object.entries(current.verificationProfiles ?? {}).map(([name, ids]) => `${name}: ${(ids as string[]).join(", ") || "none"}`).join(" · ") || "none";
  const freshness = current.engineObservedAt && current.capturedAt > current.engineObservedAt
    ? `<div class="notice warning"><span class="status-icon">•</span><div><strong>Snapshot may be newer than engine-observed state</strong><p>請在 Codex Chat 使用 status 確認，再重新整理；Extension 不自行重建 fingerprint。</p></div></div>`
    : "";
  return `<section class="section-card repository-meta"><div class="metric-grid"><div class="metric"><span>Project</span><strong>${escapeHtml(current.projectPath)}</strong></div><div class="metric"><span>Snapshot</span><strong>${escapeHtml(current.capturedAt)}</strong></div><div class="metric"><span>Last engine-observed</span><strong>${escapeHtml(current.engineObservedAt ?? "not observed")}</strong></div><div class="metric"><span>Source</span><strong>Filesystem snapshot</strong></div></div><div class="meta-line"><span class="pill ${current.hookPresent ? "success" : "warning"}">${current.hookPresent ? "hook present" : "hook missing"}</span><span class="pill ${current.skillPresent ? "success" : "warning"}">${current.skillPresent ? "skill present" : "skill missing"}</span><span class="muted">verification profiles: ${escapeHtml(profiles)}</span></div>${freshness}</section>`;
}

function renderWorkSelector(): string {
  if (!snapshot) return "";
  const items = snapshot.workItems ?? [];
  if (!items.length) return "";
  const placeholder = items.length > 1 && !selectedWorkId ? `<option value="" selected>選擇 work item（必要）</option>` : "";
  return `<section class="section-card compact"><label for="work-select">${items.length > 1 ? "目前 work item（請先選擇）" : "目前 work item（自動帶入）"}</label><select id="work-select" aria-label="選擇 DevWeave work item">${placeholder}${items.map((item: any) => `<option value="${escapeAttr(item.id)}" ${item.id === selectedWorkId ? "selected" : ""}>${escapeHtml(item.title)} · ${escapeHtml(item.phase)}</option>`).join("")}</select></section>`;
}

function renderPublicCommandForm(work: any): string {
  const command = selectedCommand;
  const mutationDisabled = Boolean(snapshot?.mutationBlocked && ["new", "feature", "refactor", "bug", "revise", "approve"].includes(command));
  const requiresWork = command === "revise" || command === "approve";
  const disabled = mutationDisabled || (requiresWork && !work);
  return `<section class="section-card composer" aria-labelledby="public-command-title"><div class="section-heading"><div><p class="eyebrow">PUBLIC COMMANDS</p><h2 id="public-command-title">產生 Codex 對話命令</h2><p class="muted">只處理初始化與使用手冊列出的八個公開命令；先預覽，再複製到 Codex Chat。</p></div><span class="pill info">$devweave</span></div><form id="public-command-form"><label for="command-select">命令</label><select id="command-select" name="command" aria-label="選擇公開 DevWeave 命令">${publicCommandOptions(command)}</select>${renderCommandFields(command, work)}${mutationDisabled ? `<div class="notice warning"><span class="status-icon">!</span><div><strong>目前為 read-only diagnostic state</strong><p>請先使用 status 公開命令確認狀態；mutation 命令暫停產生。</p></div></div>` : ""}<div class="action-row"><button class="primary" type="submit" ${disabled ? "disabled" : ""}>Preview public command</button>${requiresWork && !work ? `<span class="muted">請先選擇目前 work item。</span>` : ""}</div></form></section>`;
}

function publicCommandOptions(selected: PublicCommandName): string {
  const options: Array<[PublicCommandName, string]> = [
    ["new", "new — 建立 work item"],
    ["feature", "feature — 新功能"],
    ["refactor", "refactor — 重構"],
    ["bug", "bug — 問題症狀"],
    ["next", "next — 下一步"],
    ["status", "status — 目前狀態"],
    ["revise", "revise — 修改決策"],
    ["approve", "approve — 人工核准"]
  ];
  return options.map(([value, label]) => `<option value="${value}" ${value === selected ? "selected" : ""}>${escapeHtml(label)}</option>`).join("");
}

function renderCommandFields(command: PublicCommandName, work: any): string {
  switch (command) {
    case "new":
      return `<label for="command-goal">Goal</label><input id="command-goal" name="goal" type="text" placeholder="例如：建立 CSV 匯出能力" autocomplete="off" />`;
    case "feature":
      return `<label for="command-request">Request</label><textarea id="command-request" name="request" rows="3" placeholder="描述要新增的功能" spellcheck="true"></textarea>`;
    case "refactor":
      return `<label for="command-request">Request</label><textarea id="command-request" name="request" rows="3" placeholder="描述要整理或重構的部分" spellcheck="true"></textarea>`;
    case "bug":
      return `<label for="command-symptom">Symptom</label><textarea id="command-symptom" name="symptom" rows="3" placeholder="描述實際觀察到的問題" spellcheck="true"></textarea>`;
    case "next":
    case "status":
      return work
        ? `<label class="checkbox-field" for="include-work"><input id="include-work" name="include-work" type="checkbox" checked />帶入目前 work：<code>${escapeHtml(work.id)}</code><small>取消勾選即可產生不帶 work ID 的 ${command}。</small></label>`
        : `<p class="field-hint">目前沒有 work item；${command} 會產生不帶 work ID 的公開命令。</p>`;
    case "revise":
      return work
        ? `<div class="selected-work"><span>目前 work</span><code>${escapeHtml(work.id)}</code></div><label for="command-change">Decision change</label><textarea id="command-change" name="change" rows="3" placeholder="說明需要修改的決策或方向" spellcheck="true"></textarea>`
        : `<p class="field-hint">revise 需要先選擇目前 work item。</p>`;
    case "approve":
      return work
        ? `<div class="selected-work"><span>目前 work</span><code>${escapeHtml(work.id)}</code><small>目前 gate 僅在 Dashboard 唯讀呈現，公開 approve 命令不帶 gate 參數。</small></div>`
        : `<p class="field-hint">approve 需要先選擇目前 work item。</p>`;
  }
}

function formIntent(form: HTMLFormElement, work: any): PublicCommandIntent | null {
  const command = formValue(form, "command");
  if (!isPublicCommandName(command)) return null;
  let candidate: unknown;
  switch (command) {
    case "new":
      candidate = { type: command, goal: formValue(form, "goal") };
      break;
    case "feature":
    case "refactor":
      candidate = { type: command, request: formValue(form, "request") };
      break;
    case "bug":
      candidate = { type: command, symptom: formValue(form, "symptom") };
      break;
    case "next":
    case "status":
      candidate = form.elements.namedItem("include-work") && !((form.elements.namedItem("include-work") as HTMLInputElement).checked)
        ? { type: command }
        : { type: command, ...(work ? { workId: work.id } : {}) };
      break;
    case "revise":
      candidate = work ? { type: command, workId: work.id, change: formValue(form, "change") } : null;
      break;
    case "approve":
      candidate = work ? { type: command, workId: work.id } : null;
      break;
  }
  return parsePublicCommandIntent(candidate);
}

function formValue(form: HTMLFormElement, name: string): string {
  const value = new FormData(form).get(name);
  return typeof value === "string" ? value : "";
}

function selectedWork(): any | null {
  if (!snapshot || !selectedWorkId) return null;
  return snapshot.workItems?.find((item: any) => item.id === selectedWorkId) ?? null;
}

function renderWork(work: any): string {
  if (!snapshot) return "";
  const current = snapshot;
  const taskDone = (work.tasks ?? []).filter((task: any) => task.status === "completed").length;
  const evidencePassed = (work.evidence ?? []).filter((item: any) => item.status === "passed" && !item.stale).length;
  return `<section class="section-card">
    <div class="section-heading"><div><p class="eyebrow">WORK ITEM</p><h2>${escapeHtml(work.title)}</h2><p class="muted mono">${escapeHtml(work.id)}</p></div><div class="pill-row"><span class="pill">${escapeHtml(work.kind)}</span><span class="pill ${work.risk === "high" ? "danger" : "info"}">${escapeHtml(work.risk)} risk</span><span class="pill">${escapeHtml(work.status)}</span></div></div>
    <div class="gate-grid">${gateCard(work, "scope", "G1 Scope")} ${gateCard(work, "build", "G2 Build")} ${gateCard(work, "acceptance", "G3 Acceptance")}</div>
    <div class="metric-grid"><div class="metric"><span>Phase</span><strong>${escapeHtml(work.phase)}</strong></div><div class="metric"><span>Tasks</span><strong>${taskDone}/${(work.tasks ?? []).length}</strong></div><div class="metric"><span>Evidence</span><strong>${evidencePassed}/${(work.evidence ?? []).length}</strong></div><div class="metric"><span>Knowledge</span><strong>${escapeHtml(work.knowledge?.health ?? "unknown")}</strong></div></div>
    ${work.blocker ? `<div class="notice danger"><span class="status-icon">!</span><div><strong>Blocker · ${escapeHtml(work.blocker.task ?? "task")}</strong><p>${escapeHtml(work.blocker.reason ?? "")}</p></div></div>` : ""}
  </section>
  ${renderNextAction(work)}
  ${renderArtifacts(work)}
  ${renderRequirementsDesign(work)}
  ${renderKnowledge(work)}
  ${renderTasksEvidence(work)}
  ${renderVerification(work, current)}
  ${renderAcceptance(work)}
  ${renderAudit(work)}`;
}

function gateCard(work: any, gate: string, label: string): string {
  const value = work.gates?.[gate] ?? { status: "pending" };
  const status = value.status ?? "pending";
  const approvalNote = status !== "approved" && work.phase !== "closed" ? `<small class="approval-note">人工 gate · 僅唯讀呈現</small>` : "";
  return `<article class="gate-card ${escapeAttr(status)}"><div class="gate-title"><span class="status-icon">${icon(status)}</span><span>${label}</span></div><strong>${escapeHtml(status)}</strong><p class="muted">${value.approvedAt ? escapeHtml(value.approvedAt) : "等待目前 phase 的 engine validation"}</p>${approvalNote}</article>`;
}

function renderNextAction(work: any): string {
  const next = nextSafeAction(work);
  return `<section class="next-action"><div><p class="eyebrow">NEXT SAFE ACTION</p><h2>${escapeHtml(next.title)}</h2><p class="muted">${escapeHtml(next.detail)}</p></div><span class="pill info">唯讀提示</span></section>`;
}

function nextSafeAction(work: any): { title: string; detail: string } {
  if (work.status === "closed" || work.phase === "closed") {
    return { title: "Work item closed", detail: "這個 work item 僅供唯讀 audit；不提供版本控制或重新開啟操作。" };
  }
  if (work.blocker) {
    return { title: "Review the current blocker", detail: `${work.blocker.task ?? "Task"}: ${work.blocker.reason ?? "需要在 Codex Chat 處理 blocker。"}` };
  }
  if (work.gates?.scope?.status !== "approved") {
    return { title: "Review requirements and request G1", detail: "確認 scope、risk 與 Wiki-first context，再透過公開對話命令與 Codex Chat 處理。" };
  }
  if (work.gates?.build?.status !== "approved") {
    return { title: "Review design and request G2", detail: "確認 DEC、plan、task dependency 與 high-risk analysis，再透過 Codex Chat 處理。" };
  }
  if (work.phase === "implementation") {
    const pending = (work.tasks ?? []).find((task: any) => task.status === "pending");
    return pending
      ? { title: `Continue ${pending.id}`, detail: "依 plan dependency 執行下一個 task，完成後以 evidence 回填。" }
      : { title: "Continue implementation", detail: "所有已投影 task 已啟動或完成；請在 Codex Chat 查看目前 work 的下一步。" };
  }
  if (work.phase === "verification" || work.phase === "acceptance_review") {
    return { title: "Review verification readiness", detail: "確認 current source fingerprint、evidence、Wiki 與 baseline 後，再進行人工 acceptance。" };
  }
  return { title: "Review current work status", detail: "Extension 只呈現 filesystem snapshot；請在 Codex Chat 使用公開命令後 Refresh。" };
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

function renderKnowledge(work: any): string {
  const knowledge = work.knowledge ?? snapshot?.knowledge;
  const pages = knowledge?.pages ?? [];
  const categoryCounts = pages.reduce((counts: Record<string, number>, page: any) => { counts[page.type] = (counts[page.type] ?? 0) + 1; return counts; }, {});
  const categories = Object.entries(categoryCounts).map(([type, count]) => `<span class="pill">${escapeHtml(type)} ${escapeHtml(count)}</span>`).join("");
  return `<section class="section-card"><div class="section-heading"><div><p class="eyebrow">WIKI-FIRST KNOWLEDGE</p><h2>Knowledge health</h2></div><span class="pill ${knowledge?.health === "healthy" ? "success" : "warning"}">${escapeHtml(knowledge?.health ?? "unknown")}</span></div><div class="notice info"><span class="status-icon">i</span><div><strong>G1 fixed read order</strong><p><code>wiki/index.md</code> first, followed by at most five related pages. Raw sources are only for recorded gaps.</p></div></div><div class="pill-row">${categories || `<span class="muted">No Wiki categories detected.</span>`}</div><div class="metric-grid"><div class="metric"><span>Pages</span><strong>${pages.length}</strong></div><div class="metric"><span>Placeholder</span><strong>${(knowledge?.placeholderPages ?? []).length}</strong></div><div class="metric"><span>Stale</span><strong>${(knowledge?.stalePages ?? []).length}</strong></div><div class="metric"><span>Pending refresh</span><strong>${(knowledge?.pendingRefresh ?? []).length}</strong></div></div><div class="page-list">${pages.slice(0, 12).map((page: any) => `<button class="page-row" data-action="open" data-path="${escapeAttr(page.path)}"><span>${icon(page.status)}</span><span><strong>${escapeHtml(page.title)}</strong><small>${escapeHtml(page.path)} · ${escapeHtml(page.status)}${page.parseErrors?.length ? " · parse warning" : ""}</small></span></button>`).join("")}</div></section>`;
}

function renderTasksEvidence(work: any): string {
  return `<section class="section-card"><div class="section-heading"><div><p class="eyebrow">IMPLEMENTATION</p><h2>Task board</h2></div><span class="muted">pending · in progress · completed · blocked</span></div><div class="task-list">${(work.tasks ?? []).map((task: any) => `<div class="task-row"><span class="status-icon">${icon(task.status)}</span><span><strong>${escapeHtml(task.id)}</strong><small>${escapeHtml(task.status)}${task.note ? ` · ${escapeHtml(task.note)}` : ""}${task.evidence?.length ? ` · evidence ${escapeHtml(task.evidence.join(", "))}` : ""}</small></span></div>`).join("") || `<p class="muted">G2 approval will create task tracking data.</p>`}</div></section>`;
}

function renderVerification(work: any, current: WorkspaceSnapshot): string {
  const commands = current.commands ?? [];
  const profiles = Object.entries(current.verificationProfiles ?? {}).map(([name, ids]) => `<span class="pill info">${escapeHtml(name)}: ${escapeHtml((ids as string[]).join(", ") || "none")}</span>`).join("");
  const evidence = work.evidence ?? [];
  return `<section class="section-card"><div class="section-heading"><div><p class="eyebrow">VERIFICATION</p><h2>Commands and evidence</h2><p class="muted">只顯示 command metadata、exit code 與 raw-log path；不把 raw log 內容放入 Webview 或 clipboard。</p></div><div class="pill-row">${profiles || `<span class="pill warning">profiles unavailable</span>`}</div></div><div class="command-list">${commands.map((command: any) => `<div class="command-row"><span class="status-icon">⌘</span><span><strong>${escapeHtml(command.id)}</strong><small>${escapeHtml(command.argv.join(" "))} · cwd ${escapeHtml(command.cwd)} · timeout ${escapeHtml(command.timeoutSeconds)}s</small></span></div>`).join("") || `<p class="muted">No verification command configured.</p>`}</div><div class="evidence-list">${evidence.map((item: any) => `<article class="evidence-card"><div class="section-heading"><strong>${escapeHtml(item.id)} · ${escapeHtml(item.kind)}</strong><span class="pill ${item.status === "passed" && !item.stale ? "success" : item.stale ? "warning" : "danger"}">${escapeHtml(item.status)}${item.stale ? " · stale" : ""}</span></div><p>${escapeHtml(item.summary)}</p><small>covers ${escapeHtml(item.covers.join(", ") || "—")} · tasks ${escapeHtml(item.tasks.join(", ") || "—")} · command ${escapeHtml(item.commandId ?? "—")} · exit ${escapeHtml(item.exitCode ?? "—")}</small>${item.rawLog ? `<code class="raw-log-path">raw log: ${escapeHtml(item.rawLog)}</code>` : ""}</article>`).join("") || `<p class="muted">No evidence recorded.</p>`}</div></section>`;
}

function renderAcceptance(work: any): string {
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
    return `<section class="empty-card"><span class="empty-icon">⌁</span><h2>Select a work item</h2><p class="muted">目前有多個 work items；請先在上方選擇 work ID。next/status 可以不帶 work，revise/approve 必須先選擇。</p></section>`;
  }
  return `<section class="empty-card"><span class="empty-icon">＋</span><h2>No work item selected</h2><p class="muted">沒有既有 work item 時，仍可使用 new、feature、refactor、bug、next 與 status 公開命令；revise/approve 需要目前 work。</p></section>`;
}

function renderActionPreview(bundle: any): void {
  const panel = document.querySelector<HTMLElement>("#copy-preview");
  if (!panel) return;
  panel.classList.remove("hidden");
  panel.innerHTML = `<div class="preview-heading"><div><p class="eyebrow">PUBLIC COMMAND PREVIEW</p><h2>Review before copy</h2></div><span class="pill ${bundle.mutation ? "warning" : "info"}">${bundle.mutation ? "mutation · manual send" : "read-only"}</span></div><p class="muted">${escapeHtml(bundle.command ?? pendingIntent?.type ?? "public command")}${bundle.workId ? ` · ${escapeHtml(bundle.workId)}` : ""}</p><div class="notice warning"><span class="status-icon">!</span><div><strong>此 Extension 不會執行</strong><p>確認後只會複製公開命令到 clipboard；仍需由使用者在 Codex Chat 審閱並送出。</p></div></div><h3>Codex Chat command</h3><pre>${escapeHtml(bundle.chatText ?? "")}</pre>${(bundle.warnings ?? []).length ? `<div class="notice warning"><strong>Review warnings</strong><ul>${bundle.warnings.map((warning: string) => `<li>${escapeHtml(warning)}</li>`).join("")}</ul></div>` : ""}<div class="action-row"><button class="primary" data-action="confirm-copy">Confirm and copy</button><button class="secondary" data-action="cancel-preview">Cancel</button></div>`;
  setStatus("請審閱公開命令，再確認複製到 Codex Chat。", false);
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
  panel.innerHTML = `<div class="preview-heading"><div><p class="eyebrow">PUBLIC COMMAND PREVIEW</p><h2>已複製到 clipboard</h2></div><span class="pill ${bundle.mutation ? "warning" : "info"}">${bundle.mutation ? "mutation · manual send" : "read-only"}</span></div><p class="muted">${escapeHtml(bundle.command ?? "public command")}${bundle.workId ? ` · ${escapeHtml(bundle.workId)}` : ""} · Extension 不會自行執行。</p><h3>Codex Chat command</h3><pre>${escapeHtml(bundle.chatText ?? "")}</pre>${(bundle.warnings ?? []).length ? `<div class="notice warning"><strong>Review before sending</strong><ul>${bundle.warnings.map((warning: string) => `<li>${escapeHtml(warning)}</li>`).join("")}</ul></div>` : ""}`;
  setStatus("公開 prompt 已複製；請在 Codex Chat 審閱並送出。", false);
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

function clearPendingPreview(): void {
  pendingIntent = null;
  document.querySelector<HTMLElement>("#copy-preview")?.classList.add("hidden");
}

function parsePublicCommandName(value: string): value is PublicCommandName {
  return ["new", "feature", "refactor", "bug", "next", "status", "revise", "approve"].includes(value);
}

function isPublicCommandName(value: unknown): value is PublicCommandName {
  return typeof value === "string" && parsePublicCommandName(value);
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
