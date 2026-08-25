import type { UiProjection } from "../src/ui/projection";
import type { UiIntent } from "../src/ui/protocol";
import { nextTabIndex, renderControlCenter, TABS } from "./render";

declare function acquireVsCodeApi<T = unknown>(): { postMessage(message: UiIntent): void; getState(): T | undefined; setState(value: T): void };

interface PersistedState { activeTab: string; }

const vscode = acquireVsCodeApi<PersistedState>();
const root = document.querySelector<HTMLElement>("#app");
let activeTab = vscode.getState()?.activeTab ?? "overview";
let projection: UiProjection | undefined;

window.addEventListener("message", (event: MessageEvent<unknown>) => {
  if (!isRecord(event.data) || event.data.type !== "state" || !isRecord(event.data.state)) return;
  projection = event.data.state as unknown as UiProjection;
  render();
});

document.addEventListener("submit", (event) => {
  if (!(event.target instanceof HTMLFormElement) || event.target.id !== "start-form") return;
  event.preventDefault();
  const goal = value("goal");
  const scope = value("scope");
  const risk = value("risk");
  if (risk !== "low" && risk !== "standard" && risk !== "high") return;
  vscode.postMessage({ type: "start", goal, scope, risk });
});

document.addEventListener("click", (event) => {
  const target = event.target instanceof Element ? event.target.closest<HTMLElement>("[data-action],[data-tab]") : null;
  if (!target) return;
  const tab = target.dataset.tab;
  if (tab && TABS.includes(tab as typeof TABS[number])) {
    activeTab = tab;
    vscode.setState({ activeTab });
    render(target.id);
    return;
  }
  const action = target.dataset.action;
  if (!action) return;
  dispatchAction(action, target);
});

document.addEventListener("keydown", (event) => {
  if (!(event.target instanceof HTMLElement) || event.target.getAttribute("role") !== "tab") return;
  const tabs = Array.from(document.querySelectorAll<HTMLElement>('[role="tab"]'));
  const current = tabs.indexOf(event.target);
  const next = nextTabIndex(current, event.key, tabs.length);
  if (next === current) return;
  event.preventDefault();
  activeTab = tabs[next].dataset.tab ?? activeTab;
  vscode.setState({ activeTab });
  render(tabs[next].id);
});

function dispatchAction(action: string, target: HTMLElement): void {
  if (action === "resume" && projection?.run) {
    const runId = String(projection.run.run_id ?? "");
    if (runId) vscode.postMessage({ type: "resume", runId, ...(projection.threadId ? { threadId: projection.threadId } : {}) });
  } else if (action === "turn" || action === "steer") {
    const text = value("turn-input");
    if (text.trim()) vscode.postMessage({ type: action, text });
  } else if (action === "interrupt" || action === "cancel" || action === "review" || action === "refresh") {
    vscode.postMessage({ type: action });
  } else if (action === "approval") {
    const requestId = target.dataset.requestId;
    const decision = target.dataset.decision;
    if (requestId && (decision === "accept" || decision === "decline" || decision === "cancel")) {
      vscode.postMessage({ type: "approval", requestId, decision });
    }
  } else if (action === "decision") {
    const decisionId = target.dataset.decisionId;
    const optionId = target.dataset.optionId;
    if (decisionId && optionId) vscode.postMessage({ type: "decision", decisionId, optionId });
  } else if (action === "decision-other") {
    const decisionId = target.dataset.decisionId;
    const other = value("decision-other");
    if (decisionId && other.trim()) vscode.postMessage({ type: "decision", decisionId, other });
  } else if (action === "gate") {
    const gateId = target.dataset.gateId;
    if (gateId) vscode.postMessage({ type: "gate", gateId, approve: target.dataset.approve === "true" });
  }
}

function render(focusId?: string): void {
  if (!root || !projection) return;
  const focusKey = document.activeElement instanceof HTMLElement ? document.activeElement.dataset.focusKey : undefined;
  root.innerHTML = renderControlCenter(projection, activeTab);
  const focusTarget = focusId ? document.getElementById(focusId) : focusKey ? document.querySelector<HTMLElement>(`[data-focus-key="${CSS.escape(focusKey)}"]`) : null;
  focusTarget?.focus();
}

function value(id: string): string {
  const element = document.getElementById(id);
  return element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement || element instanceof HTMLSelectElement
    ? element.value.slice(0, 32_768)
    : "";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
