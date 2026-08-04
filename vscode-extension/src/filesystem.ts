export type EntryKind = "file" | "directory";

export interface DirectoryEntry {
  name: string;
  kind: EntryKind;
}

export interface FileSystemPort {
  exists(relativePath: string): Promise<boolean>;
  readBytes?(relativePath: string): Promise<Uint8Array>;
  readText(relativePath: string, maxBytes?: number): Promise<{ text: string; truncated: boolean }>;
  readDirectory(relativePath: string): Promise<DirectoryEntry[]>;
}

export function normalizeRelativePath(value: string): string {
  const normalized = value.replaceAll("\\", "/").replace(/^\.\//, "");
  if (!normalized || normalized === ".") {
    return ".";
  }
  if (normalized.startsWith("/") || /^[A-Za-z]:\//.test(normalized)) {
    throw new Error(`Absolute path is not allowed: ${value}`);
  }
  const parts = normalized.split("/").filter(Boolean);
  if (parts.some((part) => part === "..")) {
    throw new Error(`Path escapes workspace: ${value}`);
  }
  return parts.join("/");
}

export function joinRelativePath(...parts: string[]): string {
  return normalizeRelativePath(parts.filter(Boolean).join("/"));
}
