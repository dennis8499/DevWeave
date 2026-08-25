import type { ApprovalDecision } from "../controller/approval-broker";

export type UiIntent =
  | { type: "start"; goal: string; scope: string; risk: "low" | "standard" | "high" }
  | { type: "resume"; runId: string; threadId?: string }
  | { type: "turn"; text: string }
  | { type: "steer"; text: string }
  | { type: "interrupt" }
  | { type: "cancel" }
  | { type: "decision"; decisionId: string; optionId?: string; other?: string }
  | { type: "gate"; gateId: string; approve: boolean }
  | { type: "approval"; requestId: string | number; decision: ApprovalDecision }
  | { type: "review" }
  | { type: "refresh" };

export function parseUiIntent(value: unknown): UiIntent | null {
  if (!record(value) || typeof value.type !== "string") return null;
  const keys = Object.keys(value).sort().join(",");
  switch (value.type) {
    case "start":
      if (keys !== "goal,risk,scope,type" || !text(value.goal, 8_192) || !text(value.scope, 512) || !["low", "standard", "high"].includes(String(value.risk))) return null;
      return { type: "start", goal: value.goal, scope: value.scope, risk: value.risk as "low" | "standard" | "high" };
    case "resume":
      if (!allowedKeys(value, ["type", "runId", "threadId"], ["type", "runId"]) || !text(value.runId, 128) || (value.threadId !== undefined && !text(value.threadId, 256))) return null;
      return { type: "resume", runId: value.runId, ...(typeof value.threadId === "string" ? { threadId: value.threadId } : {}) };
    case "turn":
    case "steer":
      return keys === "text,type" && text(value.text, 32_768) ? { type: value.type, text: value.text } : null;
    case "interrupt":
    case "cancel":
    case "review":
    case "refresh":
      return keys === "type" ? { type: value.type } : null;
    case "decision":
      if (!allowedKeys(value, ["type", "decisionId", "optionId", "other"], ["type", "decisionId"]) || !text(value.decisionId, 128)) return null;
      if ((typeof value.optionId === "string") === (typeof value.other === "string")) return null;
      return { type: "decision", decisionId: value.decisionId, ...(typeof value.optionId === "string" ? { optionId: value.optionId } : { other: value.other as string }) };
    case "gate":
      return keys === "approve,gateId,type" && text(value.gateId, 128) && typeof value.approve === "boolean"
        ? { type: "gate", gateId: value.gateId, approve: value.approve }
        : null;
    case "approval":
      return keys === "decision,requestId,type"
        && (typeof value.requestId === "string" || typeof value.requestId === "number")
        && ["accept", "decline", "cancel"].includes(String(value.decision))
        ? { type: "approval", requestId: value.requestId, decision: value.decision as ApprovalDecision }
        : null;
    default:
      return null;
  }
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function text(value: unknown, maximum: number): value is string {
  return typeof value === "string" && value.trim().length > 0 && value.length <= maximum;
}

function allowedKeys(value: Record<string, unknown>, allowed: string[], required: string[]): boolean {
  return Object.keys(value).every((key) => allowed.includes(key)) && required.every((key) => key in value);
}
