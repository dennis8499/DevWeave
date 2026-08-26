import { lstatSync, realpathSync } from "node:fs";
import { isAbsolute, relative, resolve } from "node:path";

interface CompiledTaskScope {
  readonly repository: string;
  readonly declarations: ReadonlyArray<{ declaration: string; root: string }>;
  readonly writableRoots: string[];
}

/**
 * Return declarations only when exactly one task owns the implementation turn.
 * An empty result is deliberately ambiguous between no owner and malformed state;
 * every caller must fail closed in either case.
 */
export function currentDeclarations(run: Record<string, unknown>): string[] {
  const tasks = Object.values(record(run.tasks)).filter((value) => record(value).status === "in_progress");
  if (tasks.length !== 1) return [];
  const definition = record(record(tasks[0]).definition);
  const declared = Array.isArray(definition.declared_paths)
    ? definition.declared_paths.filter((item): item is string => typeof item === "string")
    : [];
  return declared.length > 0 ? [...new Set(declared)] : [];
}

/**
 * Codex writableRoots are directory subtrees. Only a declaration with exactly the
 * same semantics (`directory/**`) can be represented without widening authority.
 */
export function writableTaskRoots(repository: string, run: Record<string, unknown>): string[] {
  return compileTaskScope(repository, run)?.writableRoots ?? [];
}

export function isTaskPathInScope(repository: string, run: Record<string, unknown>, candidate: string): boolean {
  const scope = compileTaskScope(repository, run);
  const normalized = normalizeRelative(candidate);
  if (!scope || !normalized) return false;

  for (const declaration of scope.declarations) {
    if (normalized !== declaration.declaration && !normalized.startsWith(`${declaration.declaration}/`)) continue;
    const absolute = resolve(scope.repository, ...normalized.split("/"));
    if (!contained(scope.repository, absolute) || !contained(declaration.root, absolute)) return false;
    if (!hasSafeExistingComponents(scope.repository, absolute)) return false;
    try {
      if (lstatSync(absolute).isSymbolicLink()) return false;
      const physical = realpathSync.native(absolute);
      return contained(declaration.root, physical);
    } catch (error) {
      return isMissing(error);
    }
  }
  return false;
}

function compileTaskScope(repository: string, run: Record<string, unknown>): CompiledTaskScope | null {
  const declarations = currentDeclarations(run);
  if (declarations.length === 0) return null;
  const lexicalRepository = resolve(repository);
  let physicalRepository: string;
  try {
    const root = lstatSync(lexicalRepository);
    if (!root.isDirectory() || root.isSymbolicLink()) return null;
    physicalRepository = realpathSync.native(lexicalRepository);
  } catch {
    return null;
  }

  const compiled: Array<{ declaration: string; root: string }> = [];
  for (const raw of declarations) {
    const normalized = normalizeRelative(raw);
    if (!normalized?.endsWith("/**")) return null;
    const declaration = normalized.slice(0, -3);
    if (!declaration || /[*?[\]]/.test(declaration)) return null;
    const lexicalRoot = resolve(lexicalRepository, ...declaration.split("/"));
    if (!contained(lexicalRepository, lexicalRoot) || !hasSafeExistingComponents(lexicalRepository, lexicalRoot)) return null;
    try {
      const stat = lstatSync(lexicalRoot);
      if (!stat.isDirectory() || stat.isSymbolicLink()) return null;
      const physicalRoot = realpathSync.native(lexicalRoot);
      if (!contained(physicalRepository, physicalRoot)) return null;
      compiled.push({ declaration, root: physicalRoot });
    } catch {
      return null;
    }
  }
  const writableRoots = [...new Set(compiled.map((item) => item.root))];
  return { repository: physicalRepository, declarations: compiled, writableRoots };
}

function normalizeRelative(value: string): string | null {
  if (typeof value !== "string" || !value || /[\0\r\n]/.test(value)) return null;
  const normalized = value.replaceAll("\\", "/");
  if (normalized.startsWith("/") || normalized.startsWith("//") || normalized.includes(":") || isAbsolute(value)) return null;
  const parts = normalized.split("/");
  if (parts.some((part) => !part || part === "." || part === ".." || part.endsWith(".") || part.endsWith(" ") || windowsDevice(part))) return null;
  return parts.join("/");
}

function windowsDevice(part: string): boolean {
  const stem = part.split(".", 1)[0].toUpperCase();
  return /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$/.test(stem);
}

function hasSafeExistingComponents(root: string, candidate: string): boolean {
  const rel = relative(root, candidate);
  if (!rel || rel.startsWith("..") || isAbsolute(rel)) return rel === "";
  let cursor = root;
  for (const part of rel.split(/[\\/]/)) {
    cursor = resolve(cursor, part);
    try {
      if (lstatSync(cursor).isSymbolicLink()) return false;
    } catch (error) {
      return isMissing(error);
    }
  }
  return true;
}

function contained(root: string, candidate: string): boolean {
  const rel = relative(root, candidate);
  return rel === "" || (!rel.startsWith("..") && !isAbsolute(rel));
}

function isMissing(error: unknown): boolean {
  return typeof error === "object" && error !== null && "code" in error && (error as { code?: unknown }).code === "ENOENT";
}

function record(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
