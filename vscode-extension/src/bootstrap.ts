import { createHash } from "node:crypto";
import { normalizeRelativePath } from "./filesystem";

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

export type BootstrapStatus = "initialized" | "already_initialized" | "conflict" | "failed";

export interface BootstrapReport {
  ok: boolean;
  status: BootstrapStatus;
  created: string[];
  adopted: string[];
  skipped: string[];
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

export class BootstrapInstaller {
  public constructor(private readonly options: BootstrapInstallerOptions = {}) {}

  public async install(
    bundle: BootstrapBundle,
    resources: BootstrapResourceReader,
    workspace: BootstrapWorkspace
  ): Promise<BootstrapReport> {
    const normalized = this.normalizeBundle(bundle);
    if ("error" in normalized) {
      return failedReport([], [{ path: "manifest.json", reason: normalized.error }]);
    }

    const conflicts: BootstrapConflict[] = [];
    const errors: BootstrapError[] = [];
    const adopted: string[] = [];
    const skipped: string[] = [];
    const missingDirectories: string[] = [];
    const preparedFiles: PreparedFile[] = [];
    const missingFiles: PreparedFile[] = [];
    const date = (this.options.now ?? (() => new Date().toISOString()))().slice(0, 10);

    const allDirectories = [...normalized.directories];
    for (const file of normalized.files) {
      const parent = parentPath(file.destination);
      if (parent) allDirectories.push(...parentDirectories(parent));
    }
    const directories = [...new Set(allDirectories)].sort(comparePathDepth);

    for (const directory of directories) {
      const parentIssue = await this.parentIssue(directory, workspace);
      if (parentIssue) {
        conflicts.push({ path: directory, reason: parentIssue });
        continue;
      }
      const kind = await workspace.stat(directory);
      if (kind === "absent") {
        missingDirectories.push(directory);
      } else if (kind === "directory") {
        skipped.push(directory);
      } else {
        conflicts.push({ path: directory, reason: `Expected directory but found ${kind}.` });
      }
    }

    for (const file of normalized.files) {
      let sourceBytes: Uint8Array;
      try {
        sourceBytes = await resources.read(file.source);
      } catch (error) {
        errors.push({ path: file.source, reason: errorMessage(error) });
        continue;
      }
      const actualHash = sha256(sourceBytes);
      if (sourceBytes.byteLength !== file.byteLength || actualHash !== file.sha256) {
        errors.push({
          path: file.source,
          reason: `Bundle integrity mismatch (expected ${file.byteLength}/${file.sha256}, actual ${sourceBytes.byteLength}/${actualHash}).`
        });
        continue;
      }
      const bytes = file.transform === "date"
        ? new TextEncoder().encode(new TextDecoder("utf-8", { fatal: true }).decode(sourceBytes).replaceAll("{date}", date))
        : sourceBytes;
      const prepared = { ...file, destination: file.destination, bytes };
      preparedFiles.push(prepared);
      const parentIssue = await this.parentIssue(file.destination, workspace);
      if (parentIssue) {
        conflicts.push({ path: file.destination, reason: parentIssue });
        continue;
      }
      const kind = await workspace.stat(file.destination);
      if (kind === "absent") {
        missingFiles.push(prepared);
      } else if (kind === "file") {
        try {
          const existing = await workspace.readBytes(file.destination);
          if (sameBytes(existing, bytes)) {
            adopted.push(file.destination);
          } else {
            conflicts.push({ path: file.destination, reason: "Existing file bytes differ from the bundled content." });
          }
        } catch (error) {
          errors.push({ path: file.destination, reason: errorMessage(error) });
        }
      } else {
        conflicts.push({ path: file.destination, reason: `Expected file but found ${kind}.` });
      }
    }

    if (conflicts.length || errors.length) {
      return failedReport(adopted, errors, conflicts, skipped);
    }

    const createdDirectories: string[] = [];
    const createdFiles: string[] = [];
    const rolledBack: string[] = [];
    try {
      for (const directory of missingDirectories) {
        await workspace.createDirectory(directory);
        createdDirectories.push(directory);
      }
      for (const file of missingFiles.sort((left, right) => left.destination.localeCompare(right.destination))) {
        await workspace.writeBytes(file.destination, file.bytes);
        createdFiles.push(file.destination);
      }
    } catch (error) {
      for (const path of [...createdFiles].reverse()) {
        try {
          await workspace.delete(path);
          rolledBack.push(path);
        } catch (rollbackError) {
          errors.push({ path, reason: `Rollback failed: ${errorMessage(rollbackError)}` });
        }
      }
      errors.push({ path: createdFiles.at(-1) ?? createdDirectories.at(-1) ?? ".", reason: errorMessage(error) });
      return failedReport(adopted, errors, [], skipped, [...createdDirectories, ...createdFiles], rolledBack);
    }

    const created = [...createdDirectories, ...createdFiles];
    return {
      ok: true,
      status: created.length ? "initialized" : "already_initialized",
      created,
      adopted,
      skipped,
      conflicts: [],
      errors: [],
      rolledBack: []
    };
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
      destinations.set(destination, "file");
      files.push({ ...file, source, destination, sha256: file.sha256.toLowerCase() });
    }
    for (const [path, kind] of destinations) {
      const parent = parentPath(path);
      if (parent && destinations.get(parent) === "file") {
        return { error: `Manifest file ${parent} cannot contain ${kind} ${path}.` };
      }
    }
    return { directories: [...new Set(directories)].sort(comparePathDepth), files: files.sort((left, right) => left.destination.localeCompare(right.destination)) };
  }

  private async parentIssue(path: string, workspace: BootstrapWorkspace): Promise<string | null> {
    const parts = path.split("/");
    let current = "";
    for (const part of parts.slice(0, -1)) {
      current = current ? `${current}/${part}` : part;
      const kind = await workspace.stat(current);
      if (kind === "file" || kind === "symlink" || kind === "other") {
        return `Parent path ${current} is ${kind}.`;
      }
    }
    return null;
  }
}

function failedReport(
  adopted: string[],
  errors: BootstrapError[],
  conflicts: BootstrapConflict[] = [],
  skipped: string[] = [],
  created: string[] = [],
  rolledBack: string[] = []
): BootstrapReport {
  return {
    ok: false,
    status: conflicts.length ? "conflict" : "failed",
    created,
    adopted,
    skipped,
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
