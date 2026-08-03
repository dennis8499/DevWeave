import * as vscode from "vscode";

export interface ClipboardAdapter {
  copy(text: string): Promise<void>;
}

export class VscodeClipboardAdapter implements ClipboardAdapter {
  public async copy(text: string): Promise<void> {
    await vscode.env.clipboard.writeText(text);
  }
}
