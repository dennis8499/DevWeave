import * as vscode from "vscode";
import { DirectoryEntry, FileSystemPort, FileSystemPathKind, normalizeRelativePath, PathInspection } from "./filesystem";

export class VscodeFileSystemPort implements FileSystemPort {
  public constructor(private readonly root: vscode.Uri) {}

  public async exists(relativePath: string): Promise<boolean> {
    return await vscode.workspace.fs.stat(this.uri(relativePath)).then(
      () => true,
      () => false
    );
  }

  public async inspectPath(relativePath: string): Promise<PathInspection> {
    try {
      const type = await vscode.workspace.fs.stat(this.uri(relativePath));
      return { kind: pathKind(type.type) };
    } catch (error) {
      if (!isFileNotFound(error)) {
        return {
          kind: "other",
          diagnostic: error instanceof Error ? error.message : String(error)
        };
      }
      return { kind: "missing" };
    }
  }

  public async readBytes(relativePath: string): Promise<Uint8Array> {
    return vscode.workspace.fs.readFile(this.uri(relativePath));
  }

  public async readText(
    relativePath: string,
    maxBytes = 1_000_000
  ): Promise<{ text: string; truncated: boolean }> {
    const bytes = await vscode.workspace.fs.readFile(this.uri(relativePath));
    const truncated = bytes.byteLength > maxBytes;
    const selected = truncated ? bytes.slice(0, maxBytes) : bytes;
    return {
      text: new TextDecoder("utf-8", { fatal: false }).decode(selected),
      truncated
    };
  }

  public async readDirectory(relativePath: string): Promise<DirectoryEntry[]> {
    const entries = await vscode.workspace.fs.readDirectory(this.uri(relativePath));
    return entries.map(([name, type]) => ({
      name,
      kind: type === vscode.FileType.Directory ? "directory" : "file"
    }));
  }

  private uri(relativePath: string): vscode.Uri {
    const normalized = normalizeRelativePath(relativePath);
    if (normalized === ".") {
      return this.root;
    }
    return vscode.Uri.joinPath(this.root, ...normalized.split("/"));
  }
}

function pathKind(type: vscode.FileType): FileSystemPathKind {
  if ((type & vscode.FileType.SymbolicLink) !== 0) return "symlink";
  if ((type & vscode.FileType.Directory) !== 0) return "directory";
  if ((type & vscode.FileType.File) !== 0) return "file";
  return "other";
}

function isFileNotFound(error: unknown): boolean {
  return Boolean(error && typeof error === "object" && "code" in error && (error as { code?: unknown }).code === "FileNotFound");
}
