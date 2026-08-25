import { resolve, relative, isAbsolute } from "node:path";

import type { ServerRequest } from "../app-server/session";

export type ApprovalDecision = "accept" | "decline" | "cancel";

export interface ApprovalAssessment {
  eligible: boolean;
  reason: string;
  paths: string[];
  readOnly: boolean;
}

const READ_ONLY_COMMANDS = new Set([
  "git status", "git diff", "git log", "git show", "git rev-parse",
  "rg", "git grep", "get-content"
]);

const FORBIDDEN_COMMANDS = /\b(?:git\s+(?:push|pull|merge|reset|checkout)|rm\b|rmdir\b|remove-item\b|del\b)/i;

export class ApprovalBroker {
  public constructor(private readonly repository: string) {}

  public assess(request: ServerRequest, run: Record<string, unknown>): ApprovalAssessment {
    const phase = typeof run.phase === "string" ? run.phase : "planning";
    if (request.method === "item/fileChange/requestApproval") {
      const paths = extractPaths(request.params);
      if (!new Set(["implementation", "review"]).has(phase)) {
        return { eligible: false, reason: "File writes are blocked before implementation.", paths, readOnly: false };
      }
      if (!paths.length || !paths.every((path) => this.inScope(path, run))) {
        return { eligible: false, reason: "File request is outside the current task scope.", paths, readOnly: false };
      }
      return { eligible: true, reason: "File request is within the current task scope.", paths, readOnly: false };
    }
    const command = extractCommand(request.params);
    const readOnly = [...READ_ONLY_COMMANDS].some((prefix) => command.toLowerCase().startsWith(prefix));
    if (FORBIDDEN_COMMANDS.test(command)) {
      return { eligible: false, reason: "Command is outside DevWeave Git/destructive policy.", paths: [], readOnly };
    }
    if (!new Set(["implementation", "review"]).has(phase) && !readOnly) {
      return { eligible: false, reason: "Only read-only commands are eligible before planning gates.", paths: [], readOnly };
    }
    return { eligible: true, reason: readOnly ? "Read-only command is eligible for user review." : "Command requires explicit user review.", paths: [], readOnly };
  }

  public assertDecision(assessment: ApprovalAssessment, decision: ApprovalDecision): void {
    if (decision === "accept" && !assessment.eligible) {
      throw new Error("Ineligible approval request cannot be accepted.");
    }
  }

  private inScope(candidate: string, run: Record<string, unknown>): boolean {
    if (!candidate || isAbsolute(candidate) || candidate.replaceAll("\\", "/").split("/").includes("..")) return false;
    const absolute = resolve(this.repository, candidate);
    const rel = relative(this.repository, absolute).replaceAll("\\", "/");
    if (!rel || rel.startsWith("../") || isAbsolute(rel)) return false;
    const declarations = currentDeclarations(run);
    return declarations.some((pattern) => matches(rel, pattern));
  }
}

function currentDeclarations(run: Record<string, unknown>): string[] {
  const tasks = record(run.tasks);
  const task = Object.values(tasks).find((value) => record(value).status === "in_progress");
  const definition = record(record(task).definition);
  const declared = Array.isArray(definition.declared_paths) ? definition.declared_paths.filter((item): item is string => typeof item === "string") : [];
  if (declared.length) return declared;
  const plan = record(run.plan);
  return Array.isArray(plan.scope) ? plan.scope.filter((item): item is string => typeof item === "string") : [];
}

function extractPaths(params: unknown): string[] {
  const value = record(params);
  const direct = typeof value.path === "string" ? [value.path] : [];
  const changes = Array.isArray(value.changes)
    ? value.changes.map((item) => record(item).path).filter((item): item is string => typeof item === "string")
    : [];
  return [...new Set([...direct, ...changes])];
}

function extractCommand(params: unknown): string {
  const value = record(params);
  if (Array.isArray(value.command)) return value.command.filter((item): item is string => typeof item === "string").join(" ");
  return typeof value.command === "string" ? value.command : "";
}

function matches(path: string, pattern: string): boolean {
  const normalized = pattern.replaceAll("\\", "/");
  if (normalized.endsWith("/**")) return path === normalized.slice(0, -3) || path.startsWith(normalized.slice(0, -2));
  if (normalized.endsWith("/*")) return path.startsWith(normalized.slice(0, -1)) && !path.slice(normalized.length - 1).includes("/");
  return path === normalized;
}

function record(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
