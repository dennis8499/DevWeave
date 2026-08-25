export const APP_SERVER_METHODS = [
  "thread/start",
  "thread/resume",
  "thread/read",
  "turn/start",
  "turn/steer",
  "turn/interrupt",
  "review/start",
  "mcpServerStatus/list",
  "config/mcpServer/reload"
] as const;

export type AppServerMethod = typeof APP_SERVER_METHODS[number];

export const SERVER_REQUEST_METHODS = [
  "item/commandExecution/requestApproval",
  "item/fileChange/requestApproval"
] as const;

export type ServerRequestMethod = typeof SERVER_REQUEST_METHODS[number];

export interface JsonRpcRequest {
  id: number;
  method: string;
  params: unknown;
}

export interface JsonRpcNotification {
  method: string;
  params?: unknown;
}

export interface AppServerDiagnostic {
  code: string;
  message: string;
}

export class AppServerError extends Error {
  public constructor(public readonly code: string, message: string) {
    super(message);
    this.name = "AppServerError";
  }
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function bounded(value: unknown, maximum = 8_192): string {
  const text = typeof value === "string" ? value : JSON.stringify(value ?? "");
  const redacted = text
    .replace(/\b(api[_-]?key|access[_-]?token|authorization|password|secret)\b\s*[:=]\s*[^\s,;]+/gi, "$1=<redacted>")
    .replace(/\b(?:sk|sess|token)-[A-Za-z0-9_-]{8,}\b/g, "<redacted>");
  return redacted.length <= maximum ? redacted : `${redacted.slice(0, maximum - 22)}<diagnostic-truncated>`;
}
