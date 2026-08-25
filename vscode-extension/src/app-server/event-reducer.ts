import { bounded, isRecord, type AppServerDiagnostic } from "./protocol";

export interface ProjectedItem {
  id: string;
  type: string;
  status: string;
  authoritative: boolean;
  content?: string;
  hasPrivateContent?: boolean;
}

export interface AppServerProjection {
  connection: "disconnected" | "connecting" | "connected" | "failed";
  threadId?: string;
  turnId?: string;
  threadStatus: string;
  turnStatus: string;
  plan: unknown[];
  diff: string;
  items: Record<string, ProjectedItem>;
  usage: { inputTokens: number; outputTokens: number; totalTokens: number } | null;
  mcpStatus: Record<string, unknown> | null;
  diagnostics: AppServerDiagnostic[];
}

export function initialProjection(): AppServerProjection {
  return {
    connection: "disconnected",
    threadStatus: "unknown",
    turnStatus: "idle",
    plan: [],
    diff: "",
    items: {},
    usage: null,
    mcpStatus: null,
    diagnostics: []
  };
}

export function reduceAppServerEvent(
  current: AppServerProjection,
  method: string,
  params: unknown
): AppServerProjection {
  const state = cloneProjection(current);
  const value = isRecord(params) ? params : {};
  switch (method) {
    case "thread/started":
      state.threadId = stringField(value, "threadId", "thread_id") ?? state.threadId;
      state.threadStatus = "active";
      return state;
    case "thread/status/changed":
      state.threadStatus = bounded(value.status ?? "unknown", 128);
      return state;
    case "turn/started":
      state.turnId = stringField(value, "turnId", "turn_id") ?? state.turnId;
      state.turnStatus = "active";
      return state;
    case "turn/completed":
      state.turnStatus = bounded(value.status ?? "completed", 128);
      return state;
    case "turn/plan/updated":
      state.plan = Array.isArray(value.plan) ? structuredClone(value.plan).slice(0, 256) : [];
      return state;
    case "turn/diff/updated":
      state.diff = bounded(value.diff ?? value.patch ?? "", 262_144);
      return state;
    case "item/started":
      return projectStartedItem(state, value);
    case "item/agentMessage/delta":
    case "item/commandExecution/outputDelta":
    case "item/fileChange/outputDelta":
      return projectDelta(state, value);
    case "item/completed":
      return projectCompletedItem(state, value);
    case "thread/tokenUsage/updated":
    case "turn/usage/updated":
      state.usage = projectUsage(value);
      return state;
    case "mcpServer/startupStatus/updated":
      state.mcpStatus = safeRecord(value);
      return state;
    case "configWarning":
    case "warning":
    case "error":
      return addDiagnostic(state, method === "error" ? "app_server_error" : "app_server_warning", value.message ?? value);
    default:
      return addDiagnostic(state, "unsupported_event", method);
  }
}

export function addDiagnostic(state: AppServerProjection, code: string, message: unknown): AppServerProjection {
  const next = cloneProjection(state);
  next.diagnostics.push({ code, message: bounded(message, 4_096) });
  next.diagnostics = next.diagnostics.slice(-100);
  return next;
}

function projectStartedItem(state: AppServerProjection, value: Record<string, unknown>): AppServerProjection {
  const item = isRecord(value.item) ? value.item : value;
  const id = stringField(item, "id", "itemId", "item_id");
  if (!id) return addDiagnostic(state, "malformed_item", "item/started lacks an id");
  const type = bounded(item.type ?? "unknown", 128);
  state.items[id] = {
    id,
    type,
    status: bounded(item.status ?? "in_progress", 128),
    authoritative: false,
    ...(type === "reasoning" ? { hasPrivateContent: true } : {})
  };
  return state;
}

function projectDelta(state: AppServerProjection, value: Record<string, unknown>): AppServerProjection {
  const id = stringField(value, "itemId", "item_id", "id");
  if (!id) return addDiagnostic(state, "malformed_delta", "item delta lacks an id");
  const existing = state.items[id] ?? { id, type: "agentMessage", status: "in_progress", authoritative: false };
  if (existing.type === "reasoning" || existing.authoritative) return state;
  existing.content = bounded(`${existing.content ?? ""}${typeof value.delta === "string" ? value.delta : ""}`, 262_144);
  state.items[id] = existing;
  return state;
}

function projectCompletedItem(state: AppServerProjection, value: Record<string, unknown>): AppServerProjection {
  const item = isRecord(value.item) ? value.item : value;
  const id = stringField(item, "id", "itemId", "item_id");
  if (!id) return addDiagnostic(state, "malformed_item", "item/completed lacks an id");
  const type = bounded(item.type ?? state.items[id]?.type ?? "unknown", 128);
  if (type === "reasoning") {
    state.items[id] = {
      id,
      type,
      status: bounded(item.status ?? "completed", 128),
      authoritative: true,
      hasPrivateContent: true
    };
    return state;
  }
  const content = extractDisplayContent(item);
  state.items[id] = {
    id,
    type,
    status: bounded(item.status ?? "completed", 128),
    authoritative: true,
    ...(content ? { content } : {})
  };
  return state;
}

function extractDisplayContent(item: Record<string, unknown>): string {
  for (const key of ["content", "text", "output", "message"]) {
    if (typeof item[key] === "string") return bounded(item[key], 262_144);
  }
  return "";
}

function projectUsage(value: Record<string, unknown>): AppServerProjection["usage"] {
  const usage = isRecord(value.usage) ? value.usage : value;
  const input = numberField(usage, "inputTokens", "input_tokens");
  const output = numberField(usage, "outputTokens", "output_tokens");
  const total = numberField(usage, "totalTokens", "total_tokens");
  if (input === undefined || output === undefined || total === undefined) return null;
  return { inputTokens: input, outputTokens: output, totalTokens: total };
}

function stringField(value: Record<string, unknown>, ...keys: string[]): string | undefined {
  for (const key of keys) if (typeof value[key] === "string") return bounded(value[key], 256);
  return undefined;
}

function numberField(value: Record<string, unknown>, ...keys: string[]): number | undefined {
  for (const key of keys) {
    const candidate = value[key];
    if (typeof candidate === "number" && Number.isSafeInteger(candidate) && candidate >= 0) return candidate;
  }
  return undefined;
}

function safeRecord(value: Record<string, unknown>): Record<string, unknown> {
  return JSON.parse(JSON.stringify(value)) as Record<string, unknown>;
}

function cloneProjection(value: AppServerProjection): AppServerProjection {
  return {
    ...value,
    plan: structuredClone(value.plan),
    items: structuredClone(value.items),
    usage: value.usage ? { ...value.usage } : null,
    mcpStatus: value.mcpStatus ? structuredClone(value.mcpStatus) : null,
    diagnostics: value.diagnostics.map((item) => ({ ...item }))
  };
}
