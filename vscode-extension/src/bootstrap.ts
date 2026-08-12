import { createHash } from "node:crypto";
import { normalizeRelativePath } from "./filesystem";
import {
  BootstrapCompatibilityKind,
  BootstrapExistingPolicy,
  normalizeBootstrapCompatibility,
  validateExistingBootstrapContent
} from "./bootstrap-compat";

export type BootstrapPathKind = "file" | "directory" | "symlink" | "other" | "absent";
export type BootstrapTransform = "copy" | "date";

export interface BootstrapWorkspace {
  stat(relativePath: string): Promise<BootstrapPathKind>;
  readBytes(relativePath: string): Promise<Uint8Array>;
  writeBytes(relativePath: string, bytes: Uint8Array): Promise<void>;
  createDirectory(relativePath: string): Promise<void>;
  delete(relativePath: string): Promise<void>;
}

export interface BootstrapResourceReader {
  read(source: string): Promise<Uint8Array>;
}

export interface BootstrapBundleFile {
  source: string;
  destination: string;
  transform: BootstrapTransform;
  byteLength: number;
  sha256: string;
  existingPolicy?: BootstrapExistingPolicy;
  compatibility?: BootstrapCompatibilityKind;
}

export interface BootstrapBundle {
  schemaVersion: number;
  bundleVersion: string;
  directories: string[];
  files: BootstrapBundleFile[];
}

export interface BootstrapConflict {
  path: string;
  reason: string;
}

export interface BootstrapError {
  path: string;
  reason: string;
}

export type BootstrapStatus = "initialized" | "repaired" | "already_initialized" | "partial" | "conflict" | "failed";

export interface BootstrapInspection {
  complete: boolean;
  expected: string[];
  missing: string[];
  adopted: string[];
  skipped: string[];
  conflicts: BootstrapConflict[];
  errors: BootstrapError[];
}

export interface BootstrapReport {
  ok: boolean;
  complete: boolean;
  status: BootstrapStatus;
  created: string[];
  adopted: string[];
  skipped: string[];
  missing: string[];
  conflicts: BootstrapConflict[];
  errors: BootstrapError[];
  rolledBack: string[];
}

export interface BootstrapInstallerOptions {
  now?: () => string;
}

interface PreparedFile extends BootstrapBundleFile {
  destination: string;
  bytes: Uint8Array;
}

interface NormalizedBundle {
  directories: string[];
  files: BootstrapBundleFile[];
}

interface PreparedBundle {
  normalized: NormalizedBundle;
  missingDirectories: string[];
  missingFiles: PreparedFile[];
  adopted: string[];
  skipped: string[];
  conflicts: BootstrapConflict[];
  errors: BootstrapError[];
  hadExistingContent: boolean;
}

export class BootstrapInstaller {
  public constructor(private readonly options: BootstrapInstallerOptions = {}) {}

  public async prepare(
    bundle: BootstrapBundle,
    resources: BootstrapResourceReader,
    workspace: BootstrapWorkspace
  ): Promise<PreparedBundle> {
    try {
      return await this.prepareInternal(bundle, resources, workspace);
    } catch (error) {
      return failedPreparation(error);
    }
  }

  public async inspect(
    bundle: BootstrapBundle,
    resources: BootstrapResourceReader,
    workspace: BootstrapWorkspace
  ): Promise<BootstrapInspection> {
    const prepared = await this.prepare(bundle, resources, workspace);
    return this.inspectPrepared(prepared);
  }

  public inspectPrepared(prepared: PreparedBundle): BootstrapInspection {
    const missing = [
      ...prepared.missingDirectories,
      ...prepared.missingFiles.map((file) => file.destination)
    ].sort(comparePathDepth);
    return {
      complete: missing.length === 0 && prepared.conflicts.length === 0 && prepared.errors.length === 0,
      expected: [...prepared.normalized.directories, ...prepared.normalized.files.map((file) => file.destination)].sort(comparePathDepth),
      missing,
      adopted: prepared.adopted,
      skipped: prepared.skipped,
      conflicts: prepared.conflicts,
      errors: prepared.errors
    };
  }

  public async install(
    bundle: BootstrapBundle,
    resources: BootstrapResourceReader,
    workspace: BootstrapWorkspace
  ): Promise<BootstrapReport> {
    const prepared = await this.prepare(bundle, resources, workspace);
    return this.installPrepared(prepared, workspace);
  }

  public async installPrepared(
    prepared: PreparedBundle,
    workspace: BootstrapWorkspace
  ): Promise<BootstrapReport> {
    const missing = [
      ...prepared.missingDirectories,
      ...prepared.missingFiles.map((file) => file.destination)
    ].sort(comparePathDepth);
    if (prepared.errors.length > 0) {
      return failedReport(prepared.adopted, prepared.errors, prepared.conflicts, prepared.skipped, missing);
    }

    const revalidation = await this.revalidate(prepared, workspace);
    if (revalidation.errors.length > 0) {
      return failedReport(
        prepared.adopted,
        [...prepared.errors, ...revalidation.errors],
        prepared.conflicts,
        prepared.skipped,
        missing
      );
    }
    prepared.conflicts.push(...revalidation.conflicts);
    const revalidationConflictPaths = new Set(revalidation.conflicts.map((item) => item.path));
    const blockedByRevalidation = (path: string): boolean => [...revalidationConflictPaths].some(
      (conflictPath) => path === conflictPath || path.startsWith(`${conflictPath}/`)
    );

    const createdDirectories: string[] = [];
    const createdFiles: string[] = [];
    const rolledBack: string[] = [];
    try {
      for (const directory of prepared.missingDirectories) {
        if (blockedByRevalidation(directory)) continue;
        await workspace.createDirectory(directory);
        createdDirectories.push(directory);
      }
      for (const file of prepared.missingFiles.sort((left, right) => left.destination.localeCompare(right.destination))) {
        if (blockedByRevalidation(file.destination)) continue;
        await workspace.writeBytes(file.destination, file.bytes);
        createdFiles.push(file.destination);
      }
    } catch (error) {
      for (const path of [...createdFiles].reverse()) {
        try {
          await workspace.delete(path);
          rolledBack.push(path);
        } catch (rollbackError) {
          prepared.errors.push({ path, reason: `Rollback failed: ${errorMessage(rollbackError)}` });
        }
      }
      for (const path of [...createdDirectories].reverse()) {
        try {
          await workspace.delete(path);
          rolledBack.push(path);
        } catch (rollbackError) {
          prepared.errors.push({ path, reason: `Rollback failed: ${errorMessage(rollbackError)}` });
        }
      }
      prepared.errors.push({ path: createdFiles.at(-1) ?? createdDirectories.at(-1) ?? ".", reason: errorMessage(error) });
      return failedReport(prepared.adopted, prepared.errors, prepared.conflicts, prepared.skipped, missing, [...createdDirectories, ...createdFiles], rolledBack);
    }

    const created = [...createdDirectories, ...createdFiles];
    const complete = prepared.conflicts.length === 0 && prepared.errors.length === 0;
    const status: BootstrapStatus = complete
      ? created.length === 0
        ? "already_initialized"
        : prepared.hadExistingContent ? "repaired" : "initialized"
      : prepared.conflicts.length > 0
        ? created.length > 0 ? "partial" : "conflict"
        : "failed";
    return {
      ok: complete,
      complete,
      status,
      created,
      adopted: prepared.adopted,
      skipped: prepared.skipped,
      missing: complete ? [] : missing,
      conflicts: prepared.conflicts,
      errors: prepared.errors,
      rolledBack: []
    };
  }

  private async prepareInternal(
    bundle: BootstrapBundle,
    resources: BootstrapResourceReader,
    workspace: BootstrapWorkspace
  ): Promise<PreparedBundle> {
    const normalized = this.normalizeBundle(bundle);
    if ("error" in normalized) {
      return {
        normalized: { directories: [], files: [] },
        missingDirectories: [],
        missingFiles: [],
        adopted: [],
        skipped: [],
        conflicts: [],
        errors: [{ path: "manifest.json", reason: normalized.error }],
        hadExistingContent: false
      };
    }

    const conflicts: BootstrapConflict[] = [];
    const errors: BootstrapError[] = [];
    const adopted: string[] = [];
    const skipped: string[] = [];
    const missingDirectories: string[] = [];
    const missingFiles: PreparedFile[] = [];
    let hadExistingContent = false;
    const date = (this.options.now ?? (() => new Date().toISOString()))().slice(0, 10);

    const allDirectories = [...normalized.directories];
    for (const file of normalized.files) {
      const parent = parentPath(file.destination);
      if (parent) allDirectories.push(...parentDirectories(parent));
    }
    const directories = [...new Set(allDirectories)].sort(comparePathDepth);

    const statCache = new Map<string, Promise<BootstrapPathKind>>();
    for (const directory of directories) {
      const parentIssue = await this.parentIssue(directory, workspace, statCache);
      if (parentIssue) {
        conflicts.push({ path: directory, reason: parentIssue });
        hadExistingContent = true;
        continue;
      }
      const kind = await this.cachedStat(directory, workspace, statCache);
      if (kind === "absent") {
        missingDirectories.push(directory);
      } else if (kind === "directory") {
        skipped.push(directory);
        hadExistingContent = true;
      } else {
        conflicts.push({ path: directory, reason: `Expected directory but found ${kind}.` });
        hadExistingContent = true;
      }
    }

    const fileResults = await Promise.all(normalized.files.map(async (file) => {
      const result = {
        missing: [] as PreparedFile[],
        adopted: [] as string[],
        conflicts: [] as BootstrapConflict[],
        errors: [] as BootstrapError[],
        hadExistingContent: false
      };
      let sourceBytes: Uint8Array;
      try {
        sourceBytes = await resources.read(file.source);
      } catch (error) {
        result.errors.push({ path: file.source, reason: errorMessage(error) });
        return result;
      }
      const actualHash = sha256(sourceBytes);
      if (sourceBytes.byteLength !== file.byteLength || actualHash !== file.sha256) {
        result.errors.push({
          path: file.source,
          reason: `Bundle integrity mismatch (expected ${file.byteLength}/${file.sha256}, actual ${sourceBytes.byteLength}/${actualHash}).`
        });
        return result;
      }
      const bytes = file.transform === "date"
        ? new TextEncoder().encode(new TextDecoder("utf-8", { fatal: true }).decode(sourceBytes).replaceAll("{date}", date))
        : sourceBytes;
      const parentIssue = await this.parentIssue(file.destination, workspace, statCache);
      if (parentIssue) {
        result.conflicts.push({ path: file.destination, reason: parentIssue });
        result.hadExistingContent = true;
        return result;
      }
      const kind = await this.cachedStat(file.destination, workspace, statCache);
      if (kind === "absent") {
        result.missing.push({ ...file, bytes });
      } else if (kind === "file") {
        result.hadExistingContent = true;
        try {
          const existing = await workspace.readBytes(file.destination);
          const semantic = file.existingPolicy === "adopt-compatible"
            ? validateExistingBootstrapContent(file.compatibility as BootstrapCompatibilityKind, existing)
            : { compatible: sameBytes(existing, bytes) };
          if (semantic.compatible) {
            result.adopted.push(file.destination);
          } else {
            result.conflicts.push({
              path: file.destination,
              reason: file.existingPolicy === "adopt-compatible"
                ? `Existing file is not compatible: ${semantic.reason ?? "semantic contract mismatch"}`
                : "Existing file bytes differ from the bundled content."
            });
          }
        } catch (error) {
          result.errors.push({ path: file.destination, reason: errorMessage(error) });
        }
      } else {
        result.conflicts.push({ path: file.destination, reason: `Expected file but found ${kind}.` });
        result.hadExistingContent = true;
      }
      return result;
    }));
    for (const result of fileResults) {
      missingFiles.push(...result.missing);
      adopted.push(...result.adopted);
      conflicts.push(...result.conflicts);
      errors.push(...result.errors);
      hadExistingContent ||= result.hadExistingContent;
    }

    return { normalized, missingDirectories, missingFiles, adopted, skipped, conflicts, errors, hadExistingContent };
  }

  private async revalidate(
    prepared: PreparedBundle,
    workspace: BootstrapWorkspace
  ): Promise<{ conflicts: BootstrapConflict[]; errors: BootstrapError[] }> {
    const conflicts: BootstrapConflict[] = [];
    const errors: BootstrapError[] = [];
    const statCache = new Map<string, Promise<BootstrapPathKind>>();
    const paths = [
      ...prepared.missingDirectories.map((path) => ({ path, expected: "directory" as const })),
      ...prepared.missingFiles.map((file) => ({ path: file.destination, expected: "file" as const }))
    ];
    for (const item of paths) {
      try {
        const parentIssue = await this.parentIssue(item.path, workspace, statCache);
        if (parentIssue) {
          conflicts.push({ path: item.path, reason: parentIssue });
          continue;
        }
        const kind = await this.cachedStat(item.path, workspace, statCache);
        if (kind !== "absent") {
          conflicts.push({
            path: item.path,
            reason: `Workspace changed after inspection; expected missing ${item.expected} but found ${kind}.`
          });
        }
      } catch (error) {
        errors.push({ path: item.path, reason: errorMessage(error) });
      }
    }
    return { conflicts, errors };
  }

  private normalizeBundle(bundle: BootstrapBundle): NormalizedBundle | { error: string } {
    if (!bundle || bundle.schemaVersion !== 1 || !Array.isArray(bundle.directories) || !Array.isArray(bundle.files)) {
      return { error: "Unsupported or malformed bootstrap manifest." };
    }
    const directories: string[] = [];
    const destinations = new Map<string, "directory" | "file">();
    for (const value of bundle.directories) {
      const path = safePath(value);
      if (!path || destinations.has(path)) {
        return { error: `Invalid or duplicate directory destination: ${String(value)}.` };
      }
      destinations.set(path, "directory");
      directories.push(path);
    }
    const files: BootstrapBundleFile[] = [];
    for (const file of bundle.files) {
      const destination = safePath(file?.destination);
      const source = safePath(file?.source);
      if (!destination || !source || destinations.has(destination)) {
        return { error: `Invalid or duplicate file destination: ${String(file?.destination)}.` };
      }
      if ((file.transform !== "copy" && file.transform !== "date")
        || !Number.isInteger(file.byteLength)
        || file.byteLength < 0
        || !/^[a-f0-9]{64}$/i.test(file.sha256)) {
        return { error: `Malformed bootstrap file entry: ${String(file?.destination)}.` };
      }
      const compatibility = normalizeBootstrapCompatibility(file);
      if ("error" in compatibility) {
        return { error: `Malformed bootstrap compatibility for ${String(file?.destination)}: ${compatibility.error}` };
      }
      destinations.set(destination, "file");
      files.push({
        ...file,
        ...compatibility,
        source,
        destination,
        sha256: file.sha256.toLowerCase()
      });
    }
    for (const [path, kind] of destinations) {
      const parent = parentPath(path);
      if (parent && destinations.get(parent) === "file") {
        return { error: `Manifest file ${parent} cannot contain ${kind} ${path}.` };
      }
    }
    return {
      directories: [...new Set(directories)].sort(comparePathDepth),
      files: files.sort((left, right) => left.destination.localeCompare(right.destination))
    };
  }

  private async cachedStat(
    path: string,
    workspace: BootstrapWorkspace,
    cache: Map<string, Promise<BootstrapPathKind>>
  ): Promise<BootstrapPathKind> {
    let pending = cache.get(path);
    if (!pending) {
      pending = workspace.stat(path);
      cache.set(path, pending);
    }
    return pending;
  }

  private async parentIssue(
    path: string,
    workspace: BootstrapWorkspace,
    cache: Map<string, Promise<BootstrapPathKind>>
  ): Promise<string | null> {
    const parts = path.split("/");
    let current = "";
    for (const part of parts.slice(0, -1)) {
      current = current ? `${current}/${part}` : part;
      const kind = await this.cachedStat(current, workspace, cache);
      if (kind === "file" || kind === "symlink" || kind === "other") {
        return `Parent path ${current} is ${kind}.`;
      }
    }
    return null;
  }
}

function failedPreparation(error: unknown): PreparedBundle {
  return {
    normalized: { directories: [], files: [] },
    missingDirectories: [],
    missingFiles: [],
    adopted: [],
    skipped: [],
    conflicts: [],
    errors: [{ path: "manifest.json", reason: errorMessage(error) }],
    hadExistingContent: false
  };
}

function failedReport(
  adopted: string[],
  errors: BootstrapError[],
  conflicts: BootstrapConflict[] = [],
  skipped: string[] = [],
  missing: string[] = [],
  created: string[] = [],
  rolledBack: string[] = []
): BootstrapReport {
  return {
    ok: false,
    complete: false,
    status: errors.length > 0 ? "failed" : conflicts.length ? created.length ? "partial" : "conflict" : "failed",
    created,
    adopted,
    skipped,
    missing,
    conflicts,
    errors,
    rolledBack
  };
}

function safePath(value: unknown): string | null {
  if (typeof value !== "string" || !value.trim()) return null;
  try {
    const path = normalizeRelativePath(value);
    return path === "." ? null : path;
  } catch {
    return null;
  }
}

function parentPath(path: string): string {
  const index = path.lastIndexOf("/");
  return index < 0 ? "" : path.slice(0, index);
}

function parentDirectories(path: string): string[] {
  const parts = path.split("/");
  const parents: string[] = [];
  for (let index = 1; index <= parts.length; index += 1) {
    parents.push(parts.slice(0, index).join("/"));
  }
  return parents;
}

function comparePathDepth(left: string, right: string): number {
  const depth = left.split("/").length - right.split("/").length;
  return depth || left.localeCompare(right);
}

function sha256(bytes: Uint8Array): string {
  return createHash("sha256").update(Buffer.from(bytes)).digest("hex");
}

function sameBytes(left: Uint8Array, right: Uint8Array): boolean {
  return left.byteLength === right.byteLength && left.every((value, index) => value === right[index]);
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
