import { ActionIntent, GateName, PromptBundle, WorkspaceSnapshot } from "./model";

export interface PromptComposer {
  compose(intent: ActionIntent, snapshot: WorkspaceSnapshot): PromptBundle;
}

const ENGINE = "python -B .agents/skills/devweave/scripts/devweave.py --repo .";

export class DevWeavePromptComposer implements PromptComposer {
  public compose(intent: ActionIntent, snapshot: WorkspaceSnapshot): PromptBundle {
    const warnings = snapshot.diagnostics
      .filter((item) => item.severity !== "info")
      .map((item) => `${item.code}: ${item.message}`);
    const mutation = this.isMutation(intent);
    if (mutation) {
      warnings.push("此 Extension 不會執行或寫入；請先審閱，再將 prompt 貼入 Codex Chat 送出。");
    }
    if (this.isApproval(intent)) {
      warnings.push("這是人工 gate 操作；複製不代表核准，送出前請確認目前 validation summary。");
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

    const workId = "workId" in intent ? intent.workId : undefined;
    const command = this.commandFor(intent);
    const targetPaths = this.targetsFor(intent);
    const mutationBlocked = mutation && snapshot.mutationBlocked;
    if (mutationBlocked) {
      warnings.push("目前 snapshot 含有 critical contract diagnostic；mutation prompt 已停用，請先在 Codex Chat 執行 doctor/status 修復或確認。");
    }
    const chatText = mutationBlocked
      ? this.blockedChatText(intent, warnings)
      : this.chatTextFor(intent, command, workId);
    return {
      chatText,
      machineCommand: mutationBlocked ? undefined : command,
      workId,
      gate: this.gateFor(intent),
      targetPaths,
      warnings,
      mutation
    };
  }

  private blockedChatText(intent: ActionIntent, warnings: string[]): string {
    return [
      "目前 repository 進入 DevWeave read-only diagnostic state，無法產生或執行 mutation action。",
      "",
      `Requested action: ${intent.type}`,
      "",
      ...warnings.map((warning) => `- ${warning}`),
      "",
      "請先在 Codex Chat 送出 doctor/status，修復或確認 contract diagnostic，再重新整理 Extension。"
    ].join("\n");
  }

  private commandFor(intent: ActionIntent): string {
    switch (intent.type) {
      case "init":
        return `${ENGINE} init`;
      case "doctor":
        return `${ENGINE} doctor`;
      case "project":
        return `${ENGINE} project`;
      case "commandList":
        return `${ENGINE} command list`;
      case "commandSet":
        return `${ENGINE} command set --id ${arg(intent.id)} --cwd ${arg(intent.cwd)} --timeout ${intent.timeout}${optionList("--required-for", intent.requiredFor)} -- ${intent.argv.map(arg).join(" ")}`;
      case "commandRemove":
        return `${ENGINE} command remove --id ${arg(intent.id)}`;
      case "start":
        return `${ENGINE} start --kind ${arg(intent.kind)} --title ${arg(intent.title)} --risk ${arg(intent.risk)} --rationale ${arg(intent.rationale)}`;
      case "status":
        return `${ENGINE} status${intent.workId ? ` --work ${arg(intent.workId)}` : ""}${intent.all ? " --all" : ""}`;
      case "instructions":
        return `${ENGINE} instructions --work ${arg(intent.workId)}`;
      case "validate":
        return `${ENGINE} validate --work ${arg(intent.workId)}${intent.gate ? ` --gate ${arg(intent.gate)}` : ""}`;
      case "bind":
        return `${ENGINE} bind --work ${arg(intent.workId)}`;
      case "risk":
        return `${ENGINE} risk --work ${arg(intent.workId)} --level ${arg(intent.level)} --rationale ${arg(intent.rationale)}${intent.downgradeRationale ? ` --downgrade-rationale ${arg(intent.downgradeRationale)}` : ""}`;
      case "scope":
        return `${ENGINE} scope --work ${arg(intent.workId)} ${canonicalList(intent.paths).flatMap((path) => ["--path", arg(path)]).join(" ")} --rationale ${arg(intent.rationale)}`;
      case "baseline":
        return `${ENGINE} baseline --work ${arg(intent.workId)} ${canonicalList(intent.targets).flatMap((path) => ["--target", arg(path)]).join(" ")} --rationale ${arg(intent.rationale)}`;
      case "knowledgeStatus":
        return `${ENGINE} knowledge status${intent.workId ? ` --work ${arg(intent.workId)}` : ""}`;
      case "knowledgeContext":
        return `${ENGINE} knowledge context --work ${arg(intent.workId)} ${intent.pages.flatMap((page) => ["--page", arg(page)]).join(" ")}${intent.gaps.map((gap) => ` --gap ${arg(gap)}`).join("")}`;
      case "knowledgePlan":
        return `${ENGINE} knowledge plan --work ${arg(intent.workId)}${intent.upserts.map((page) => ` --upsert ${arg(page)}`).join("")}${intent.deletes.map((page) => ` --delete ${arg(page)}`).join("")} --rationale ${arg(intent.rationale)}`;
      case "knowledgeSeal":
        return `${ENGINE} knowledge seal --work ${arg(intent.workId)}${intent.pages.map((page) => ` --page ${arg(page)}`).join("")}`;
      case "taskStart":
        return `${ENGINE} task start --work ${arg(intent.workId)} --task ${arg(intent.taskId)}`;
      case "taskComplete":
        return `${ENGINE} task complete --work ${arg(intent.workId)} --task ${arg(intent.taskId)}${(intent.evidence ?? []).map((id) => ` --evidence ${arg(id)}`).join("")}${intent.note ? ` --note ${arg(intent.note)}` : ""}`;
      case "taskBlock":
        return `${ENGINE} task block --work ${arg(intent.workId)} --task ${arg(intent.taskId)} --note ${arg(intent.note)}`;
      case "evidenceAdd":
        return `${ENGINE} evidence add --work ${arg(intent.workId)} --kind ${arg(intent.kind)} --status ${arg(intent.status)} --summary ${arg(intent.summary)}${intent.covers.map((id) => ` --covers ${arg(id)}`).join("")}${intent.tasks.map((id) => ` --task ${arg(id)}`).join("")}${intent.observedResult ? ` --observed-result ${arg(intent.observedResult)}` : ""}${intent.bindsCurrentSource === true ? " --binds-current-source" : intent.bindsCurrentSource === false ? " --does-not-bind-current-source" : ""}`;
      case "verify":
        return `${ENGINE} verify --work ${arg(intent.workId)} --command ${arg(intent.command)} --kind ${arg(intent.kind)}${intent.covers.map((id) => ` --covers ${arg(id)}`).join("")}${intent.tasks.map((id) => ` --task ${arg(id)}`).join("")}${intent.expect ? ` --expect ${arg(intent.expect)}` : ""}`;
      case "waiverAdd":
        return `${ENGINE} waiver add --work ${arg(intent.workId)} --kind ${arg(intent.kind)} --target ${arg(intent.target)} --reason ${arg(intent.reason)}${intent.gate ? ` --gate ${arg(intent.gate)}` : ""}`;
      case "approve":
        return `${ENGINE} approve --work ${arg(intent.workId)}${intent.gate ? ` --gate ${arg(intent.gate)}` : ""}`;
      case "revise":
        return `${ENGINE} revise --work ${arg(intent.workId)} --from ${arg(intent.from)} --reason ${arg(intent.reason)}`;
      case "close":
        return `${ENGINE} close --work ${arg(intent.workId)}`;
    }
  }

  private chatTextFor(intent: ActionIntent, command: string, workId?: string): string {
    const publicCommand = this.publicChatCommand(intent, workId);
    const heading = publicCommand ?? "請在目前 repository 依照 DevWeave contract 執行以下操作";
    const goal = intent.type === "init" && intent.goal ? `\nInitialization goal: ${chatArg(intent.goal)}\n` : "";
    return [
      heading,
      goal,
      "",
      "請保留既有 DevWeave engine、hook、人工 gate 與 scope policy；不要猜測缺失狀態，也不要執行未列出的 mutation。",
      "",
      "```text",
      command,
      "```",
      "",
      "完成後請回報 JSON 結果、validation/errors、phase/gate 變化與需要使用者確認的事項。"
    ].join("\n");
  }

  private publicChatCommand(intent: ActionIntent, workId?: string): string | null {
    switch (intent.type) {
      case "start":
        return `$devweave ${intent.kind === "new" ? "new" : intent.kind} ${chatArg(intent.title)}`;
      case "status":
        return `$devweave status${workId ? ` ${chatArg(workId)}` : ""}`;
      case "instructions":
        return `$devweave next ${chatArg(intent.workId)}`;
      case "approve":
        return `$devweave approve ${chatArg(intent.workId)}`;
      case "revise":
        return `$devweave revise ${chatArg(intent.workId)} ${chatArg(intent.reason)}`;
      default:
        return null;
    }
  }

  private targetsFor(intent: ActionIntent): string[] {
    switch (intent.type) {
      case "scope":
        return canonicalList(intent.paths).map(displayPath);
      case "baseline":
        return canonicalList(intent.targets).map(displayPath);
      case "knowledgeContext":
      case "knowledgeSeal":
        return intent.pages.map(displayPath);
      case "knowledgePlan":
        return [...intent.upserts, ...intent.deletes].map(displayPath);
      case "commandSet":
        return [".devweave/project.json"];
      case "commandRemove":
        return [".devweave/project.json"];
      case "init":
        return [".devweave/project.json", ".devweave/baseline/", "wiki/"];
      case "status":
      case "knowledgeStatus":
      case "doctor":
      case "project":
      case "commandList":
        return [];
      case "instructions":
      case "validate":
      case "bind":
      case "risk":
      case "taskStart":
      case "taskComplete":
      case "taskBlock":
      case "evidenceAdd":
      case "verify":
      case "waiverAdd":
      case "approve":
      case "revise":
      case "close":
        return workTargets(intent.workId);
      default:
        return [];
    }
  }

  private gateFor(intent: ActionIntent): GateName | undefined {
    if (intent.type === "approve") {
      return intent.gate;
    }
    if (intent.type === "validate") {
      return intent.gate;
    }
    if (intent.type === "waiverAdd") {
      return intent.gate;
    }
    if (intent.type === "baseline" || intent.type === "knowledgePlan" || intent.type === "knowledgeSeal" || intent.type === "close") {
      return "acceptance";
    }
    return undefined;
  }

  private isMutation(intent: ActionIntent): boolean {
    return !["doctor", "project", "commandList", "status", "instructions", "validate", "knowledgeStatus"].includes(intent.type);
  }

  private isApproval(intent: ActionIntent): boolean {
    return ["approve", "baseline", "close", "waiverAdd", "revise", "knowledgePlan", "knowledgeSeal"].includes(intent.type);
  }
}

function arg(value: string): string {
  const safe = sanitize(value);
  return JSON.stringify(safe);
}

function optionList(name: string, values: string[]): string {
  const items = canonicalList(values);
  return items.length ? ` ${name} ${items.map(arg).join(" ")}` : "";
}

function workTargets(workId: string): string[] {
  const safeId = isUnsafePath(workId) ? "[invalid-work-id]" : workId;
  return [`.devweave/work-items/${safeId}/state.json`, `.devweave/work-items/${safeId}/events.jsonl`];
}

function canonicalList(values: string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b));
}

function displayPath(value: string): string {
  return isUnsafePath(value) ? "[invalid-repo-relative-path]" : value.replaceAll("\\", "/");
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
