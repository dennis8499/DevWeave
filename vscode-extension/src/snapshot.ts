import {
  ArtifactProjection,
  CommandProjection,
  Diagnostic,
  EvidenceProjection,
  GateName,
  GateProjection,
  KnowledgeProjection,
  TaskProjection,
  WaiverProjection,
  WikiPageProjection,
  WorkItemProjection,
  WorkspaceSnapshot
} from "./model";
import { DirectoryEntry, FileSystemPort, joinRelativePath } from "./filesystem";

const ARTIFACT_NAMES = ["brief.md", "requirements.md", "design.md", "plan.md", "acceptance.md"];
const MAX_EVENTS = 100;

export interface SnapshotReaderOptions {
  rootName: string | null;
  rootPath: string | null;
  now?: () => string;
}

export interface WorkspaceSnapshotReaderPort {
  readWorkspace(): Promise<WorkspaceSnapshot>;
}

export class WorkspaceSnapshotReader implements WorkspaceSnapshotReaderPort {
  public constructor(
    private readonly files: FileSystemPort,
    private readonly options: SnapshotReaderOptions
  ) {}

  public async readWorkspace(): Promise<WorkspaceSnapshot> {
    const diagnostics: Diagnostic[] = [];
    const capturedAt = (this.options.now ?? (() => new Date().toISOString()))();
    const projectPath = ".devweave/project.json";
    const projectExists = await this.files.exists(projectPath);
    const hooksPresent = await this.files.exists(".codex/hooks.json");
    const skillPresent = await this.files.exists(".agents/skills/devweave/SKILL.md");
    const baselineFiles = await this.files.exists(".devweave/baseline")
      ? await this.collectFiles(".devweave/baseline")
      : [];
    const knowledge = await this.readKnowledge("wiki", diagnostics);

    if (!projectExists) {
      diagnostics.push({
        severity: "warning",
        code: "project_missing",
        message: "DevWeave project configuration is not initialized.",
        path: projectPath
      });
      return {
        capturedAt,
        rootName: this.options.rootName,
        rootPath: this.options.rootPath,
        projectPath,
        projectExists: false,
        managed: null,
        schemaVersion: null,
        project: null,
        commands: [],
        verificationProfiles: {},
        baselineFiles,
        hookPresent: hooksPresent,
        skillPresent,
        workItems: [],
        knowledge,
        diagnostics,
        mutationBlocked: false,
        source: "filesystem",
        authoritative: false,
        engineObservedAt: null,
        selectedWorkId: null
      };
    }

    const projectRead = await this.safeReadJson(projectPath, diagnostics);
    const project = projectRead.value;
    if (!project) {
      diagnostics.push({
        severity: "critical",
        code: "project_invalid",
        message: "DevWeave project configuration could not be parsed.",
        path: projectPath
      });
    }
    const managed = typeof project?.managed === "boolean" ? project.managed : null;
    const schemaVersion = typeof project?.schema_version === "number" ? project.schema_version : null;
    if (managed === null) {
      diagnostics.push({
        severity: "critical",
        code: "managed_missing",
        message: "Project managed flag is missing or invalid.",
        path: projectPath
      });
    } else if (!managed) {
      diagnostics.push({
        severity: "info",
        code: "managed_disabled",
        message: "DevWeave is not managed; explicit activation is required."
      });
    }
    if (schemaVersion !== null && schemaVersion !== 1) {
      diagnostics.push({
        severity: "critical",
        code: "unsupported_schema",
        message: `Unsupported DevWeave project schema version: ${schemaVersion}.`,
        path: projectPath
      });
    }
    if (!hooksPresent) {
      diagnostics.push({
        severity: "warning",
        code: "hook_missing",
        message: "Codex repository hook is missing.",
        path: ".codex/hooks.json"
      });
    }
    if (!skillPresent) {
      diagnostics.push({
        severity: "warning",
        code: "skill_missing",
        message: "DevWeave skill is missing.",
        path: ".agents/skills/devweave/SKILL.md"
      });
    }

    const commands = this.readCommands(project, diagnostics);
    const verificationProfiles = isRecord(project?.verification_profiles)
      ? mapStringArrays(project.verification_profiles)
      : {};
    const workItems = await this.readWorkItems(knowledge, diagnostics);
    const mutationBlocked = diagnostics.some((item) => item.severity === "critical");
    const engineObservedAt = workItems
      .map((item) => item.updatedAt)
      .filter((value): value is string => Boolean(value))
      .sort()
      .at(-1) ?? null;

    return {
      capturedAt,
      rootName: this.options.rootName,
      rootPath: this.options.rootPath,
      projectPath,
      projectExists: true,
      managed,
      schemaVersion,
      project: project ?? null,
      commands,
      verificationProfiles,
      baselineFiles,
      hookPresent: hooksPresent,
      skillPresent,
      workItems,
      knowledge,
      diagnostics,
      mutationBlocked,
      source: "filesystem",
      authoritative: false,
      engineObservedAt,
      selectedWorkId: null
    };
  }

  private async readWorkItems(
    knowledge: KnowledgeProjection,
    diagnostics: Diagnostic[]
  ): Promise<WorkItemProjection[]> {
    if (!(await this.files.exists(".devweave/work-items"))) {
      return [];
    }
    const entries = await this.files.readDirectory(".devweave/work-items");
    const workItems: WorkItemProjection[] = [];
    for (const entry of entries.filter((item) => item.kind === "directory")) {
      const relativeRoot = joinRelativePath(".devweave/work-items", entry.name);
      const statePath = joinRelativePath(relativeRoot, "state.json");
      if (!(await this.files.exists(statePath))) {
        continue;
      }
      const read = await this.safeReadJson(statePath, diagnostics);
      if (!read.value) {
        diagnostics.push({
          severity: "critical",
          code: "work_invalid",
          message: `Work item state could not be parsed: ${entry.name}.`,
          path: statePath
        });
        continue;
      }
      workItems.push(await this.toWorkItem(entry.name, relativeRoot, read.value, knowledge, diagnostics));
    }
    return workItems.sort((a, b) => (b.updatedAt ?? "").localeCompare(a.updatedAt ?? ""));
  }

  private async toWorkItem(
    id: string,
    root: string,
    state: Record<string, unknown>,
    knowledge: KnowledgeProjection,
    diagnostics: Diagnostic[]
  ): Promise<WorkItemProjection> {
    const diagnosticStart = diagnostics.length;
    const stateReadOnly = this.validateWorkState(id, state, diagnostics);
    const artifacts: ArtifactProjection[] = [];
    for (const name of ARTIFACT_NAMES) {
      const path = joinRelativePath(root, name);
      if (await this.files.exists(path)) {
        const read = await this.files.readText(path);
        artifacts.push({ path, exists: true, text: read.text, truncated: read.truncated });
      } else {
        artifacts.push({ path, exists: false, text: "", truncated: false });
      }
    }
    const evidence = await this.readEvidence(root, diagnostics);
    const events = await this.readEvents(root);
    const waivers = Array.isArray(state.waivers) ? state.waivers.flatMap((raw): WaiverProjection[] => {
      if (!isRecord(raw)) {
        return [];
      }
      return [{
        kind: stringValue(raw.kind),
        target: stringValue(raw.target),
        reason: stringValue(raw.reason),
        gate: nullableString(raw.gate) ?? undefined,
        actor: nullableString(raw.actor) ?? undefined,
        createdAt: nullableString(raw.created_at) ?? undefined
      }];
    }) : [];
    const gates = normalizeGates(state.gates);
    const taskRecord = isRecord(state.tasks) ? state.tasks : {};
    const tasks = Object.entries(taskRecord).map(([taskId, raw]) => {
      const value = isRecord(raw) ? raw : {};
      return {
        id: taskId,
        status: stringValue(value.status),
        startedAt: nullableString(value.started_at),
        completedAt: nullableString(value.completed_at),
        evidence: stringArray(value.evidence),
        note: stringValue(value.note)
      } satisfies TaskProjection;
    }).sort((a, b) => a.id.localeCompare(b.id));
    const planned = isRecord(state.knowledge_updates) ? state.knowledge_updates : null;
    const reviewState = isRecord(state.knowledge_review) ? state.knowledge_review : null;
    const reviewRequired = state.knowledge_review_required === true;
    const disposition = reviewState?.disposition === "promote" || reviewState?.disposition === "no-update"
      ? reviewState.disposition
      : null;
    const affectedPages = stringArray(reviewState?.affected_pages);
    const coveredChangedPaths = stringArray(reviewState?.covered_changed_paths);
    const uncoveredChangedPaths = stringArray(reviewState?.uncovered_changed_paths);
    const sealed = new Set(stringArray(planned?.sealed));
    const upserts = new Set(stringArray(planned?.upserts));
    const deletes = new Set(stringArray(planned?.deletes));
    const existingPages = new Set(knowledge.pages.map((page) => page.path));
    const pendingRefresh = affectedPages.filter((page) => {
      const deleted = deletes.has(page) && !existingPages.has(page);
      const refreshed = upserts.has(page) && sealed.has(page);
      return !deleted && !refreshed;
    });
    const review = {
      required: reviewRequired,
      current: Boolean(
        reviewRequired
        && disposition
        && stringValue(reviewState?.rationale).trim()
        && nullableString(reviewState?.recorded_at)
        && !nullableString(reviewState?.invalidated_at)
      ),
      disposition,
      rationale: stringValue(reviewState?.rationale),
      affectedPages,
      coveredChangedPaths,
      uncoveredChangedPaths,
      changeFingerprint: nullableString(reviewState?.change_fingerprint),
      recordedAt: nullableString(reviewState?.recorded_at),
      invalidatedAt: nullableString(reviewState?.invalidated_at)
    };
    const workKnowledge: KnowledgeProjection = {
      ...knowledge,
      affectedPages,
      pendingRefresh,
      coveredChangedPaths,
      uncoveredChangedPaths,
      review,
      planned
    };
    return {
      id,
      title: stringValue(state.title, id),
      kind: stringValue(state.kind),
      status: stringValue(state.status),
      phase: stringValue(state.phase),
      risk: isRecord(state.risk) ? stringValue(state.risk.level) : "unknown",
      gates,
      scope: isRecord(state.scope) ? stringArray(state.scope.paths) : [],
      scopeRationale: isRecord(state.scope) ? stringValue(state.scope.rationale) : "",
      baselineTargets: isRecord(state.baseline_updates) ? stringArray(state.baseline_updates.targets) : [],
      baselineRationale: isRecord(state.baseline_updates) ? stringValue(state.baseline_updates.rationale) : "",
      tasks,
      evidence,
      waivers,
      artifacts,
      events,
      blocker: isRecord(state.blocker) ? {
        task: nullableString(state.blocker.task) ?? undefined,
        reason: nullableString(state.blocker.reason) ?? undefined,
        at: nullableString(state.blocker.at) ?? undefined
      } : null,
      staleEvidence: [...new Set([
        ...stringArray(state.stale_evidence),
        ...evidence.filter((item) => item.stale).map((item) => item.id)
      ])],
      readOnly: stateReadOnly || diagnostics.slice(diagnosticStart).some((item) => item.severity === "critical"),
      updatedAt: nullableString(state.updated_at) ?? undefined,
      knowledgeProfile: state.knowledge_profile === "bootstrap" ? "bootstrap" : undefined,
      knowledgeReviewRequired: reviewRequired,
      knowledge: workKnowledge
    };
  }

  private validateWorkState(id: string, state: Record<string, unknown>, diagnostics: Diagnostic[]): boolean {
    let readOnly = false;
    const path = `.devweave/work-items/${id}/state.json`;
    if (state.schema_version !== 1) {
      diagnostics.push({
        severity: "critical",
        code: "work_unsupported_schema",
        message: `Unsupported work-item schema version: ${String(state.schema_version ?? "missing")}.`,
        path
      });
      readOnly = true;
    }
    if (state.id !== undefined && state.id !== id) {
      diagnostics.push({ severity: "critical", code: "work_id_mismatch", message: "Work-item state id does not match its directory.", path });
      readOnly = true;
    }
    if (state.status !== undefined && !["active", "closed"].includes(stringValue(state.status))) {
      diagnostics.push({ severity: "critical", code: "work_status_invalid", message: "Work-item status is invalid.", path });
      readOnly = true;
    }
    const phases = ["requirements", "scope_review", "design", "build_review", "implementation", "verification", "acceptance_review", "closed"];
    if (state.phase !== undefined && !phases.includes(stringValue(state.phase))) {
      diagnostics.push({ severity: "critical", code: "work_phase_invalid", message: "Work-item phase is invalid.", path });
      readOnly = true;
    }
    if (
      !Object.prototype.hasOwnProperty.call(state, "base_knowledge")
      || !Object.prototype.hasOwnProperty.call(state, "knowledge_review_required")
    ) {
      diagnostics.push({ severity: "warning", code: "legacy_work", message: "Work item predates one or more knowledge-review fields; displaying a legacy-compatible projection.", path });
    }
    if (state.knowledge_profile !== undefined && state.knowledge_profile !== "bootstrap") {
      diagnostics.push({ severity: "critical", code: "knowledge_profile_invalid", message: "Work-item knowledge profile is unknown.", path });
      readOnly = true;
    }
    if (state.knowledge_review_required !== undefined && typeof state.knowledge_review_required !== "boolean") {
      diagnostics.push({ severity: "critical", code: "knowledge_review_invalid", message: "Work-item knowledge review marker is invalid.", path });
      readOnly = true;
    }
    if (
      state.knowledge_review_required === true
      && !Object.prototype.hasOwnProperty.call(state, "base_knowledge")
    ) {
      diagnostics.push({ severity: "critical", code: "knowledge_review_invalid", message: "Knowledge review requires a base knowledge snapshot.", path });
      readOnly = true;
    }
    if (state.knowledge_profile === "bootstrap" && state.knowledge_review_required !== true) {
      diagnostics.push({ severity: "critical", code: "knowledge_profile_invalid", message: "Bootstrap profile requires the new knowledge review contract.", path });
      readOnly = true;
    }
    if (state.knowledge_review_required === true) {
      const review = isRecord(state.knowledge_review) ? state.knowledge_review : null;
      const disposition = review?.disposition;
      const arraysValid = review
        && ["affected_pages", "covered_changed_paths", "uncovered_changed_paths"]
          .every((key) => Array.isArray(review[key]) && review[key].every((item: unknown) => typeof item === "string"));
      if (
        !review
        || ![undefined, null, "promote", "no-update"].includes(disposition)
        || typeof review.rationale !== "string"
        || !arraysValid
        || (disposition !== undefined && disposition !== null && (
          review.rationale.trim().length === 0
          || typeof review.change_fingerprint !== "string"
          || review.change_fingerprint.length === 0
          || typeof review.recorded_at !== "string"
          || review.recorded_at.length === 0
        ))
      ) {
        diagnostics.push({ severity: "critical", code: "knowledge_review_invalid", message: "Work-item knowledge review contract is invalid or unknown.", path });
        readOnly = true;
      }
    }
    return readOnly;
  }

  private async readEvidence(root: string, diagnostics: Diagnostic[]): Promise<EvidenceProjection[]> {
    const evidenceRoot = joinRelativePath(root, "evidence");
    if (!(await this.files.exists(evidenceRoot))) {
      return [];
    }
    const entries = await this.files.readDirectory(evidenceRoot);
    const results: EvidenceProjection[] = [];
    for (const entry of entries.filter((item) => item.kind === "file" && item.name.endsWith(".json"))) {
      const path = joinRelativePath(evidenceRoot, entry.name);
      const read = await this.safeReadJson(path, diagnostics);
      const value = read.value;
      if (!value) {
        continue;
      }
      results.push({
        id: stringValue(value.id, entry.name.replace(/\.json$/, "")),
        kind: stringValue(value.kind),
        status: stringValue(value.status),
        summary: stringValue(value.summary),
        covers: stringArray(value.covers),
        tasks: stringArray(value.tasks),
        observedResult: nullableString(value.observed_result) ?? undefined,
        commandId: nullableString(value.command_id),
        exitCode: typeof value.exit_code === "number" ? value.exit_code : null,
        rawLog: nullableString(value.raw_log),
        stale: Boolean(value.stale),
        bindsCurrentSource: Boolean(value.binds_current_source),
        sourceFingerprint: nullableString(value.source_fingerprint) ?? undefined
      });
    }
    return results.sort((a, b) => a.id.localeCompare(b.id));
  }

  private async readEvents(root: string): Promise<string[]> {
    const path = joinRelativePath(root, "events.jsonl");
    if (!(await this.files.exists(path))) {
      return [];
    }
    const read = await this.files.readText(path, 250_000);
    return read.text.split(/\r?\n/).filter(Boolean).slice(-MAX_EVENTS);
  }

  private async readKnowledge(root: string, diagnostics: Diagnostic[]): Promise<KnowledgeProjection> {
    const pages: WikiPageProjection[] = [];
    if (await this.files.exists(root)) {
      for (const path of await this.collectFiles(root)) {
        if (!path.endsWith(".md")) {
          continue;
        }
        const read = await this.files.readText(path);
        pages.push(parseWikiPage(path, read.text, read.truncated));
      }
    }
    const placeholderPages = pages.filter((page) => page.status === "placeholder").map((page) => page.path);
    const stalePages = pages.filter((page) => page.status === "stale" || Boolean(
      page.sourceFingerprint && page.computedSourceFingerprint && page.sourceFingerprint !== page.computedSourceFingerprint
    )).map((page) => page.path);
    const critical = pages.flatMap((page) => page.parseErrors.map((message) => ({
      severity: "critical" as const,
      code: "wiki_parse",
      message,
      path: page.path
    })));
    const warnings: Diagnostic[] = [
      ...placeholderPages.map((path) => ({ severity: "warning" as const, code: "placeholder", message: "Wiki page is still a placeholder.", path })),
      ...stalePages.map((path) => ({ severity: "warning" as const, code: "stale", message: "Wiki page may be stale against its source fingerprint.", path }))
    ];
    const bootstrap = assessBootstrap(pages, critical.length > 0);
    return {
      root,
      health: critical.length > 0 ? "critical" : warnings.length > 0 ? "warning" : "healthy",
      pages: pages.sort((a, b) => a.path.localeCompare(b.path)),
      placeholderPages,
      stalePages,
      critical,
      warnings,
      affectedPages: [],
      pendingRefresh: [],
      coveredChangedPaths: [],
      uncoveredChangedPaths: [],
      bootstrap,
      review: {
        required: false,
        current: false,
        disposition: null,
        rationale: "",
        affectedPages: [],
        coveredChangedPaths: [],
        uncoveredChangedPaths: [],
        changeFingerprint: null,
        recordedAt: null,
        invalidatedAt: null
      },
      planned: null
    };
  }

  private async collectFiles(root: string): Promise<string[]> {
    const result: string[] = [];
    const visit = async (relative: string): Promise<void> => {
      for (const entry of await this.files.readDirectory(relative)) {
        const path = joinRelativePath(relative, entry.name);
        if (entry.kind === "directory") {
          await visit(path);
        } else {
          result.push(path);
        }
      }
    };
    await visit(root);
    return result.sort();
  }

  private readCommands(project: Record<string, unknown> | null, diagnostics: Diagnostic[]): CommandProjection[] {
    const rawCommands = project?.commands;
    if (Array.isArray(rawCommands)) {
      return rawCommands.flatMap((raw) => {
        if (!isRecord(raw) || !stringValue(raw.id) || !Array.isArray(raw.argv)) {
          diagnostics.push({ severity: "critical", code: "commands_invalid", message: "Configured verification command entries are invalid.", path: ".devweave/project.json" });
          return [];
        }
        return [this.toCommandProjection(stringValue(raw.id), raw)];
      });
    }
    if (isRecord(rawCommands)) {
      return Object.entries(rawCommands).flatMap(([id, raw]) => {
        if (!isRecord(raw) || !Array.isArray(raw.argv)) {
          diagnostics.push({ severity: "critical", code: "commands_invalid", message: "Configured verification command entries are invalid.", path: ".devweave/project.json" });
          return [];
        }
        return [this.toCommandProjection(id, raw)];
      });
    }
    if (rawCommands !== undefined) {
      diagnostics.push({ severity: "warning", code: "commands_invalid", message: "Configured verification commands are invalid.", path: ".devweave/project.json" });
    }
    return [];
  }

  private toCommandProjection(id: string, raw: Record<string, unknown>): CommandProjection {
    return {
      id,
      argv: stringArray(raw.argv),
      cwd: stringValue(raw.cwd, "."),
      timeoutSeconds: typeof raw.timeout_seconds === "number" ? raw.timeout_seconds : 0,
      requiredFor: stringArray(raw.required_for)
    };
  }

  private async safeReadJson(path: string, diagnostics: Diagnostic[]): Promise<{ value: Record<string, any> | null }> {
    try {
      const read = await this.files.readText(path);
      const value: unknown = JSON.parse(read.text);
      if (!isRecord(value)) {
        throw new Error("JSON root must be an object");
      }
      return { value };
    } catch (error) {
      diagnostics.push({ severity: "critical", code: "json_parse", message: error instanceof Error ? error.message : "JSON parse failed.", path });
      return { value: null };
    }
  }
}

function parseWikiPage(path: string, text: string, truncated: boolean): WikiPageProjection {
  const errors: string[] = [];
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
  if (!match) {
    errors.push("Wiki page is missing a valid frontmatter block.");
    return { path, title: path, type: "unknown", status: "invalid", sources: [], parseErrors: errors, bodyPreview: text.slice(0, 500) };
  }
  const fields = parseFrontmatter(match[1]);
  const title = stringValue(fields.title, path);
  const type = stringValue(fields.type, "unknown");
  const status = stringValue(fields.status, "unknown");
  if (!fields.title || !fields.type || !fields.status) {
    errors.push("Wiki frontmatter must include title, type, and status.");
  }
  return {
    path,
    title,
    type,
    status,
    sources: stringArray(fields.sources),
    sourceFingerprint: nullableString(fields.source_fingerprint) ?? undefined,
    computedSourceFingerprint: nullableString(fields.computed_source_fingerprint) ?? undefined,
    verifiedBy: nullableString(fields.verified_by) ?? undefined,
    parseErrors: errors,
    bodyPreview: `${match[2].slice(0, 500)}${truncated || match[2].length > 500 ? "…" : ""}`
  };
}

function assessBootstrap(pages: WikiPageProjection[], hasCritical: boolean): KnowledgeProjection["bootstrap"] {
  const ready = (page: WikiPageProjection): boolean => Boolean(
    page.status === "active"
    && page.sources.length > 0
    && page.sourceFingerprint
    && page.sourceFingerprint !== "none"
    && page.verifiedBy
    && page.parseErrors.length === 0
  );
  const overview = pages.find((page) => page.path === "wiki/overview.md" && page.type === "overview" && ready(page));
  const architecturePages = pages
    .filter((page) => page.type === "architecture" && ready(page))
    .map((page) => page.path)
    .sort();
  const modulePages = pages
    .filter((page) => page.type === "module" && ready(page))
    .map((page) => page.path)
    .sort();
  const reasons: string[] = [];
  if (!overview) reasons.push("overview_not_ready");
  if (architecturePages.length === 0) reasons.push("architecture_missing");
  if (modulePages.length === 0) reasons.push("module_missing");
  if (hasCritical) reasons.push("critical_lint");
  return {
    complete: reasons.length === 0,
    recommended: reasons.length > 0,
    reasons,
    overview: overview?.path ?? null,
    architecturePages,
    modulePages
  };
}

function parseFrontmatter(text: string): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const line of text.split(/\r?\n/)) {
    const separator = line.indexOf(":");
    if (separator <= 0) {
      continue;
    }
    const key = line.slice(0, separator).trim();
    const raw = line.slice(separator + 1).trim();
    if (raw.startsWith("[") && raw.endsWith("]")) {
      result[key] = raw.slice(1, -1).split(",").map((item) => item.trim().replace(/^['\"]|['\"]$/g, "")).filter(Boolean);
    } else {
      result[key] = raw.replace(/^['\"]|['\"]$/g, "");
    }
  }
  return result;
}

function normalizeGates(raw: unknown): Record<GateName, GateProjection> {
  const input = isRecord(raw) ? raw : {};
  return {
    scope: normalizeGate(input.scope),
    build: normalizeGate(input.build),
    acceptance: normalizeGate(input.acceptance)
  };
}

function normalizeGate(raw: unknown): GateProjection {
  const value = isRecord(raw) ? raw : {};
  return {
    status: stringValue(value.status, "pending"),
    fingerprint: nullableString(value.fingerprint),
    approvedBy: nullableString(value.approved_by),
    approvedAt: nullableString(value.approved_at)
  };
}

function isRecord(value: unknown): value is Record<string, any> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function stringValue(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function nullableString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function mapStringArrays(value: Record<string, any>): Record<string, string[]> {
  return Object.fromEntries(Object.entries(value).map(([key, raw]) => [key, stringArray(raw)]));
}
