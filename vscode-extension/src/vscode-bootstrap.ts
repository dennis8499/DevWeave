import * as vscode from "vscode";
import { normalizeRelativePath } from "./filesystem";
import { BootstrapPathKind, BootstrapResourceReader, BootstrapWorkspace } from "./bootstrap";

export class VscodeBootstrapWorkspace implements BootstrapWorkspace {
  public constructor(private readonly root: vscode.Uri) {}

  public async stat(relativePath: string): Promise<BootstrapPathKind> {
    try {
      const type = await vscode.workspace.fs.stat(this.uri(relativePath));
      if ((type.type & vscode.FileType.SymbolicLink) !== 0) return "symlink";
      if ((type.type & vscode.FileType.Directory) !== 0) return "directory";
      if ((type.type & vscode.FileType.File) !== 0) return "file";
      return "other";
    } catch (error) {
      if (error instanceof vscode.FileSystemError && error.code === "FileNotFound") {
        return "absent";
      }
      throw error;
    }
  }

  public async readBytes(relativePath: string): Promise<Uint8Array> {
    return vscode.workspace.fs.readFile(this.uri(relativePath));
  }

  public async writeBytes(relativePath: string, bytes: Uint8Array): Promise<void> {
    await vscode.workspace.fs.writeFile(this.uri(relativePath), bytes);
  }

  public async createDirectory(relativePath: string): Promise<void> {
    await vscode.workspace.fs.createDirectory(this.uri(relativePath));
  }

  public async delete(relativePath: string): Promise<void> {
    await vscode.workspace.fs.delete(this.uri(relativePath), { recursive: false, useTrash: false });
  }

  private uri(relativePath: string): vscode.Uri {
    const normalized = normalizeRelativePath(relativePath);
    if (normalized === ".") return this.root;
    return vscode.Uri.joinPath(this.root, ...normalized.split("/"));
  }
}

export class VscodeBootstrapResourceReader implements BootstrapResourceReader {
  private readonly root: vscode.Uri;

  public constructor(extensionUri: vscode.Uri) {
    this.root = vscode.Uri.joinPath(extensionUri, "dist", "bootstrap");
  }

  public async read(source: string): Promise<Uint8Array> {
    const normalized = normalizeRelativePath(source);
    if (normalized === ".") throw new Error("Bootstrap resource path cannot be empty.");
    return vscode.workspace.fs.readFile(vscode.Uri.joinPath(this.root, ...normalized.split("/")));
  }
}

export async function readBootstrapBundle(resources: BootstrapResourceReader): Promise<unknown> {
  const bytes = await resources.read("manifest.json");
  return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)) as unknown;
}
