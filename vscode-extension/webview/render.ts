import type { UiProjection } from "../src/ui/projection";

export const TABS = ["overview", "plan", "approvals", "quality", "diagnostics"] as const;

export function renderControlCenter(state: UiProjection, activeTab: string = "overview"): string {
  const run = record(state.run);
  const preflight = record(state.preflight);
  const codex = record(preflight.codex);
  const appServerPreflight = record(preflight.app_server);
  const plan = record(run.plan);
  const decision = record(run.pending_decision);
  const verification = record(run.verification);
  const gates = record(run.gates);
  const statusLabel = state.stale ? "Projection / stale" : "Authoritative / current";
  return `
    <header class="hero">
      <div><p class="eyebrow">DevWeave V2</p><h1>Control Center</h1></div>
      <span class="authority ${state.stale ? "stale" : "current"}" aria-label="State authority">${escapeHtml(statusLabel)}</span>
    </header>
    ${renderTabs(activeTab)}
    <main>
      <section id="panel-overview" role="tabpanel" aria-labelledby="tab-overview" ${hidden(activeTab !== "overview")}>
        <h2>Connection &amp; run</h2>
        <dl class="metrics">
          ${metric("Connection", state.appServer.connection)}
          ${metric("Preflight", string(preflight.status, "Not run"))}
          ${metric("Codex", string(codex.version, "Unavailable"))}
          ${metric("Schema", string(appServerPreflight.schema_sha256, "Unavailable"))}
          ${metric("Run", string(run.run_id, "Not started"))}
          ${metric("Run status", string(run.status, state.status))}
          ${metric("Thread", state.threadId || "Not connected")}
          ${metric("Turn", state.turnId || state.appServer.turnStatus)}
          ${metric("Usage", renderUsage(state.appServer.usage))}
        </dl>
        ${renderStartForm(Boolean(state.run))}
        <div class="toolbar" aria-label="Run controls">
          <button data-action="resume">Resume</button>
          <button data-action="refresh">Refresh authority</button>
          <button data-action="interrupt">Interrupt</button>
          <button data-action="review">Detached review</button>
          <button class="danger" data-action="cancel">Cancel run</button>
        </div>
        <label for="turn-input">Turn / steering instruction</label>
        <textarea id="turn-input" data-focus-key="turn-input" rows="4"></textarea>
        <div class="toolbar"><button data-action="turn">Start turn</button><button data-action="steer">Steer</button></div>
      </section>
      <section id="panel-plan" role="tabpanel" aria-labelledby="tab-plan" ${hidden(activeTab !== "plan")}>
        <h2>Plan &amp; diff</h2>
        <p class="source-label">Saved plan source: authoritative RunPlan. Live steps and diff are app-server projections until completed items arrive.</p>
        <h3>Goal</h3><p>${escapeHtml(string(plan.goal, "No plan saved"))}</p>
        <h3>Plan steps</h3>${renderList(state.appServer.plan.map((item) => display(item)))}
        <h3>Current diff</h3><pre aria-label="Current projected diff">${escapeHtml(state.appServer.diff || "No projected diff")}</pre>
        <h3>Gates</h3>${renderGates(gates)}
      </section>
      <section id="panel-approvals" role="tabpanel" aria-labelledby="tab-approvals" ${hidden(activeTab !== "approvals")}>
        <h2>Tools, approvals &amp; decisions</h2>
        ${renderApprovals(state.pendingApprovals)}
        ${renderDecision(decision)}
        <h3>Completed items</h3>${renderItems(state.appServer.items)}
      </section>
      <section id="panel-quality" role="tabpanel" aria-labelledby="tab-quality" ${hidden(activeTab !== "quality")}>
        <h2>Verification &amp; review</h2>
        <dl class="metrics">
          ${metric("Verification", string(verification.status, string(run.verification_status, "pending")))}
          ${metric("Review", string(record(state.review).status, string(record(run.review).status, "pending")))}
          ${metric("Review round", string(record(state.review).round, "0"))}
        </dl>
        ${renderFindings(record(state.review).findings)}
      </section>
      <section id="panel-diagnostics" role="tabpanel" aria-labelledby="tab-diagnostics" ${hidden(activeTab !== "diagnostics")}>
        <h2>Diagnostics</h2>
        <div class="diagnostics" role="log" aria-live="polite" aria-relevant="additions text">
          ${renderList([...state.diagnostics, ...state.appServer.diagnostics.map((item) => `${item.code}: ${item.message}`)])}
        </div>
      </section>
    </main>`;
}

export function nextTabIndex(current: number, key: string, count: number = TABS.length): number {
  if (key === "Home") return 0;
  if (key === "End") return count - 1;
  if (key === "ArrowRight" || key === "ArrowDown") return (current + 1) % count;
  if (key === "ArrowLeft" || key === "ArrowUp") return (current - 1 + count) % count;
  return current;
}

function renderTabs(active: string): string {
  return `<nav class="tabs" role="tablist" aria-label="Control Center sections">${TABS.map((tab) => {
    const selected = tab === active;
    return `<button id="tab-${tab}" role="tab" aria-controls="panel-${tab}" aria-selected="${selected}" tabindex="${selected ? 0 : -1}" data-tab="${tab}">${escapeHtml(label(tab))}</button>`;
  }).join("")}</nav>`;
}

function renderStartForm(hasRun: boolean): string {
  if (hasRun) return "";
  return `<form id="start-form" aria-label="Start governed run">
    <label for="goal">Goal</label><textarea id="goal" rows="3" required data-focus-key="goal"></textarea>
    <label for="scope">Scope (repository-relative pattern)</label><input id="scope" value="src/**" required />
    <label for="risk">Risk</label><select id="risk"><option>low</option><option selected>standard</option><option>high</option></select>
    <button type="submit">Start governed run</button>
  </form>`;
}

function renderApprovals(value: UiProjection["pendingApprovals"]): string {
  if (!value.length) return "<p>No pending tool approval.</p>";
  return value.map((item) => `<article class="card" data-focus-key="approval-${escapeAttribute(String(item.request.id))}">
    <h3>${escapeHtml(item.request.method)}</h3><p>${escapeHtml(item.assessment.reason)}</p>
    <p>Scope: ${escapeHtml(item.assessment.paths.join(", ") || "command")}</p>
    <div class="toolbar">
      <button data-action="approval" data-request-id="${escapeAttribute(String(item.request.id))}" data-decision="accept" ${item.assessment.eligible ? "" : "disabled"}>Accept</button>
      <button data-action="approval" data-request-id="${escapeAttribute(String(item.request.id))}" data-decision="decline">Decline</button>
      <button data-action="approval" data-request-id="${escapeAttribute(String(item.request.id))}" data-decision="cancel">Cancel</button>
    </div></article>`).join("");
}

function renderDecision(value: Record<string, unknown>): string {
  if (!value.decision_id) return "<p>No pending product decision.</p>";
  const options = Array.isArray(value.options) ? value.options.map(record) : [];
  const other = value.allow_other === true
    ? `<label for="decision-other">Other answer</label><input id="decision-other" data-focus-key="decision-other" maxlength="4096"><button data-action="decision-other" data-decision-id="${escapeAttribute(String(value.decision_id))}">Submit other</button>`
    : "";
  return `<article class="card"><h3>Pending decision</h3><p>${escapeHtml(string(value.question, "Decision required"))}</p>
    <div class="toolbar">${options.map((option) => `<button data-action="decision" data-decision-id="${escapeAttribute(String(value.decision_id))}" data-option-id="${escapeAttribute(String(option.option_id))}">${escapeHtml(string(option.label, "Option"))}</button>`).join("")}${other}</div>
  </article>`;
}

function renderGates(gates: Record<string, unknown>): string {
  const entries = Object.entries(gates);
  if (!entries.length) return "<p>No required Gate.</p>";
  return entries.map(([id, raw]) => `<article class="gate"><strong>${escapeHtml(id)}</strong><span>${escapeHtml(string(record(raw).status, "pending"))}</span>
    <button data-action="gate" data-gate-id="${escapeAttribute(id)}" data-approve="true">Approve</button>
    <button data-action="gate" data-gate-id="${escapeAttribute(id)}" data-approve="false">Reject</button></article>`).join("");
}

function renderItems(items: UiProjection["appServer"]["items"]): string {
  const displayItems = Object.values(items).filter((item) => item.type !== "reasoning");
  if (!displayItems.length) return "<p>No completed items.</p>";
  return displayItems.map((item) => `<article class="card"><h3>${escapeHtml(item.type)}</h3><span class="source-label">${item.authoritative ? "Authoritative item/completed" : "Projection / streaming"}</span><pre>${escapeHtml(item.content ?? item.status)}</pre></article>`).join("");
}

function renderFindings(value: unknown): string {
  if (!Array.isArray(value) || !value.length) return "<p>No review findings.</p>";
  return renderList(value.map((item) => `${string(record(item).severity, "advisory")}: ${string(record(item).summary, "finding")}`));
}

function renderUsage(value: UiProjection["appServer"]["usage"]): string {
  return value ? `${value.totalTokens} total (${value.inputTokens} in / ${value.outputTokens} out)` : "Unavailable — not estimated";
}

function renderList(values: string[]): string {
  return values.length ? `<ul>${values.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : "<p>None.</p>";
}

function metric(name: string, value: unknown): string {
  return `<div><dt>${escapeHtml(name)}</dt><dd>${escapeHtml(String(value))}</dd></div>`;
}

function hidden(value: boolean): string { return value ? "hidden" : ""; }

function display(value: unknown): string {
  if (typeof value === "string") return value;
  const item = record(value);
  return string(item.step ?? item.description ?? item.status, "Plan step");
}

function label(tab: string): string {
  return ({ overview: "Overview", plan: "Plan & diff", approvals: "Approvals", quality: "Quality", diagnostics: "Diagnostics" } as Record<string, string>)[tab] ?? tab;
}

function string(value: unknown, fallback: string): string {
  return typeof value === "string" || typeof value === "number" ? String(value) : fallback;
}

function record(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]!);
}

function escapeAttribute(value: string): string { return escapeHtml(value).replace(/`/g, "&#96;"); }
