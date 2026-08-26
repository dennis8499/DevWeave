import { isAbsolute } from "node:path";

import type { ServerRequest } from "../app-server/session";
import { currentDeclarations, isTaskPathInScope } from "./task-scope";

export { currentDeclarations } from "./task-scope";

export type ApprovalDecision = "accept" | "decline" | "cancel";

export interface ApprovalAssessment {
  eligible: boolean;
  reason: string;
  paths: string[];
  readOnly: boolean;
}

const READ_ONLY_GIT = new Set(["status", "rev-parse"]);
const DANGEROUS_GIT_OPTIONS = new Set([
  "--config-env", "--exec-path", "--ext-diff", "--no-index", "--output", "--paginate",
  "--recurse-submodules", "--submodule", "--textconv", "-c", "-p"
]);
const SHELL_SYNTAX = /[;&|><`\r\n]|\$\(|\$\{|%[^%]+%/;

export class ApprovalBroker {
  public constructor(private readonly repository: string) {}

  public assess(request: ServerRequest, run: Record<string, unknown>): ApprovalAssessment {
    const phase = typeof run.phase === "string" ? run.phase : "planning";
    if (request.method === "item/fileChange/requestApproval") {
      const paths = extractPaths(request.params);
      if (phase !== "implementation" || currentDeclarations(run).length === 0) {
        return { eligible: false, reason: "File writes require exactly one in-progress implementation task.", paths, readOnly: false };
      }
      if (!paths.length || !paths.every((path) => isTaskPathInScope(this.repository, run, path))) {
        return { eligible: false, reason: "File request is outside the current task scope.", paths, readOnly: false };
      }
      return { eligible: true, reason: "File request is within the current task scope.", paths, readOnly: false };
    }
    const argv = extractArgv(request.params);
    const readOnly = argv !== null && safeReadOnlyCommand(argv);
    if (!readOnly) {
      return {
        eligible: false,
        reason: "Only structurally validated read-only argv commands are approval-eligible; run writers through governed MCP verification.",
        paths: [],
        readOnly: false
      };
    }
    return { eligible: true, reason: "Structurally validated read-only command is eligible for user review.", paths: [], readOnly: true };
  }

  public assertDecision(assessment: ApprovalAssessment, decision: ApprovalDecision): void {
    if (decision === "accept" && !assessment.eligible) {
      throw new Error("Ineligible approval request cannot be accepted.");
    }
  }
}

function extractPaths(params: unknown): string[] {
  const value = record(params);
  const direct = typeof value.path === "string" ? [value.path] : [];
  const changes = Array.isArray(value.changes)
    ? value.changes.map((item) => record(item).path).filter((item): item is string => typeof item === "string")
    : [];
  return [...new Set([...direct, ...changes])];
}

function extractArgv(params: unknown): string[] | null {
  const command = record(params).command;
  if (!Array.isArray(command) || command.length === 0 || !command.every((item) => typeof item === "string" && item.length > 0)) {
    return null;
  }
  return command;
}

function safeReadOnlyCommand(argv: string[]): boolean {
  if (argv.some((token) => SHELL_SYNTAX.test(token))) return false;
  const executable = argv[0].replaceAll("\\", "/").split("/").at(-1)?.toLowerCase();
  if (executable === "git" || executable === "git.exe") {
    if (argv.length < 2 || !READ_ONLY_GIT.has(argv[1].toLowerCase())) return false;
    return !argv.slice(2).some((token) => {
      const option = token.toLowerCase().split("=", 1)[0];
      const normalized = token.replaceAll("\\", "/");
      return DANGEROUS_GIT_OPTIONS.has(option)
        || isAbsolute(token)
        || normalized === ".."
        || normalized.startsWith("../")
        || normalized.includes("/../");
    });
  }
  if (executable === "rg" || executable === "rg.exe") {
    const safeOptions = new Set([
      "--", "--after-context", "--before-context", "--case-sensitive", "--context", "--count",
      "--files", "--fixed-strings", "--glob", "--hidden", "--ignore-case", "--json",
      "--line-number", "--max-count", "--no-ignore", "--quiet", "--type", "--type-not",
      "--word-regexp", "-a", "-b", "-c", "-f", "-g", "-i", "-m", "-n", "-q", "-s", "-t", "-w"
    ]);
    return !argv.slice(1).some((token) => {
      const option = token.toLowerCase().split("=", 1)[0];
      if (token.startsWith("-") && !safeOptions.has(option)) return true;
      const normalized = token.replaceAll("\\", "/");
      return isAbsolute(token) || normalized === ".." || normalized.startsWith("../") || normalized.includes("/../");
    });
  }
  return false;
}

function record(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
