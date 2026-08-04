import type { DashboardPreferences, DisplayMode, PublicCommandIntent, PromptBundle, WorkspaceSnapshot } from "./model";
import type { BootstrapReport } from "./bootstrap";

export type WebviewToHostMessage =
  | { type: "refresh" }
  | { type: "initialize" }
  | { type: "selectWork"; workId: string | null }
  | { type: "setDisplayMode"; mode: DisplayMode }
  | { type: "openFile"; path: string }
  | { type: "previewAction"; intent: PublicCommandIntent }
  | { type: "copyAction"; intent: PublicCommandIntent };

export type HostToWebviewMessage =
  | { type: "snapshot"; snapshot: WorkspaceSnapshot; preferences?: DashboardPreferences }
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
      return noExtraFields(record, ["type"]) ? { type: "refresh" } : null;
    case "initialize":
      return noExtraFields(record, ["type"]) ? { type: "initialize" } : null;
    case "selectWork":
      return noExtraFields(record, ["type", "workId"]) && (record.workId === null || typeof record.workId === "string")
        ? { type: "selectWork", workId: record.workId }
        : null;
    case "setDisplayMode":
      return noExtraFields(record, ["type", "mode"]) && isDisplayMode(record.mode)
        ? { type: "setDisplayMode", mode: record.mode }
        : null;
    case "openFile":
      return noExtraFields(record, ["type", "path"]) && typeof record.path === "string"
        ? { type: "openFile", path: record.path }
        : null;
    case "copyAction": {
      const intent = parsePublicCommandIntent(record.intent);
      return intent && noExtraFields(record, ["type", "intent"]) ? { type: "copyAction", intent } : null;
    }
    case "previewAction": {
      const intent = parsePublicCommandIntent(record.intent);
      return intent && noExtraFields(record, ["type", "intent"]) ? { type: "previewAction", intent } : null;
    }
    default:
      return null;
  }
}

export function parsePublicCommandIntent(value: unknown): PublicCommandIntent | null {
  const record = asRecord(value);
  if (!record || typeof record.type !== "string") {
    return null;
  }
  switch (record.type) {
    case "new":
      return noExtraFields(record, ["type", "goal"]) && isNonEmptyString(record.goal)
        ? { type: "new", goal: record.goal }
        : null;
    case "feature":
      return noExtraFields(record, ["type", "request"]) && isNonEmptyString(record.request)
        ? { type: "feature", request: record.request }
        : null;
    case "refactor":
      return noExtraFields(record, ["type", "request"]) && isNonEmptyString(record.request)
        ? { type: "refactor", request: record.request }
        : null;
    case "bug":
      return noExtraFields(record, ["type", "symptom"]) && isNonEmptyString(record.symptom)
        ? { type: "bug", symptom: record.symptom }
        : null;
    case "next":
      return noExtraFields(record, ["type", "workId"]) && optionalWorkId(record)
        ? { type: "next", ...(record.workId === undefined ? {} : { workId: record.workId as string }) }
        : null;
    case "status":
      return noExtraFields(record, ["type", "workId"]) && optionalWorkId(record)
        ? { type: "status", ...(record.workId === undefined ? {} : { workId: record.workId as string }) }
        : null;
    case "wikiBootstrap":
      return noExtraFields(record, ["type"]) ? { type: "wikiBootstrap" } : null;
    case "revise":
      return noExtraFields(record, ["type", "workId", "change"]) && isNonEmptyString(record.workId) && isNonEmptyString(record.change)
        ? { type: "revise", workId: record.workId, change: record.change }
        : null;
    case "approve":
      return noExtraFields(record, ["type", "workId"]) && isNonEmptyString(record.workId)
        ? { type: "approve", workId: record.workId }
        : null;
    default:
      return null;
  }
}

// Compatibility export for extension-local callers; it now accepts public intents only.
export const parseActionIntent = parsePublicCommandIntent;

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function optionalWorkId(record: Record<string, unknown>): boolean {
  return record.workId === undefined || isNonEmptyString(record.workId);
}

function isDisplayMode(value: unknown): value is DisplayMode {
  return value === "concise" || value === "advanced";
}

function noExtraFields(record: Record<string, unknown>, fields: string[]): boolean {
  return Object.keys(record).every((key) => fields.includes(key));
}
