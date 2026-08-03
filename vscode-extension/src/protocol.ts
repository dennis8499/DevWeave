import type { ActionIntent, GateName, PromptBundle, RiskLevel, WorkKind, WorkspaceSnapshot } from "./model";
import type { BootstrapReport } from "./bootstrap";

export type WebviewToHostMessage =
  | { type: "refresh" }
  | { type: "initialize" }
  | { type: "selectWork"; workId: string | null }
  | { type: "openFile"; path: string }
  | { type: "previewAction"; intent: ActionIntent }
  | { type: "copyAction"; intent: ActionIntent };

export type HostToWebviewMessage =
  | { type: "snapshot"; snapshot: WorkspaceSnapshot }
  | { type: "bootstrapResult"; report: BootstrapReport; snapshot: WorkspaceSnapshot }
  | { type: "actionPreview"; bundle: PromptBundle }
  | { type: "copyResult"; ok: true; bundle: PromptBundle }
  | { type: "copyResult"; ok: false; message: string }
  | { type: "protocolError"; message: string }
  | { type: "error"; message: string };

export function parseWebviewMessage(value: unknown): WebviewToHostMessage | null {
  const record = asRecord(value);
  if (!record || typeof record.type !== "string") {
    return null;
  }
  switch (record.type) {
    case "refresh":
      return Object.keys(record).every((key) => key === "type") ? { type: "refresh" } : null;
    case "initialize":
      return noExtraFields(record, ["type"]) ? { type: "initialize" } : null;
    case "selectWork":
      return (record.workId === null || typeof record.workId === "string")
        ? { type: "selectWork", workId: record.workId }
        : null;
    case "openFile":
      return typeof record.path === "string" ? { type: "openFile", path: record.path } : null;
    case "copyAction": {
      const intent = parseActionIntent(record.intent);
      return intent ? { type: "copyAction", intent } : null;
    }
    case "previewAction": {
      const intent = parseActionIntent(record.intent);
      return intent ? { type: "previewAction", intent } : null;
    }
    default:
      return null;
  }
}

export function parseActionIntent(value: unknown): ActionIntent | null {
  const record = asRecord(value);
  if (!record || typeof record.type !== "string") {
    return null;
  }
  switch (record.type) {
    case "init":
      return record.goal === undefined ? { type: "init" } : isString(record.goal) ? { type: "init", goal: record.goal } : null;
    case "doctor":
      return noExtraFields(record, ["type"]) ? { type: "doctor" } : null;
    case "project":
      return noExtraFields(record, ["type"]) ? { type: "project" } : null;
    case "commandList":
      return noExtraFields(record, ["type"]) ? { type: "commandList" } : null;
    case "commandSet":
      return isString(record.id) && isString(record.cwd) && isStringArray(record.argv) && isFiniteNumber(record.timeout) && isRiskArray(record.requiredFor)
        ? { type: "commandSet", id: record.id, cwd: record.cwd, argv: record.argv, timeout: record.timeout, requiredFor: record.requiredFor }
        : null;
    case "commandRemove":
      return isString(record.id) ? { type: "commandRemove", id: record.id } : null;
    case "start":
      return isKind(record.kind) && isString(record.title) && isRisk(record.risk) && isString(record.rationale)
        ? { type: "start", kind: record.kind, title: record.title, risk: record.risk, rationale: record.rationale }
        : null;
    case "status":
      return optionalString(record, "workId") && optionalBoolean(record, "all")
        ? { type: "status", ...(record.workId === undefined ? {} : { workId: record.workId as string }), ...(record.all === undefined ? {} : { all: record.all as boolean }) }
        : null;
    case "instructions":
      return isString(record.workId) ? { type: "instructions", workId: record.workId } : null;
    case "validate":
      return isString(record.workId) && optionalGate(record, "gate")
        ? { type: "validate", workId: record.workId, ...(record.gate === undefined ? {} : { gate: record.gate as GateName }) }
        : null;
    case "bind":
      return isString(record.workId) ? { type: "bind", workId: record.workId } : null;
    case "risk":
      return isString(record.workId) && isRisk(record.level) && isString(record.rationale) && optionalString(record, "downgradeRationale")
        ? { type: "risk", workId: record.workId, level: record.level, rationale: record.rationale, ...(record.downgradeRationale === undefined ? {} : { downgradeRationale: record.downgradeRationale as string }) }
        : null;
    case "scope":
      return isString(record.workId) && isStringArray(record.paths) && isString(record.rationale)
        ? { type: "scope", workId: record.workId, paths: record.paths, rationale: record.rationale }
        : null;
    case "baseline":
      return isString(record.workId) && isStringArray(record.targets) && isString(record.rationale)
        ? { type: "baseline", workId: record.workId, targets: record.targets, rationale: record.rationale }
        : null;
    case "knowledgeStatus":
      return optionalString(record, "workId")
        ? { type: "knowledgeStatus", ...(record.workId === undefined ? {} : { workId: record.workId as string }) }
        : null;
    case "knowledgeContext":
      return isString(record.workId) && isStringArray(record.pages) && isStringArray(record.gaps)
        ? { type: "knowledgeContext", workId: record.workId, pages: record.pages, gaps: record.gaps }
        : null;
    case "knowledgePlan":
      return isString(record.workId) && isStringArray(record.upserts) && isStringArray(record.deletes) && isString(record.rationale)
        ? { type: "knowledgePlan", workId: record.workId, upserts: record.upserts, deletes: record.deletes, rationale: record.rationale }
        : null;
    case "knowledgeSeal":
      return isString(record.workId) && isStringArray(record.pages)
        ? { type: "knowledgeSeal", workId: record.workId, pages: record.pages }
        : null;
    case "taskStart":
      return isString(record.workId) && isString(record.taskId) ? { type: "taskStart", workId: record.workId, taskId: record.taskId } : null;
    case "taskComplete":
      return isString(record.workId) && isString(record.taskId) && optionalStringArray(record, "evidence") && optionalString(record, "note")
        ? { type: "taskComplete", workId: record.workId, taskId: record.taskId, ...(record.evidence === undefined ? {} : { evidence: record.evidence as string[] }), ...(record.note === undefined ? {} : { note: record.note as string }) }
        : null;
    case "taskBlock":
      return isString(record.workId) && isString(record.taskId) && isString(record.note)
        ? { type: "taskBlock", workId: record.workId, taskId: record.taskId, note: record.note }
        : null;
    case "evidenceAdd":
      return isString(record.workId) && isString(record.kind) && isEvidenceStatus(record.status) && isString(record.summary) && isStringArray(record.covers) && isStringArray(record.tasks) && optionalObservedResult(record, "observedResult") && optionalBoolean(record, "bindsCurrentSource")
        ? { type: "evidenceAdd", workId: record.workId, kind: record.kind, status: record.status, summary: record.summary, covers: record.covers, tasks: record.tasks, ...(record.observedResult === undefined ? {} : { observedResult: record.observedResult as "success" | "failure" | "neutral" }), ...(record.bindsCurrentSource === undefined ? {} : { bindsCurrentSource: record.bindsCurrentSource as boolean }) }
        : null;
    case "verify":
      return isString(record.workId) && isString(record.command) && isString(record.kind) && isStringArray(record.covers) && isStringArray(record.tasks) && optionalExpect(record, "expect")
        ? { type: "verify", workId: record.workId, command: record.command, kind: record.kind, covers: record.covers, tasks: record.tasks, ...(record.expect === undefined ? {} : { expect: record.expect as "zero" | "nonzero" | "any" }) }
        : null;
    case "waiverAdd":
      return isString(record.workId) && isString(record.kind) && isString(record.target) && isString(record.reason) && optionalGate(record, "gate")
        ? { type: "waiverAdd", workId: record.workId, kind: record.kind, target: record.target, reason: record.reason, ...(record.gate === undefined ? {} : { gate: record.gate as GateName }) }
        : null;
    case "approve":
      return isString(record.workId) && optionalGate(record, "gate")
        ? { type: "approve", workId: record.workId, ...(record.gate === undefined ? {} : { gate: record.gate as GateName }) }
        : null;
    case "revise":
      return isString(record.workId) && isRevisionPhase(record.from) && isString(record.reason)
        ? { type: "revise", workId: record.workId, from: record.from, reason: record.reason }
        : null;
    case "close":
      return isString(record.workId) ? { type: "close", workId: record.workId } : null;
    default:
      return null;
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(isString);
}

function optionalString(record: Record<string, unknown>, key: string): boolean {
  return record[key] === undefined || isString(record[key]);
}

function optionalStringArray(record: Record<string, unknown>, key: string): boolean {
  return record[key] === undefined || isStringArray(record[key]);
}

function optionalBoolean(record: Record<string, unknown>, key: string): boolean {
  return record[key] === undefined || typeof record[key] === "boolean";
}

function optionalGate(record: Record<string, unknown>, key: string): boolean {
  return record[key] === undefined || isGate(record[key]);
}

function optionalObservedResult(record: Record<string, unknown>, key: string): boolean {
  return record[key] === undefined || record[key] === "success" || record[key] === "failure" || record[key] === "neutral";
}

function optionalExpect(record: Record<string, unknown>, key: string): boolean {
  return record[key] === undefined || record[key] === "zero" || record[key] === "nonzero" || record[key] === "any";
}

function isRisk(value: unknown): value is RiskLevel {
  return value === "low" || value === "standard" || value === "high";
}

function isRiskArray(value: unknown): value is RiskLevel[] {
  return isStringArray(value) && value.every(isRisk);
}

function isKind(value: unknown): value is WorkKind {
  return value === "new" || value === "feature" || value === "refactor" || value === "bug";
}

function isGate(value: unknown): value is GateName {
  return value === "scope" || value === "build" || value === "acceptance";
}

function isEvidenceStatus(value: unknown): value is "passed" | "failed" | "waived" {
  return value === "passed" || value === "failed" || value === "waived";
}

function isRevisionPhase(value: unknown): value is "requirements" | "design" | "implementation" {
  return value === "requirements" || value === "design" || value === "implementation";
}

function noExtraFields(record: Record<string, unknown>, fields: string[]): boolean {
  return Object.keys(record).every((key) => fields.includes(key));
}
