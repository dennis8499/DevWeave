import * as vscode from "vscode";
import { BootstrapReport } from "./bootstrap";
import { ActionIntent, PromptBundle, WorkspaceSnapshot } from "./model";
import { HostToWebviewMessage, parseWebviewMessage } from "./protocol";

export interface DashboardCallbacks {
  refresh(): Promise<WorkspaceSnapshot>;
  initialize(): Promise<{ report: BootstrapReport; snapshot: WorkspaceSnapshot }>;
  preview(intent: ActionIntent): Promise<PromptBundle>;
  copy(intent: ActionIntent): Promise<PromptBundle>;
  openFile(relativePath: string): Promise<void>;
  selectWork(workId: string | null): void;
  protocolError(message: string): void;
}

export class DashboardPanel implements vscode.Disposable {
  private panel: vscode.WebviewPanel | undefined;

  public constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly callbacks: DashboardCallbacks
  ) {}

  public async show(snapshot: WorkspaceSnapshot, selectedWorkId?: string): Promise<void> {
    const selected = resolveSelection(snapshot, selectedWorkId ?? snapshot.selectedWorkId);
    if (this.panel) {
      this.panel.reveal(vscode.ViewColumn.One);
      await this.sendSnapshot({ ...snapshot, selectedWorkId: selected });
      return;
    }
    this.panel = vscode.window.createWebviewPanel(
      "devweave.controlCenter",
      "DevWeave Control Center",
      vscode.ViewColumn.One,
      {
        enableScripts: true,
        localResourceRoots: [vscode.Uri.joinPath(this.context.extensionUri, "dist", "webview")]
      }
    );
    this.panel.webview.html = this.html(this.panel.webview);
    this.panel.onDidDispose(() => {
      this.panel = undefined;
    }, undefined, this.context.subscriptions);
    this.panel.webview.onDidReceiveMessage(async (message: unknown) => {
      await this.handleMessage(message);
    }, undefined, this.context.subscriptions);
    await this.sendSnapshot({ ...snapshot, selectedWorkId: selected });
  }

  public async refresh(snapshot?: WorkspaceSnapshot): Promise<void> {
    if (!this.panel) {
      return;
    }
    const next = snapshot ?? await this.callbacks.refresh();
    await this.sendSnapshot({ ...next, selectedWorkId: resolveSelection(next, next.selectedWorkId) });
  }

  public dispose(): void {
    this.panel?.dispose();
    this.panel = undefined;
  }

  private async sendSnapshot(snapshot: WorkspaceSnapshot): Promise<void> {
    await this.sendMessage({ type: "snapshot", snapshot });
  }

  private async handleMessage(message: unknown): Promise<void> {
    const parsed = parseWebviewMessage(message);
    if (!parsed) {
      this.callbacks.protocolError("Rejected unknown or malformed Webview message.");
      await this.sendMessage({ type: "protocolError", message: "Unknown or malformed Webview message." });
      return;
    }
    try {
      switch (parsed.type) {
        case "refresh": {
          const snapshot = await this.callbacks.refresh();
          await this.sendSnapshot(snapshot);
          return;
        }
        case "initialize": {
          const result = await this.callbacks.initialize();
          await this.sendMessage({ type: "bootstrapResult", report: result.report, snapshot: result.snapshot });
          return;
        }
        case "selectWork":
          this.callbacks.selectWork(parsed.workId);
          return;
        case "openFile":
          await this.callbacks.openFile(parsed.path);
          return;
        case "copyAction":
          {
            const bundle = await this.callbacks.copy(parsed.intent);
            await this.sendMessage({ type: "copyResult", ok: true, bundle });
          }
          return;
        case "previewAction":
          {
            const bundle = await this.callbacks.preview(parsed.intent);
            await this.sendMessage({ type: "actionPreview", bundle });
          }
          return;
      }
    } catch (error) {
      await this.sendMessage({ type: "error", message: error instanceof Error ? error.message : "DevWeave action failed." });
    }
  }

  private async sendMessage(message: HostToWebviewMessage): Promise<void> {
    await this.panel?.webview.postMessage(message);
  }

  private html(webview: vscode.Webview): string {
    const script = webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, "dist", "webview", "main.js"));
    const style = webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, "dist", "webview", "styles.css"));
    return `<!doctype html>
<html lang="zh-Hant">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource}; script-src ${webview.cspSource};" />
    <link rel="stylesheet" href="${style}" />
    <title>DevWeave Control Center</title>
  </head>
  <body>
    <main id="app" aria-live="polite"></main>
    <script src="${script}"></script>
  </body>
</html>`;
  }
}

function resolveSelection(snapshot: WorkspaceSnapshot, selectedWorkId: string | null | undefined): string | null {
  if (selectedWorkId && snapshot.workItems.some((item) => item.id === selectedWorkId)) {
    return selectedWorkId;
  }
  return snapshot.workItems.length === 1 ? snapshot.workItems[0].id : null;
}
