import { parsePublicCommandIntent } from "../src/protocol";
import type { HostToWebviewMessage, WebviewToHostMessage } from "../src/protocol";
import type {
  AuditEventPresentation,
  DashboardPreferences,
  DashboardSection,
  DiagnosticPresentation,
  DisplayMode,
  PublicCommandIntent,
  PublicCommandName,
  PromptBundle,
  ReviewReadiness,
  SnapshotGuidance,
  WorkItemProjection,
  WorkspaceSnapshot
} from "../src/model";
import type { BootstrapReport } from "../src/bootstrap";
import {
  buildReviewReadiness,
  buildSnapshotGuidance,
  commandPresentations,
  presentDiagnostic,
  presentGate,
  presentPhase,
  presentRisk,
  presentStatus,
  presentAuditEvent
} from "../src/presentation";
import { resolveWorkSelection } from "../src/work-selection";
import { RenderScheduler } from "../src/render-scheduler";
import { WikiSearchModel } from "../src/wiki-search";
import { mountWikiResults } from "../src/wiki-results-mount";
import { dashboardPanelState, dashboardSectionDefinitions, moveDashboardSection } from "../src/dashboard-sections";
import { helpContent } from "./help-content";

declare function acquireVsCodeApi<T>(): { postMessage(message: T): void };

type AppApi = { postMessage(message: WebviewToHostMessage): void };
const api: AppApi = acquireVsCodeApi<WebviewToHostMessage>();

let snapshot: WorkspaceSnapshot | null = null;
let snapshotRevision = 0;
let preferences: DashboardPreferences = { displayMode: "concise" };
let selectedSection: DashboardSection = "overview";
let selectedWorkId: string | null = null;
let selectedCommand: PublicCommandName = "feature";
let pendingIntent: PublicCommandIntent | null = null;
let previewRevision: number | null = null;
let previewBundle: PromptBundle | null = null;
let copiedBundle: PromptBundle | null = null;
let bootstrapReport: BootstrapReport | null = null;
let showAllAudit = false;
let busyAction: string | null = null;
let statusMessage = "正在等待 workspace 檔案快照。";
let statusError = false;
let errorDetail: string | null = null;
let focusRestoreKey: string | null = null;

const wikiSearch = new WikiSearchModel();
const sectionDefinitions = dashboardSectionDefinitions;
const frameScheduler = (callback: () => void): void => {
  if (typeof window.requestAnimationFrame === "function") {
    window.requestAnimationFrame(() => callback());
  } else {
    window.setTimeout(callback, 0);
  }
};
const renderScheduler = new RenderScheduler(() => render(), frameScheduler);
const knowledgeRenderScheduler = new RenderScheduler(() => {
  mountWikiResults(document, renderKnowledgeResults());
}, frameScheduler);

window.addEventListener("message", (event) => {
  const message = event.data;
  if (!isHostMessage(message)) return;
  if (message.type === "snapshot") {
    if (message.revision !== snapshotRevision) {
      clearPromptResult();
    }
    snapshotRevision = message.revision;
    snapshot = message.snapshot;
    preferences = message.preferences ?? preferences;
    selectedWorkId = resolveWorkSelection(snapshot, message.snapshot.selectedWorkId ?? selectedWorkId);
    busyAction = null;
    statusMessage = "檔案快照已更新；它不是 engine 的權威狀態。";
    statusError = false;
    errorDetail = null;
    render();
  }
  if (message.type === "bootstrapResult") {
    clearPromptResult();
    snapshotRevision = message.revision;
    snapshot = message.snapshot;
    selectedWorkId = resolveWorkSelection(snapshot, message.snapshot.selectedWorkId ?? selectedWorkId);
    bootstrapReport = message.report;
    busyAction = null;
    statusMessage = message.report.ok
      ? "初始化完成；請依下方設定提示確認 hook、verification 與第一個 work。"
      : "初始化未完成；請先處理衝突或錯誤，再重新整理。";
    statusError = !message.report.ok;
    errorDetail = null;
    render();
    document.querySelector<HTMLElement>("#result-panel")?.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" });
  }
  if (message.type === "copyResult") {
    busyAction = null;
    if (message.ok) {
      copiedBundle = message.bundle;
      pendingIntent = null;
      previewRevision = null;
      previewBundle = null;
      statusMessage = message.bundle.planModeGuidance?.required
        ? "prompt 已複製；請先切換 Plan Mode，再貼到 Codex Chat 並送出，完成後回來 Refresh。"
        : "prompt 已複製；請到 Codex Chat 貼上並送出，完成後回來 Refresh。";
      statusError = false;
      errorDetail = null;
    } else {
      statusMessage = message.message;
      statusError = true;
      errorDetail = null;
    }
    render();
  }
  if (message.type === "actionPreview") {
    busyAction = null;
    if (message.revision !== snapshotRevision) {
      clearPromptResult();
      statusMessage = "這個預覽已過期；請重新整理後再預覽。";
      statusError = true;
      render();
      return;
    }
    pendingIntent = message.intent;
    previewRevision = message.revision;
    previewBundle = message.bundle;
    copiedBundle = null;
    statusMessage = "請先閱讀這個操作會做什麼、不會做什麼，再決定是否複製。";
    statusError = false;
    errorDetail = null;
    render();
    document.querySelector<HTMLElement>("#result-panel")?.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" });
  }
  if (message.type === "protocolError") {
    busyAction = null;
    statusMessage = `訊息格式無法接受：${message.message}`;
    statusError = true;
    errorDetail = null;
    render();
  }
  if (message.type === "error") {
    busyAction = null;
    statusMessage = message.message;
    statusError = true;
    errorDetail = message.detail ?? null;
    render();
  }
});

document.addEventListener("click", (event) => {
  const target = event.target as HTMLElement;
  const button = target.closest<HTMLElement>("[data-action]");
  if (!button) return;
  const action = button.dataset.action;

  if (action === "refresh") {
    beginHostAction("refresh", { type: "refresh" }, "正在重新整理檔案快照…");
  } else if (action === "initialize") {
    beginHostAction("initialize", { type: "initialize" }, "等待你確認 bootstrap 寫入…");
  } else if (action === "wiki-bootstrap") {
    const intent: PublicCommandIntent = { type: "wikiBootstrap" };
    pendingIntent = intent;
    previewBundle = null;
    copiedBundle = null;
    bootstrapReport = null;
    beginHostAction("preview", { type: "previewAction", intent }, "正在產生 Wiki bootstrap prompt…");
  } else if (action === "confirm-copy") {
    if (pendingIntent && previewBundle && previewRevision === snapshotRevision) {
      beginHostAction("copy", { type: "copyAction", intent: pendingIntent }, "正在複製 prompt…");
    }
  } else if (action === "cancel-preview") {
    clearPromptResult();
    statusMessage = "已取消這次 prompt preview。";
    statusError = false;
    renderScheduler.request();
  } else if (action === "open") {
    const path = button.dataset.path;
    if (path && !busyAction) api.postMessage({ type: "openFile", path });
  } else if (action === "section") {
    const section = button.dataset.section;
    if (isDashboardSection(section)) {
      selectSection(section);
    }
  } else if (action === "select-command") {
    const command = button.dataset.command;
    if (isPublicCommandName(command)) {
      selectedCommand = command;
      selectSection("overview");
      clearPromptResult();
      focusRestoreKey = "command-select";
      renderScheduler.request();
      focusByKey("command-select");
    }
  } else if (action === "start-work") {
    selectedCommand = "new";
    selectSection("overview");
    clearPromptResult();
    focusRestoreKey = "command-select";
    renderScheduler.request();
    focusByKey("command-select");
  } else if (action === "focus-work-select") {
    selectSection("work");
    focusRestoreKey = "work-select";
    renderScheduler.request();
    focusByKey("work-select");
  } else if (action === "set-display-mode") {
    const mode = button.dataset.mode;
    if (!busyAction && isDisplayMode(mode) && mode !== preferences.displayMode) {
      preferences = { displayMode: mode };
      beginHostAction("display-mode", { type: "setDisplayMode", mode }, "正在儲存顯示偏好…");
    }
  } else if (action === "show-all-wiki") {
    wikiSearch.setShowAll(true);
    knowledgeRenderScheduler.request();
  } else if (action === "show-all-audit") {
    showAllAudit = true;
    renderScheduler.request();
  }
});

document.addEventListener("change", (event) => {
  const target = event.target as HTMLInputElement | HTMLSelectElement;
  if (target.id === "work-select") {
    clearPromptResult();
    selectedWorkId = target.value || null;
    if (!busyAction) api.postMessage({ type: "selectWork", workId: selectedWorkId });
    renderScheduler.request();
  } else if (target.id === "command-select") {
    if (isPublicCommandName(target.value)) {
      clearPromptResult();
      selectedCommand = target.value;
      renderScheduler.request();
    }
  } else if (target.id === "wiki-type") {
    wikiSearch.setType(target.value || "all");
    knowledgeRenderScheduler.request();
  }
});

document.addEventListener("input", (event) => {
  const target = event.target as HTMLInputElement;
  if (target.id === "wiki-query") {
    wikiSearch.updateDraft(target.value);
  }
});

document.addEventListener("submit", (event) => {
  const target = event.target as HTMLFormElement;
  if (target.id !== "public-command-form") return;
  event.preventDefault();
  if (busyAction) return;
  const work = selectedWork();
  const intent = formIntent(target, work);
  if (!intent) {
    statusMessage = selectedCommand === "revise" || selectedCommand === "approve"
      ? "請先選擇一個進行中的 work，再預覽這個審查操作。"
      : "請補齊必要欄位。";
    statusError = true;
    renderScheduler.request();
    return;
  }
  pendingIntent = intent;
  previewBundle = null;
  copiedBundle = null;
  bootstrapReport = null;
  beginHostAction("preview", { type: "previewAction", intent }, "正在產生 prompt preview…");
});

document.addEventListener("keydown", (event) => {
  const target = event.target as HTMLElement;
  if (target.id === "wiki-query" && event.key === "Enter") {
    event.preventDefault();
    wikiSearch.submit();
    knowledgeRenderScheduler.request();
    return;
  }
  const tab = target.closest<HTMLButtonElement>("[role=\"tab\"]");
  if (tab && ["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp", "Home", "End"].includes(event.key)) {
    event.preventDefault();
    const currentSection = tab.dataset.section;
    if (isDashboardSection(currentSection)) {
      const nextSection = moveDashboardSection(currentSection, event.key);
      if (nextSection) selectSection(nextSection);
    }
    return;
  }
  if (event.key === "Escape" && previewBundle) {
    clearPromptResult();
    statusMessage = "已取消這次 prompt preview。";
    statusError = false;
    renderScheduler.request();
  }
});

function beginHostAction(key: string, message: WebviewToHostMessage, status: string): void {
  if (busyAction) return;
  busyAction = key;
  statusMessage = status;
  statusError = false;
  render();
  api.postMessage(message);
}

function render(): void {
  const app = document.querySelector<HTMLElement>("#app");
  if (!app || !snapshot) return;
  const focusKey = focusRestoreKey ?? document.activeElement?.getAttribute("data-focus-key") ?? document.activeElement?.id ?? null;
  focusRestoreKey = null;
  app.innerHTML = `
    ${renderHeader()}
    ${renderSectionNavigation()}
    <div id="section-content">${sectionDefinitions.map(([section]) => renderSectionPanel(section)).join("")}</div>
    ${renderStatus()}
    ${renderResultPanel()}
  `;
  restoreFocus(focusKey);
}

function renderLoading(): void {
  const app = document.querySelector<HTMLElement>("#app");
  if (app) {
    app.innerHTML = `<section class="loading-card" role="status" aria-live="polite"><span class="loading-dot" aria-hidden="true">•</span><div><strong>正在讀取 workspace</strong><p>只讀取檔案快照，不會執行 engine 或命令。</p></div></section>`;
  }
}

function renderHeader(): string {
  if (!snapshot) return "";
  const state = snapshot.projectExists
    ? snapshot.managed === true ? "已啟用 managed" : "需要確認管理狀態"
    : "尚未初始化";
  const stateClass = snapshot.projectExists && snapshot.managed === true ? "success" : "warning";
  return `<header class="topbar">
    <div class="title-block"><p class="eyebrow">DEVWEAVE CONTROL CENTER</p><h1>${escapeHtml(snapshot.rootName ?? "Repository workspace")}</h1><p class="muted">先看總覽，再按需要展開工作、知識或驗證資訊。</p></div>
    <div class="toolbar"><span class="pill ${stateClass}">${escapeHtml(state)}</span><button class="secondary" data-action="set-display-mode" data-mode="${preferences.displayMode === "concise" ? "advanced" : "concise"}" aria-label="切換顯示模式">${preferences.displayMode === "concise" ? "顯示進階資訊" : "回到簡潔模式"}</button><button class="secondary" data-action="refresh" ${busyAction ? "disabled" : ""} aria-label="重新整理檔案快照">↻ 重新整理</button></div>
  </header>`;
}

function renderSectionNavigation(): string {
  return `<nav class="section-tabs" aria-label="Control Center 區域" role="tablist" aria-orientation="horizontal">${sectionDefinitions.map(([id, label, description]) => `<button id="section-tab-${id}" class="section-tab ${selectedSection === id ? "active" : ""}" data-action="section" data-section="${id}" data-focus-key="section-${id}" role="tab" aria-selected="${selectedSection === id}" aria-controls="tabpanel-${id}" tabindex="${selectedSection === id ? 0 : -1}" title="${escapeAttr(description)}">${label}</button>`).join("")}</nav>`;
}

function renderSectionPanel(section: DashboardSection): string {
  const panel = dashboardPanelState(section, selectedSection);
  return `<section id="${panel.id}" role="tabpanel" aria-labelledby="${panel.labelledBy}" tabindex="${panel.tabIndex}"${panel.hidden ? " hidden aria-hidden=\"true\"" : ""}>${renderSection(section)}</section>`;
}

function renderSection(section: DashboardSection = selectedSection): string {
  if (!snapshot) return "";
  switch (section) {
    case "overview": return renderOverview();
    case "work": return renderWorkSection();
    case "knowledge": return renderKnowledgeSection();
    case "verification": return renderVerificationSection();
    case "help": return renderHelpSection();
  }
}

function renderHelpSection(): string {
  return `<section class="section-card section-intro"><p class="eyebrow">DEVWEAVE HELP</p><h2>Extension 使用手冊</h2><p class="muted">這份說明嵌在 Extension 內，首次開啟時才載入；不會寫入 workspace，也不會連線到網路。</p></section><section class="section-card help-content">${helpContent.map((section) => `<article class="help-section"><h3>${escapeHtml(section.title)}</h3>${section.paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}${section.items?.length ? `<ul>${section.items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : ""}</article>`).join("")}</section>`;
}

function renderOverview(): string {
  const current = snapshot as WorkspaceSnapshot;
  const work = selectedWork();
  const guidance = buildSnapshotGuidance(current, work);
  const active = current.workItems.filter((item) => item.status === "active");
  const closed = current.workItems.filter((item) => item.status === "closed");
  return `${renderDiagnostics()}
    ${renderRepositoryState()}
    <section class="summary-grid" aria-label="Workspace 摘要"><article class="summary-card"><span class="summary-label">目前工作</span><strong>${escapeHtml(work?.title ?? (active.length === 0 ? "沒有進行中的工作" : `${active.length} 個進行中的工作`))}</strong><small>${work ? `${escapeHtml(presentPhase(work.phase))} · ${escapeHtml(presentStatus(work.status))}` : `${closed.length} 個歷史工作可在「工作項目」查看`}</small></article><article class="summary-card"><span class="summary-label">下一步</span><strong>${escapeHtml(guidance.title)}</strong><small>${guidance.authoritative ? "engine 權威結果" : "根據檔案快照的建議"}</small></article><article class="summary-card"><span class="summary-label">驗證準備</span><strong>${escapeHtml(verificationSummary(current))}</strong><small>${escapeHtml(verificationDetail(current))}</small></article></section>
    ${renderGuidance(guidance)}
    ${renderOnboarding(current, active)}
    ${renderPublicCommandForm(work)}
    ${renderSnapshotMetadata(current, work)}
  `;
}

function renderRepositoryState(): string {
  if (!snapshot) return "";
  const current = snapshot;
  if (!current.projectExists) {
    return `<section class="hero-card"><div><span class="pill warning">尚未初始化</span><h2>先建立 DevWeave workspace</h2><p class="muted">這是唯一會在你確認後直接寫入固定 bootstrap bundle 的操作；其他公開命令只會複製 prompt。</p></div><button class="primary" data-action="initialize" ${busyAction ? "disabled" : ""}>初始化 DevWeave</button></section>`;
  }
  if (!current.bootstrap.complete) {
    const remaining = [...new Set([...current.bootstrap.missing, ...current.bootstrap.conflicts])];
    const missing = remaining.slice(0, 4).map((path) => `<code>${escapeHtml(path)}</code>`).join("、");
    const more = remaining.length > 4 ? ` 等 ${remaining.length} 項` : "";
    return `<section class="hero-card"><div><span class="pill warning">DevWeave 尚未完整</span><h2>補齊 DevWeave control bundle</h2><p class="muted">目前 project.json 已存在，但仍缺少或衝突於 ${missing || "控制檔案"}${more}。補齊只會建立無衝突缺檔，不覆寫既有內容。</p></div><button class="primary" data-action="initialize" ${busyAction ? "disabled" : ""}>初始化／補齊 DevWeave</button></section>`;
  }
  return `<section class="hero-card"><div><span class="pill success">檔案快照可讀取</span><h2>先用總覽理解目前狀態</h2><p class="muted">Extension 不執行 engine；公開命令會先預覽，確認後複製到 Codex Chat。</p></div><button class="secondary" data-action="section" data-section="work">查看工作項目</button></section>`;
}

function renderOnboarding(current: WorkspaceSnapshot, active: WorkItemProjection[]): string {
  const steps: string[] = [];
  if (!current.hookPresent) steps.push("確認 Codex repository hook");
  if (!current.bootstrap.complete) steps.push("補齊 DevWeave control bundle");
  if (!current.commands.length || !Object.values(current.verificationProfiles).some((ids) => ids.length > 0)) steps.push("設定 verification commands");
  if (current.projectExists && active.length === 0) steps.push("建立第一個 work item");
  if (!steps.length) return "";
  return `<section class="section-card onboarding"><div class="section-heading"><div><p class="eyebrow">建議設定</p><h2>還有幾件事可以讓流程更順</h2><p class="muted">依序完成即可；Extension 不會代替你執行 Codex 或 engine。</p></div><span class="pill info">${steps.length} 個提示</span></div><ol>${steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol><div class="action-row"><button class="secondary" data-action="section" data-section="verification">查看 verification 設定</button>${active.length === 0 && current.projectExists ? `<button class="primary" data-action="start-work">開始新工作</button>` : ""}</div></section>`;
}

function renderGuidance(guidance: SnapshotGuidance): string {
  const action = guidance.command
    ? `<button class="primary" data-action="select-command" data-command="${guidance.command}">準備 ${escapeHtml(commandLabel(guidance.command))}</button>`
    : "";
  return `<section class="next-action" aria-label="下一步提示">${guidance.planModeGuidance?.required ? renderPlanModeHandoff(guidance.planModeGuidance) : ""}<div><p class="eyebrow">檔案快照提示</p><h2>${escapeHtml(guidance.title)}</h2><p class="muted">${escapeHtml(guidance.detail)}</p></div><div class="guidance-actions"><span class="pill info">非 engine 權威結果</span>${action}</div></section>`;
}

function renderSnapshotMetadata(current: WorkspaceSnapshot, work: WorkItemProjection | null): string {
  const profiles = Object.entries(current.verificationProfiles).map(([name, ids]) => `${name}: ${(ids as string[]).join(", ") || "尚未設定"}`).join(" · ") || "尚未設定";
  const bootstrapRemaining = new Set([...current.bootstrap.missing, ...current.bootstrap.conflicts]).size;
  return `<details class="details-card" ${preferences.displayMode === "advanced" ? "open" : ""}><summary>檔案來源與技術詳細資訊</summary><div class="metric-grid"><div class="metric"><span>Snapshot</span><strong>${escapeHtml(current.capturedAt)}</strong></div><div class="metric"><span>工作項目最後更新時間</span><strong>${escapeHtml(work?.updatedAt ?? "目前沒有 active work")}</strong></div><div class="metric"><span>來源</span><strong>Filesystem snapshot</strong></div><div class="metric"><span>Verification profile</span><strong>${escapeHtml(profiles)}</strong></div></div><div class="meta-line"><span class="pill ${current.hookPresent ? "success" : "warning"}">${current.hookPresent ? "hook 已找到" : "hook 待確認"}</span><span class="pill ${current.skillPresent ? "success" : "warning"}">${current.skillPresent ? "skill 已找到" : "skill 待確認"}</span><span class="pill ${current.bootstrap.complete ? "success" : "warning"}">${current.bootstrap.complete ? "bootstrap 完整" : `bootstrap 尚有 ${bootstrapRemaining} 項`}</span><code>${escapeHtml(current.projectPath)}</code></div><p class="muted">Snapshot 是 Extension 讀到的檔案投影，不代表 engine 權威狀態；送出 status/next 後請回來 Refresh。</p></details>`;
}

function renderWorkSection(): string {
  const work = selectedWork();
  const active = snapshot?.workItems.filter((item) => item.status === "active") ?? [];
  return `<section class="section-card section-intro"><p class="eyebrow">工作項目</p><h2>把進行中的工作與歷史分開看</h2><p class="muted">只有明確選取的 closed work 才會顯示；它不會被自動當成目前工作。</p></section>${renderWorkSelector()}${work ? renderWorkDetail(work) : renderWorkEmpty(active.length)}`;
}

function renderWorkSelector(): string {
  if (!snapshot) return "";
  const active = snapshot.workItems.filter((item) => item.status === "active");
  const closed = snapshot.workItems.filter((item) => item.status === "closed");
  return `<section class="section-card compact"><label for="work-select">目前要查看的工作</label><select id="work-select" data-focus-key="work-select" aria-label="選擇要查看的 DevWeave 工作項目"><option value="">${active.length ? "選擇工作項目" : "目前沒有進行中的工作"}</option>${active.length ? `<optgroup label="進行中的工作">${active.map(workOption).join("")}</optgroup>` : ""}${closed.length ? `<optgroup label="已結束的歷史">${closed.map(workOption).join("")}</optgroup>` : ""}</select><small>${active.length ? `${active.length} 個進行中的工作` : "可從總覽開始新工作"}${closed.length ? ` · ${closed.length} 個歷史 work` : ""}</small></section>`;
}

function workOption(item: WorkItemProjection): string {
  return `<option value="${escapeAttr(item.id)}" ${item.id === selectedWorkId ? "selected" : ""}>${escapeHtml(item.title)} · ${escapeHtml(presentPhase(item.phase))}${item.status === "closed" ? "（歷史）" : ""}</option>`;
}

function renderWorkEmpty(activeCount: number): string {
  const action = activeCount
    ? `<button class="secondary" data-action="focus-work-select">選取進行中的工作</button>`
    : `<button class="primary" data-action="start-work">開始新工作</button>`;
  return `<section class="empty-card"><span class="empty-icon" aria-hidden="true">${activeCount ? "↥" : "＋"}</span><h2>${activeCount ? "請選擇一個進行中的工作" : "目前沒有進行中的工作"}</h2><p class="muted">${activeCount ? "先選取 work，才能查看 gate、blocker、task 與審查準備狀態。" : "closed history 仍可在上方選取瀏覽；若要繼續，請建立新的 work。"}</p>${action}</section>`;
}

function renderWorkDetail(work: WorkItemProjection): string {
  const closed = work.status === "closed" || work.phase === "closed";
  const readiness = snapshot ? buildReviewReadiness(snapshot, work) : null;
  const taskDone = work.tasks.filter((task) => ["completed", "approved", "passed"].includes(task.status)).length;
  const evidencePassed = work.evidence.filter((item) => item.status === "passed" && !item.stale && item.bindsCurrentSource).length;
  return `<section class="section-card"><div class="section-heading"><div><p class="eyebrow">${closed ? "歷史工作" : "目前工作"}</p><h2>${escapeHtml(work.title)}</h2><p class="muted">${escapeHtml(presentPhase(work.phase))} · ${escapeHtml(presentStatus(work.status))}</p></div><div class="pill-row"><span class="pill">${escapeHtml(presentRisk(work.risk))}</span>${closed ? `<span class="pill info">唯讀歷史</span>` : ""}</div></div><div class="gate-grid">${gateCard(work, "scope")} ${gateCard(work, "build")} ${gateCard(work, "acceptance")}</div><div class="summary-grid"><article class="summary-card"><span class="summary-label">任務</span><strong>${taskDone}/${work.tasks.length}</strong><small>${work.tasks.length ? "完成狀態" : "尚未建立 task"}</small></article><article class="summary-card"><span class="summary-label">驗證證據</span><strong>${evidencePassed}/${work.evidence.length}</strong><small>${work.staleEvidence.length ? `${work.staleEvidence.length} 個已過期` : "目前快照沒有 stale 標記"}</small></article><article class="summary-card"><span class="summary-label">知識</span><strong>${escapeHtml(presentStatus(work.knowledge.health))}</strong><small>${work.knowledge.pendingRefresh.length ? `${work.knowledge.pendingRefresh.length} 個頁面待更新` : "沒有待更新頁面"}</small></article></div>${work.blocker ? `<div class="notice danger"><span class="status-icon">!</span><div><strong>目前阻塞</strong><p>${escapeHtml(work.blocker.task ?? "Task")}：${escapeHtml(work.blocker.reason ?? "請在 Codex Chat 查看原因。")}</p><small>下一步：先處理 blocker，再 Refresh。</small></div></div>` : ""}${closed ? `<div class="notice info"><span class="status-icon">i</span><div><strong>這是歷史工作</strong><p>只提供唯讀資料與稽核內容；不會把它當成目前工作，也不提供 revise/approve。</p></div></div>` : readiness ? renderReadinessSummary(readiness) : ""}</section>${renderTaskBoard(work)}${preferences.displayMode === "advanced" ? `${renderArtifacts(work)}${renderTrace(work)}` : `<details class="details-card"><summary>展開 Requirements、Design、Plan 與 artifacts</summary>${renderArtifacts(work)}${renderTrace(work)}</details>`}`;
}

function gateCard(work: WorkItemProjection, gate: "scope" | "build" | "acceptance"): string {
  const projection = work.gates[gate];
  const label = presentGate(gate);
  const technical = gate === "scope" ? "G1" : gate === "build" ? "G2" : "G3";
  return `<article class="gate-card ${escapeAttr(projection.status)}"><div class="gate-title"><span class="status-icon">${icon(projection.status)}</span><span>${technical} ${escapeHtml(label.replace(/^G[123] /, ""))}</span></div><strong>${escapeHtml(presentStatus(projection.status))}</strong><p class="muted">${projection.approvedAt ? escapeHtml(projection.approvedAt) : "尚未記錄核准時間"}</p>${projection.approvedBy ? `<small>核准者：${escapeHtml(projection.approvedBy)}</small>` : ""}</article>`;
}

function renderReadinessSummary(readiness: ReviewReadiness): string {
  const failures = readiness.checks.filter((check) => !check.ok);
  const statusClass = readiness.status === "ready" ? "success" : readiness.status === "not_ready" ? "danger" : "warning";
  const statusLabel = readiness.status === "ready" ? "可進一步審查" : readiness.status === "not_ready" ? "尚未就緒" : readiness.status === "closed" ? "唯讀歷史" : `${failures.length} 項待確認`;
  return `<div class="readiness-banner ${statusClass}"><div><strong>${escapeHtml(readiness.summary)}</strong><p>目前 gate：${escapeHtml(presentGate(readiness.gate))} · Extension 只呈現檔案快照，approve 前仍由 engine 驗證。</p></div><span class="pill ${statusClass}">${escapeHtml(statusLabel)}</span></div>`;
}

function renderTaskBoard(work: WorkItemProjection): string {
  return `<section class="section-card"><div class="section-heading"><div><p class="eyebrow">工作進度</p><h2>工作任務</h2><p class="muted">每一項都顯示目前狀態與下一步，不只顯示數字。</p></div></div><div class="task-list">${work.tasks.length ? work.tasks.map((task) => `<div class="task-row"><span class="status-icon">${icon(task.status)}</span><span><strong>${escapeHtml(task.id)} · ${escapeHtml(presentStatus(task.status))}</strong><small>${escapeHtml(task.note || (task.status === "completed" ? "已完成" : "依 plan 順序處理"))}${task.evidence.length ? ` · evidence：${escapeHtml(task.evidence.join(", "))}` : ""}</small></span></div>`).join("") : `<p class="muted">目前沒有 task tracking；完成 G2 後由 engine 建立 task。</p>`}</div></section>`;
}

function renderArtifacts(work: WorkItemProjection): string {
  return `<section class="section-card"><div class="section-heading"><div><p class="eyebrow">詳細資料</p><h2>Requirements、Design、Plan</h2><p class="muted">保留原始 Markdown 唯讀開啟。</p></div></div><div class="artifact-list">${work.artifacts.map((artifact) => `<button class="artifact" data-action="open" data-path="${escapeAttr(artifact.path)}" ${artifact.exists ? "" : "disabled"}><span class="file-icon">${artifact.exists ? "▤" : "—"}</span><span><strong>${escapeHtml(artifact.path.split("/").at(-1) ?? artifact.path)}</strong><small>${artifact.exists ? `${artifact.text.length} chars${artifact.truncated ? " · 已截斷" : ""}` : "檔案不存在"}</small></span></button>`).join("") || `<p class="muted">目前沒有可開啟的 artifact。</p>`}</div></section>`;
}

function renderTrace(work: WorkItemProjection): string {
  const groups = [
    { label: "需求", names: ["brief.md", "requirements.md"], hint: "REQ / NFR → AC" },
    { label: "設計", names: ["design.md"], hint: "DEC 與風險決策" },
    { label: "計畫", names: ["plan.md"], hint: "TASK dependency" }
  ];
  return `<section class="section-card"><div class="trace-grid">${groups.map((group) => { const items = work.artifacts.filter((artifact) => group.names.includes(artifact.path.split("/").at(-1) ?? "")); return `<article class="trace-card"><strong>${group.label}</strong><small>${group.hint}</small>${items.map((artifact) => `<div class="trace-row"><span>${artifact.exists ? "✓" : "!"}</span><span><b>${escapeHtml(artifact.path.split("/").at(-1) ?? artifact.path)}</b><small>${artifact.exists ? traceIds(artifact.text).join(" · ") || "尚未找到 trace ID" : "檔案不存在"}</small></span></div>`).join("")}</article>`; }).join("")}</div></section>`;
}

function renderKnowledgeSection(): string {
  const knowledge = selectedWork()?.knowledge ?? snapshot?.knowledge;
  if (!knowledge) return "";
  wikiSearch.updateDocuments(knowledge.pages ?? []);
  return `<section class="section-card section-intro"><p class="eyebrow">知識</p><h2>讓 Wiki 告訴你哪些內容需要更新</h2><p class="muted">列表來自目前 snapshot；搜尋與分類不會觸發額外 repository scan。</p></section>${renderKnowledge(knowledge)}`;
}

function renderKnowledge(knowledge: WorkspaceSnapshot["knowledge"]): string {
  const pages = knowledge.pages ?? [];
  const categories = [...new Set(pages.map((page) => page.type))].sort();
  const pending = [...new Set([...knowledge.affectedPages, ...knowledge.pendingRefresh, ...knowledge.stalePages, ...knowledge.uncoveredChangedPaths])];
  const bootstrap = knowledge.bootstrap;
  const state = wikiSearch.state;
  return `<section class="section-card"><div class="section-heading"><div><p class="eyebrow">WIKI-FIRST 知識</p><h2>Wiki 狀態</h2><p class="muted">${knowledge.health === "healthy" ? "目前沒有被投影出的問題。" : "先處理下方提醒，再把結果交由 engine 確認。"}</p></div><span class="pill ${knowledge.health === "healthy" ? "success" : "warning"}">${escapeHtml(presentStatus(knowledge.health))}</span></div>${bootstrap.recommended ? `<div class="notice warning"><span class="status-icon">!</span><div><strong>Wiki 還沒有完整就緒</strong><p>${escapeHtml(bootstrapReasons(bootstrap.reasons))}</p><button class="primary" data-action="wiki-bootstrap" ${snapshot?.mutationBlocked || busyAction ? "disabled" : ""}>準備 Wiki bootstrap prompt</button></div></div>` : `<div class="notice success"><span class="status-icon">✓</span><div><strong>核心 Wiki 頁面已找到</strong><p>Extension 只顯示檔案投影；頁面是否 current 仍由 engine 與 Knowledge Review 決定。</p></div></div>`}${pending.length ? `<div class="actionable-list"><strong>需要留意的頁面與原因</strong>${pending.map((path) => `<div class="actionable-row"><span class="status-icon">•</span><span><strong>${escapeHtml(path)}</strong><small>${knowledge.pendingRefresh.includes(path) ? "工作狀態標示待 refresh" : knowledge.stalePages.includes(path) ? "來源 fingerprint 可能過期" : knowledge.uncoveredChangedPaths.includes(path) ? "目前變更尚未被頁面覆蓋" : "列為受影響頁面"}</small></span></div>`).join("")}</div>` : `<div class="notice info"><span class="status-icon">i</span><div><strong>目前沒有待更新頁面</strong><p>若這次工作改變了可重用的 codebase knowledge，請在 verification 依 Knowledge Review 處理。</p></div></div>`}<div class="knowledge-controls"><label for="wiki-query">搜尋 Wiki</label><input id="wiki-query" data-focus-key="wiki-query" type="search" value="${escapeAttr(state.draftQuery)}" placeholder="輸入後按 Enter 套用搜尋" aria-label="搜尋 Wiki 頁面" /><label for="wiki-type">分類</label><select id="wiki-type" data-focus-key="wiki-type" aria-label="依類型篩選 Wiki 頁面"><option value="all" ${state.type === "all" ? "selected" : ""}>全部分類</option>${categories.map((type) => `<option value="${escapeAttr(type)}" ${state.type === type ? "selected" : ""}>${escapeHtml(type)}</option>`).join("")}</select></div><div id="wiki-results">${renderKnowledgeResults(knowledge)}</div></section>`;
}

function renderKnowledgeResults(knowledge?: WorkspaceSnapshot["knowledge"]): string {
  const current = knowledge ?? selectedWork()?.knowledge ?? snapshot?.knowledge;
  if (!current) return "";
  wikiSearch.updateDocuments(current.pages ?? []);
  const pages = current.pages ?? [];
  const filtered = wikiSearch.filter();
  const visible = wikiSearch.visiblePages();
  return `<div id="wiki-metrics" class="metric-grid"><div class="metric"><span>頁面</span><strong>${pages.length}</strong></div><div class="metric"><span>篩選結果</span><strong>${filtered.length}</strong></div><div class="metric"><span>預留頁面</span><strong>${current.placeholderPages.length}</strong></div><div class="metric"><span>待 refresh</span><strong>${current.pendingRefresh.length}</strong></div></div><div class="page-list">${visible.map((page) => { const status = page.status ?? "unknown"; const parseErrors = page.parseErrors ?? []; return `<button class="page-row" data-action="open" data-path="${escapeAttr(page.path)}"><span class="status-icon">${icon(status)}</span><span><strong>${escapeHtml(page.title)}</strong><small>${escapeHtml(page.path)} · ${escapeHtml(presentStatus(status))}${page.verifiedBy ? ` · 已由 ${escapeHtml(page.verifiedBy)} 驗證` : ""}${parseErrors.length ? " · 解析提醒" : ""}</small></span></button>`; }).join("") || `<p class="muted">找不到符合條件的 Wiki 頁面。</p>`}</div>${!wikiSearch.state.showAll && filtered.length > visible.length ? `<button class="secondary" data-action="show-all-wiki">顯示全部 ${filtered.length} 頁</button>` : ""}`;
}

function renderVerificationSection(): string {
  const work = selectedWork();
  if (!work) {
    return `<section class="section-card section-intro"><p class="eyebrow">驗證與稽核</p><h2>先選擇一個工作項目</h2><p class="muted">有 active work 後，這裡會顯示 reviewer readiness、evidence 與稽核時間軸；verification commands 設定仍可先查看。</p></section>${renderVerificationSetup()}`;
  }
  return `<section class="section-card section-intro"><p class="eyebrow">驗證與稽核</p><h2>先看 reviewer 能否判斷目前 gate</h2><p class="muted">人話摘要優先；raw event 只在你需要追查時展開。</p></section>${renderVerificationSetup()}${renderReadinessDetail(work)}${renderEvidence(work)}${renderAcceptance(work)}${renderAudit(work)}`;
}

function renderVerificationSetup(): string {
  if (!snapshot) return "";
  const commands = snapshot.commands;
  const configured = commands.length > 0 && Object.values(snapshot.verificationProfiles).some((ids) => ids.length > 0);
  return `<section class="section-card"><div class="section-heading"><div><p class="eyebrow">驗證設定</p><h2>驗證命令</h2><p class="muted">Extension 只顯示設定與 evidence，不會在本機執行 command。</p></div><span class="pill ${configured ? "success" : "warning"}">${configured ? "已設定" : "需要設定"}</span></div>${configured ? `<div class="command-list">${commands.map((command) => `<div class="command-row"><span class="status-icon">⌘</span><span><strong>${escapeHtml(command.id)}</strong><small>${escapeHtml(command.argv.join(" "))} · cwd ${escapeHtml(command.cwd)} · timeout ${escapeHtml(command.timeoutSeconds)} 秒</small></span></div>`).join("")}</div>` : `<div class="notice warning"><span class="status-icon">!</span><div><strong>尚未設定 verification command/profile</strong><p>目前不能把工作說成已完成驗證；請在 Codex Chat 設定 commands，完成後回來 Refresh。</p></div></div>`}</section>`;
}

function renderReadinessDetail(work: WorkItemProjection): string {
  if (!snapshot) return "";
  const readiness = buildReviewReadiness(snapshot, work);
  const statusClass = readiness.status === "ready" ? "success" : readiness.status === "not_ready" ? "danger" : "warning";
  return `<section class="section-card"><div class="section-heading"><div><p class="eyebrow">REVIEWER 摘要</p><h2>${escapeHtml(presentGate(readiness.gate))} · ${readiness.status === "ready" ? "目前可進一步審查" : readiness.status === "closed" ? "歷史工作唯讀" : "仍有條件待確認"}</h2><p class="muted">${escapeHtml(readiness.summary)}</p></div><span class="pill ${statusClass}">${escapeHtml(presentStatus(readiness.status))}</span></div><div class="check-list">${readiness.checks.map((check) => `<div class="check-row ${check.ok ? "ok" : "not-ok"}"><span class="status-icon">${check.ok ? "✓" : "!"}</span><span><strong>${escapeHtml(check.label)} · ${check.ok ? "已符合" : "待處理"}</strong><small>${escapeHtml(check.detail)}${check.nextStep ? ` 下一步：${escapeHtml(check.nextStep)}` : ""}</small></span></div>`).join("")}</div><div class="action-row"><button class="primary" data-action="select-command" data-command="approve" ${work.status === "closed" || busyAction ? "disabled" : ""}>準備核准目前 gate</button><button class="secondary" data-action="select-command" data-command="revise" ${work.status === "closed" || busyAction ? "disabled" : ""}>準備修改方向</button><small>approve 不會加入 gate 參數；revise 可能讓既有 gate/evidence 失效。</small></div></section>`;
}

function renderEvidence(work: WorkItemProjection): string {
  const evidence = work.evidence.map((item) => {
    const stale = item.stale || !item.bindsCurrentSource;
    const state = item.status === "failed" ? "failed" : stale ? "stale" : item.status;
    const review = item.review ? `<details class="raw-details"><summary>展開 Independent Review raw evidence</summary><small>result：${escapeHtml(item.review.result)} · severity：${escapeHtml(item.review.severity)} · reviewer：${escapeHtml(item.review.reviewerId ?? "opaque")}</small>${item.review.reportSha256 ? `<small>report hash：<code>${escapeHtml(item.review.reportSha256)}</code></small>` : ""}${item.review.findings.length ? `<ul>${item.review.findings.map((finding) => `<li><strong>${escapeHtml(finding.id)} · ${escapeHtml(finding.severity)}</strong>：${escapeHtml(finding.title)} — ${escapeHtml(finding.recommendation)}</li>`).join("")}</ul>` : `<p class="muted">沒有 findings。</p>`}</details>` : "";
    return `<article class="evidence-card"><div class="section-heading"><strong>${escapeHtml(item.id)} · ${escapeHtml(item.kind)}</strong><span class="pill ${state === "passed" ? "success" : state === "stale" ? "warning" : "danger"}">${escapeHtml(presentStatus(state))}</span></div><p>${escapeHtml(item.summary || "沒有摘要")}</p><small>涵蓋：${escapeHtml(item.covers.join(", ") || "—")} · tasks：${escapeHtml(item.tasks.join(", ") || "—")}</small>${stale ? `<div class="notice warning"><span class="status-icon">!</span><div><strong>這筆 evidence 不能直接視為 current</strong><p>請重新執行對應 verification，再回來 Refresh。</p></div></div>` : ""}${review}${item.rawLog ? `<details class="raw-details"><summary>查看 raw log 路徑</summary><code class="raw-log-path">${escapeHtml(item.rawLog)}</code></details>` : ""}</article>`;
  }).join("");
  return `<section class="section-card"><div class="section-heading"><div><p class="eyebrow">證據</p><h2>Evidence 狀態</h2><p class="muted">顯示失敗、過期、目前 source 綁定與 Independent Review raw evidence。</p></div></div><div class="evidence-list">${evidence || `<p class="muted">目前沒有 evidence；若要進入驗收，請先完成 verification。</p>`}</div></section>`;
}

function renderAcceptance(work: WorkItemProjection): string {
  const planned = work.knowledge.planned;
  const coupled = planned && Array.isArray(planned.coupled) ? planned.coupled as string[] : [];
  return `<details class="details-card" ${preferences.displayMode === "advanced" ? "open" : ""}><summary>Baseline、Knowledge promotion 與 waiver 詳細資訊</summary><div class="acceptance-grid"><div><strong>Baseline targets</strong><ul>${work.baselineTargets.map((path) => `<li><code>${escapeHtml(path)}</code></li>`).join("") || "<li>本 work 未宣告 baseline 更新</li>"}</ul><small>${escapeHtml(work.baselineRationale || "本次 UX refinement 不修改 baseline truth。")}</small></div><div><strong>Knowledge promotion</strong><ul><li>受影響：${escapeHtml(work.knowledge.affectedPages.join(", ") || "沒有")}</li><li>待 refresh：${escapeHtml(work.knowledge.pendingRefresh.join(", ") || "沒有")}</li><li>coupled index/log：${escapeHtml(coupled.join(", ") || "尚未宣告")}</li><li>review：${escapeHtml(work.knowledge.review.current ? "已完成" : work.knowledge.review.required ? "待完成" : "不需要")}</li></ul></div></div><div class="waiver-list"><strong>Waiver</strong>${work.waivers.map((waiver) => `<div class="task-row"><span class="status-icon">!</span><span><b>${escapeHtml(waiver.kind)} · ${escapeHtml(waiver.target)}</b><small>${escapeHtml(waiver.reason)}</small></span></div>`).join("") || `<p class="muted">目前沒有 waiver。</p>`}</div></details>`;
}

function renderAudit(work: WorkItemProjection): string {
  const events = work.events ?? [];
  const visible = showAllAudit ? events : events.slice(-12);
  return `<section class="section-card"><div class="section-heading"><div><p class="eyebrow">稽核</p><h2>可讀的事件時間軸</h2><p class="muted">先看事件與結果；原始 JSONL 保留在每一筆的展開區域。</p></div><span class="pill info">唯讀</span></div><div class="audit-list">${visible.map((raw) => renderAuditEvent(presentAuditEvent(raw))).join("") || `<p class="muted">目前沒有稽核事件。</p>`}</div>${!showAllAudit && events.length > visible.length ? `<button class="secondary" data-action="show-all-audit">顯示全部 ${events.length} 筆事件</button>` : ""}</section>`;
}

function renderAuditEvent(event: AuditEventPresentation): string {
  return `<article class="audit-event"><div class="audit-marker" aria-hidden="true">•</div><div><div class="audit-heading"><strong>${escapeHtml(event.summary)}</strong><small>${escapeHtml(event.at)} · ${escapeHtml(event.event)}</small></div><details class="raw-details"><summary>展開 technical raw event</summary><code>${escapeHtml(event.raw)}</code></details></div></article>`;
}

function renderDiagnostics(): string {
  if (!snapshot) return "";
  const diagnostics = snapshot.diagnostics.map(presentDiagnostic);
  const blocked = snapshot.mutationBlocked
    ? `<div class="notice danger"><span class="status-icon">!</span><div><strong>目前只允許安全查看</strong><p>snapshot 有 critical contract 問題；mutation prompt 暫停，status 仍可交給 Codex Chat 確認。</p></div></div>`
    : "";
  if (!diagnostics.length && !blocked) return "";
  return `<section class="notice-stack" aria-label="Workspace 問題與修復建議">${blocked}${diagnostics.map(renderDiagnostic).join("")}</section>`;
}

function renderDiagnostic(item: DiagnosticPresentation): string {
  return `<div class="notice ${item.severity}"><span class="status-icon">${icon(item.severity)}</span><div><strong>${escapeHtml(item.title)}</strong><p>${escapeHtml(item.detail)}</p><small>建議：${escapeHtml(item.resolution)}</small><details class="raw-details"><summary>查看 technical code/path</summary><code>${escapeHtml(item.code)}${item.path ? ` · ${escapeHtml(item.path)}` : ""}</code></details></div></div>`;
}

function renderPublicCommandForm(work: WorkItemProjection | null): string {
  const command = selectedCommand;
  const presentation = commandPresentations().find((item) => item.name === command);
  const closed = Boolean(work && (work.status === "closed" || work.phase === "closed"));
  const activeWorks = snapshot?.workItems.filter((item) => item.status === "active") ?? [];
  const selectedActive = Boolean(work && work.status === "active");
  const requiresWork = presentation?.requiresWork ?? false;
  const mutationDisabled = Boolean(snapshot?.mutationBlocked && presentation?.mutation);
  const nextNeedsSelection = command === "next" && (!selectedActive || activeWorks.length === 0);
  const disabled = Boolean(busyAction || mutationDisabled || (requiresWork && (!work || closed)) || nextNeedsSelection);
  const nextHint = command === "next" && nextNeedsSelection
    ? `<small>${activeWorks.length > 1 ? "目前有多個 active work；請先選取一個 work。" : activeWorks.length === 0 ? "目前沒有 active work；請先建立或選取 work。" : "請先選取進行中的 work。"}</small>`
    : "";
  return `<section class="section-card composer" aria-labelledby="public-command-title"><div class="section-heading"><div><p class="eyebrow">從任務開始</p><h2 id="public-command-title">準備一個公開操作</h2><p class="muted">選擇你想完成的事；Extension 會先預覽，再由你複製到 Codex Chat。</p></div><span class="pill info">公開操作</span></div><form id="public-command-form"><label for="command-select">我要</label><select id="command-select" data-focus-key="command-select" name="command" aria-label="選擇要進行的 DevWeave 任務">${publicCommandOptions(command)}</select><p class="field-hint">${escapeHtml(presentation?.description ?? "選擇一個公開操作。")}${presentation ? ` <code>${escapeHtml(presentation.technicalLabel)}</code>` : ""}</p>${renderCommandFields(command, work)}${mutationDisabled ? `<div class="notice warning"><span class="status-icon">!</span><div><strong>目前只允許查看</strong><p>請先使用 status 公開命令確認 critical diagnostic；mutation prompt 暫停產生。</p></div></div>` : ""}<div class="action-row"><button class="primary" type="submit" ${disabled ? "disabled" : ""}>預覽公開操作</button>${requiresWork && (!work || closed) ? `<small>${closed ? "closed work 只能瀏覽，請選擇進行中的 work。" : "請先選擇一個進行中的 work。"}</small>` : ""}${nextHint}</div></form></section>`;
}

function publicCommandOptions(selected: PublicCommandName): string {
  const groups: Array<[string, string]> = [["start", "開始工作"], ["progress", "查看進度"], ["review", "審查決策"], ["knowledge", "建立知識"]];
  return groups.map(([group, label]) => `<optgroup label="${label}">${commandPresentations().filter((item) => item.group === group).map((item) => `<option value="${item.name}" ${item.name === selected ? "selected" : ""}>${escapeHtml(item.label)}</option>`).join("")}</optgroup>`).join("");
}

function renderCommandFields(command: PublicCommandName, work: WorkItemProjection | null): string {
  switch (command) {
    case "new": return `<label for="command-goal">想完成什麼</label><input id="command-goal" name="goal" type="text" placeholder="例如：建立 CSV 匯出能力" autocomplete="off" />`;
    case "feature": return `<label for="command-request">功能描述</label><textarea id="command-request" name="request" rows="3" placeholder="描述要新增的功能" spellcheck="true"></textarea>`;
    case "refactor": return `<label for="command-request">整理目標</label><textarea id="command-request" name="request" rows="3" placeholder="描述要整理或重構的部分" spellcheck="true"></textarea>`;
    case "bug": return `<label for="command-symptom">實際症狀</label><textarea id="command-symptom" name="symptom" rows="3" placeholder="描述實際觀察到的問題" spellcheck="true"></textarea>`;
    case "next":
      return work && work.status === "active" ? `<label class="checkbox-field" for="include-work"><input id="include-work" name="include-work" type="checkbox" checked />帶入目前 work <code>${escapeHtml(work.id)}</code></label>` : (snapshot?.workItems.filter((item) => item.status === "active").length ?? 0) > 1 ? `<div class="notice warning"><span class="status-icon">!</span><div><strong>next 需要先選定 work</strong><p>目前有多個 active work；請先在上方工作選擇器明確選取一個。</p></div></div>` : `<p class="field-hint">next 需要一個進行中的 work；目前尚未選定。</p>`;
    case "status":
      return work && work.status === "active" ? `<label class="checkbox-field" for="include-work"><input id="include-work" name="include-work" type="checkbox" checked />查詢目前 work <code>${escapeHtml(work.id)}</code><small>取消勾選即可查詢全部 active work。</small></label>` : (snapshot?.workItems.some((item) => item.status === "active") ? `<label class="checkbox-field" for="include-work"><input id="include-work" name="include-work" type="checkbox" />只查詢已選 work<small>目前未選定單一 work；預設會產生 <code>$devweave status --all</code>。</small></label>` : `<p class="field-hint">目前沒有 active work；會產生 <code>$devweave status --all</code>，讓 engine 明確回報空的 active-work 清單。</p>`);
    case "wikiBootstrap": return `<p class="field-hint">會探索整個 repository，建立或續接一般 DevWeave bootstrap work；Extension 只產生 prompt。</p>`;
    case "revise": return work && work.status === "active" ? `<div class="selected-work"><span>目前 work</span><code>${escapeHtml(work.id)}</code></div><label for="command-change">要修改的方向</label><textarea id="command-change" name="change" rows="3" placeholder="說明需要修改的決策或方向" spellcheck="true"></textarea>` : `<p class="field-hint">revise 需要先選擇進行中的 work。</p>`;
    case "approve": return work && work.status === "active" ? `<div class="selected-work"><span>會核准畫面標示的目前 gate</span><code>${escapeHtml(work.id)}</code><small>公開命令不帶 gate 參數；送出前請確認 reviewer readiness。</small></div>` : `<p class="field-hint">approve 需要先選擇進行中的 work。</p>`;
  }
}

function formIntent(form: HTMLFormElement, work: WorkItemProjection | null): PublicCommandIntent | null {
  const command = formValue(form, "command");
  if (!isPublicCommandName(command)) return null;
  let candidate: unknown;
  switch (command) {
    case "new": candidate = { type: command, goal: formValue(form, "goal") }; break;
    case "feature":
    case "refactor": candidate = { type: command, request: formValue(form, "request") }; break;
    case "bug": candidate = { type: command, symptom: formValue(form, "symptom") }; break;
    case "next": {
      const activeWorks = snapshot?.workItems.filter((item) => item.status === "active") ?? [];
      if (activeWorks.length === 0 || !work || work.status !== "active") return null;
      candidate = { type: command, workId: work.id };
      break;
    }
    case "status": candidate = form.elements.namedItem("include-work") && ((form.elements.namedItem("include-work") as HTMLInputElement).checked) && work?.status === "active" ? { type: command, workId: work.id } : { type: command, all: true }; break;
    case "wikiBootstrap": candidate = { type: command }; break;
    case "revise": candidate = work && work.status === "active" ? { type: command, workId: work.id, change: formValue(form, "change") } : null; break;
    case "approve": candidate = work && work.status === "active" ? { type: command, workId: work.id } : null; break;
  }
  return parsePublicCommandIntent(candidate);
}

function renderResultPanel(): string {
  if (previewBundle) return renderActionPreview(previewBundle);
  if (copiedBundle) return renderCopiedResult(copiedBundle);
  if (bootstrapReport) return renderBootstrapResult(bootstrapReport);
  return "";
}

function renderPlanModeHandoff(guidance: SnapshotGuidance["planModeGuidance"]): string {
  if (!guidance?.required) return "";
  return `<div class="notice warning plan-mode-handoff" role="status" aria-label="Plan Mode 導流"><span class="status-icon">!</span><div><strong>先切換 Plan Mode</strong><p>先切換 Plan Mode，再貼到 Codex Chat；Extension 不會嘗試切換 host mode。</p></div></div>`;
}

function renderActionPreview(bundle: PromptBundle): string {
  const presentation = commandPresentations().find((item) => item.name === bundle.command);
  const work = selectedWork();
  const gate = work ? firstPendingGate(work) : null;
  const willNot = bundle.mutation
    ? "不會在 Extension 直接執行 CLI、寫入一般 workspace，或代替你送出 Codex Chat。"
    : "不會修改 repository，也不會把檔案 snapshot 當成 engine 權威結果。";
  return `<section id="result-panel" class="preview" aria-labelledby="preview-title"><div class="preview-heading"><div><p class="eyebrow">公開操作預覽</p><h2 id="preview-title">先確認再複製</h2></div><span class="pill ${bundle.mutation ? "warning" : "info"}">${bundle.mutation ? "需要你手動送出" : "唯讀查詢"}</span></div><div class="two-column"><div><h3>這個操作會做什麼</h3><p>${escapeHtml(presentation?.description ?? "準備一個公開 DevWeave prompt。")}</p></div><div><h3>不會做什麼</h3><p>${escapeHtml(willNot)}</p></div></div><div class="notice info"><span class="status-icon">i</span><div><strong>目前操作脈絡</strong><p>${work ? `work：${escapeHtml(work.id)} · 目前 gate：${escapeHtml(presentGate(gate))}` : "目前沒有帶入 work ID"} · snapshot 只供參考。</p></div></div>${bundle.planModeGuidance?.required ? renderPlanModeHandoff(bundle.planModeGuidance) : ""}<h3>要貼到 Codex Chat 的內容</h3><pre>${escapeHtml(bundle.chatText)}</pre>${bundle.warnings.length ? `<div class="notice warning"><strong>送出前請留意</strong><ul>${bundle.warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("")}</ul></div>` : ""}<div class="handoff-steps"><h3>複製後</h3><p>到 Codex Chat 貼上並送出；engine 完成後回到這裡按 Refresh，才能看到新的檔案投影。</p></div><div class="action-row"><button class="primary" data-action="confirm-copy" ${busyAction ? "disabled" : ""}>確認並複製 prompt</button><button class="secondary" data-action="cancel-preview" ${busyAction ? "disabled" : ""}>取消</button></div></section>`;
}

function renderCopiedResult(bundle: PromptBundle): string {
  return `<section id="result-panel" class="preview" aria-labelledby="copied-title"><div class="preview-heading"><div><p class="eyebrow">Codex Chat 交接</p><h2 id="copied-title">prompt 已複製</h2></div><span class="pill success">已交給你送出</span></div>${bundle.planModeGuidance?.required ? renderPlanModeHandoff(bundle.planModeGuidance) : ""}<p>請到 Codex Chat 貼上並送出；Extension 不會自行執行。完成後回來按 Refresh，重新讀取檔案 snapshot。</p><details class="raw-details"><summary>查看已複製的 prompt</summary><pre>${escapeHtml(bundle.chatText)}</pre></details></section>`;
}

function renderBootstrapResult(report: BootstrapReport): string {
  const list = (values: string[]) => values.length ? `<ul>${values.map((value) => `<li><code>${escapeHtml(value)}</code></li>`).join("")}</ul>` : `<p class="muted">沒有項目</p>`;
  const conflicts = report.conflicts.map((item) => `<li><code>${escapeHtml(item.path)}</code> · ${escapeHtml(item.reason)}</li>`).join("");
  const errors = report.errors.map((item) => `<li><code>${escapeHtml(item.path)}</code> · ${escapeHtml(item.reason)}</li>`).join("");
  const missing = report.missing.length ? `<h3>尚未完整</h3>${list(report.missing)}` : "";
  return `<section id="result-panel" class="preview" aria-labelledby="bootstrap-result-title"><div class="preview-heading"><div><p class="eyebrow">DevWeave 初始化</p><h2 id="bootstrap-result-title">${report.complete ? "初始化完成" : "初始化未完成"}</h2></div><span class="pill ${report.complete ? "success" : "danger"}">${escapeHtml(presentStatus(report.status))}</span></div><p>${report.complete ? "這次操作已由你確認，Extension 只套用固定 bootstrap manifest。下一步是確認 Codex hook、設定 verification commands、建立第一個 work item。" : "Extension 沒有宣稱初始化完整；先處理衝突或錯誤，修正後可再次執行補齊。"}</p><h3>已建立</h3>${list(report.created)}<h3>已採用</h3>${list(report.adopted)}${missing}${conflicts ? `<h3>衝突</h3><ul>${conflicts}</ul>` : ""}${errors ? `<h3>錯誤</h3><ul>${errors}</ul>` : ""}${report.rolledBack.length ? `<h3>已回復</h3>${list(report.rolledBack)}` : ""}</section>`;
}

function renderStatus(): string {
  const detail = statusError && errorDetail
    ? `<details class="raw-details status-details"><summary>查看 technical 詳情</summary><code>${escapeHtml(errorDetail)}</code></details>`
    : "";
  return `<div id="copy-status" class="status-line ${statusError ? "error" : "success"}" role="${statusError ? "alert" : "status"}" aria-live="polite" aria-busy="${Boolean(busyAction)}">${busyAction ? "⏳ " : ""}${escapeHtml(statusMessage)}${detail}</div>`;
}

function selectedWork(): WorkItemProjection | null {
  if (!snapshot || !selectedWorkId) return null;
  return snapshot.workItems.find((item) => item.id === selectedWorkId) ?? null;
}

function firstPendingGate(work: WorkItemProjection): "scope" | "build" | "acceptance" | null {
  if (work.gates.scope.status !== "approved") return "scope";
  if (work.gates.build.status !== "approved") return "build";
  if (work.gates.acceptance.status !== "approved") return "acceptance";
  return null;
}

function verificationSummary(current: WorkspaceSnapshot): string {
  const configured = current.commands.length > 0 && Object.values(current.verificationProfiles).some((ids) => ids.length > 0);
  return configured ? "已設定" : "需要設定";
}

function verificationDetail(current: WorkspaceSnapshot): string {
  return current.commands.length ? `${current.commands.length} 個 command 可供 engine 使用` : "目前沒有 command/profile";
}

function bootstrapReasons(reasons: string[]): string {
  const labels: Record<string, string> = { overview_not_ready: "overview 尚未就緒", architecture_missing: "缺少 architecture 頁面", module_missing: "缺少 module 頁面", critical_lint: "有 critical 解析問題" };
  return reasons.map((reason) => labels[reason] ?? reason).join("、") || "核心頁面尚未完整";
}

function commandLabel(command: PublicCommandName): string {
  return commandPresentations().find((item) => item.name === command)?.label ?? command;
}

function selectSection(section: DashboardSection): void {
  selectedSection = section;
  focusRestoreKey = `section-${section}`;
  renderScheduler.request();
}

function formValue(form: HTMLFormElement, name: string): string {
  const value = new FormData(form).get(name);
  return typeof value === "string" ? value : "";
}

function clearPromptResult(): void {
  pendingIntent = null;
  previewRevision = null;
  previewBundle = null;
  copiedBundle = null;
  bootstrapReport = null;
}

function restoreFocus(key: string | null): void {
  if (!key) return;
  const element = Array.from(document.querySelectorAll<HTMLElement>("[data-focus-key], #command-select, #wiki-query, #wiki-type, #work-select")).find((candidate) => candidate.dataset.focusKey === key || candidate.id === key);
  element?.focus();
}

function focusByKey(key: string): void {
  window.setTimeout(() => restoreFocus(key), 0);
}

function isDashboardSection(value: unknown): value is DashboardSection {
  return value === "overview" || value === "work" || value === "knowledge" || value === "verification" || value === "help";
}

function isDisplayMode(value: unknown): value is DisplayMode {
  return value === "concise" || value === "advanced";
}

function isPublicCommandName(value: unknown): value is PublicCommandName {
  return typeof value === "string" && ["new", "feature", "refactor", "bug", "next", "status", "revise", "approve", "wikiBootstrap"].includes(value);
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

function reducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function traceIds(text: string): string[] {
  return [...new Set(text.match(/\b(?:REQ|NFR|AC|DEC|TASK)-\d{3}\b/g) ?? [])].slice(0, 12);
}

function escapeHtml(value: unknown): string {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function escapeAttr(value: unknown): string {
  return escapeHtml(value).replaceAll("\n", "&#10;");
}

renderLoading();
