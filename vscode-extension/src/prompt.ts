import { PublicCommandIntent, PublicCommandName, PromptBundle, WorkspaceSnapshot } from "./model";

export interface PromptComposer {
  compose(intent: PublicCommandIntent, snapshot: WorkspaceSnapshot): PromptBundle;
}

export class DevWeavePromptComposer implements PromptComposer {
  public compose(intent: PublicCommandIntent, snapshot: WorkspaceSnapshot): PromptBundle {
    const warnings = snapshot.diagnostics
      .filter((item) => item.severity !== "info")
      .map((item) => `${item.code}: ${item.message}`);
    const mutation = this.isMutation(intent);
    if (mutation) {
      warnings.push("此 Extension 不會執行或寫入；請先審閱，再將 public prompt 貼入 Codex Chat 送出。");
    }
    if (this.isApproval(intent)) {
      warnings.push("這是人工核准操作；複製不代表核准，送出前請確認目前 validation summary。");
    }
    for (const value of stringValues(intent)) {
      if (containsUnsafePath(value)) {
        warnings.push("已將 absolute/traversal path 從 prompt 參數遮罩；DevWeave 僅接受 repository-relative path。");
        break;
      }
    }
    if (stringValues(intent).some(isCredentialLike)) {
      warnings.push("已將 credential-like input 遮罩；請不要把 secrets 貼入 Codex Chat。");
    }

    if (mutation && snapshot.mutationBlocked) {
      warnings.push("目前 snapshot 含有 critical contract diagnostic；mutation public prompt 已停用，請先使用 status command 或修復/確認 diagnostic。");
      throw new Error(`DevWeave read-only diagnostic state: ${warnings.join(" ")}`);
    }

    const chatText = this.commandFor(intent);
    const workId = "workId" in intent ? intent.workId : undefined;
    return {
      chatText,
      command: intent.type,
      ...(workId === undefined ? {} : { workId }),
      warnings,
      mutation
    };
  }

  private commandFor(intent: PublicCommandIntent): string {
    switch (intent.type) {
      case "new":
        return `$devweave new ${requiredArg(intent.goal, "goal")}`;
      case "feature":
        return `$devweave feature ${requiredArg(intent.request, "request")}`;
      case "refactor":
        return `$devweave refactor ${requiredArg(intent.request, "request")}`;
      case "bug":
        return `$devweave bug ${requiredArg(intent.symptom, "symptom")}`;
      case "next":
        return `$devweave next${optionalArg(intent.workId)}`;
      case "status":
        return `$devweave status${optionalArg(intent.workId)}`;
      case "revise":
        return `$devweave revise ${requiredArg(intent.workId, "workId")} ${requiredArg(intent.change, "change")}`;
      case "approve":
        return `$devweave approve ${requiredArg(intent.workId, "workId")}`;
    }
  }

  private isMutation(intent: PublicCommandIntent): boolean {
    return ["new", "feature", "refactor", "bug", "revise", "approve"].includes(intent.type);
  }

  private isApproval(intent: PublicCommandIntent): boolean {
    return intent.type === "approve" || intent.type === "revise";
  }
}

function requiredArg(value: string, name: string): string {
  const sanitized = chatArg(value);
  if (!sanitized) {
    throw new Error(`Public command ${name} is required.`);
  }
  return sanitized;
}

function optionalArg(value: string | undefined): string {
  if (value === undefined) {
    return "";
  }
  return ` ${requiredArg(value, "workId")}`;
}

function sanitize(value: string): string {
  if (isUnsafePath(value)) {
    return "[absolute-path-redacted]";
  }
  return value
    .replace(/[\r\n\u0000]/g, " ")
    .replace(/[;&|<>]/g, " ")
    .replace(/\b[A-Za-z]:[\\/][^\s"']+/g, "[absolute-path-redacted]")
    .replace(/(^|[\s(])\/(?:Users|home|private|tmp|var|workspace)[^\s"']*/g, "$1[absolute-path-redacted]")
    .replace(/\b(?:sk-[A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9_]{10,}|xox[baprs]-[A-Za-z0-9-]{10,})\b/g, "[secret-redacted]")
    .trim();
}

function chatArg(value: string): string {
  return sanitize(value).replace(/\s+/g, " ");
}

function isUnsafePath(value: string): boolean {
  const normalized = value.replaceAll("\\", "/");
  return /^[A-Za-z]:\//.test(normalized) || normalized.startsWith("/") || normalized.split("/").includes("..");
}

function containsUnsafePath(value: string): boolean {
  return isUnsafePath(value) || /\b[A-Za-z]:[\\/]/.test(value) || /(^|[\s(])\/(?:Users|home|private|tmp|var|workspace)(?:[\s/]|$)/.test(value);
}

function isCredentialLike(value: string): boolean {
  return /\b(?:sk-[A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9_]{10,}|xox[baprs]-[A-Za-z0-9-]{10,})\b/.test(value);
}

function stringValues(value: unknown): string[] {
  if (typeof value === "string") {
    return [value];
  }
  if (Array.isArray(value)) {
    return value.flatMap(stringValues);
  }
  if (value && typeof value === "object") {
    return Object.values(value).flatMap(stringValues);
  }
  return [];
}
