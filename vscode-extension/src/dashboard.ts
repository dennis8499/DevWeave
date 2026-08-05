import * as vscode from "vscode";
import { BootstrapReport } from "./bootstrap";
import { DashboardPreferences, DisplayMode, PromptBundle, PublicCommandIntent, WorkspaceSnapshot } from "./model";
import { PreviewGate } from "./preview-gate";
import { HostToWebviewMessage, parseWebviewMessage } from "./protocol";
import { resolveWorkSelection } from "./work-selection";

export interface DashboardCallbacks {
  refresh(): Promise<WorkspaceSnapshot>;
  initialize(): Promise<{ report: BootstrapReport; snapshot: WorkspaceSnapshot }>;
  preview(intent: PublicCommandIntent): Promise<PromptBundle>;
  copy(bundle: PromptBundle): Promise<PromptBundle>;
  copySuccess?(): Promise<void> | void;
  openFile(relativePath: string): Promise<void>;
  selectWork(workId: string | null): void;
  getPreferences?(): DashboardPreferences;
  setDisplayMode?(mode: DisplayMode): Promise<void> | void;
  protocolError(message: string): void;
}

let panelSequence = 0;

export class DashboardPanel implements vscode.Disposable {
  private panel: vscode.WebviewPanel | undefined;
  private lastSnapshot: WorkspaceSnapshot | undefined;
  private revision = 0;
  private readonly panelId = `control-center-${++panelSequence}`;
  private readonly previewGate = new PreviewGate();

  public constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly callbacks: DashboardCallbacks
  ) {}

  public async show(snapshot: WorkspaceSnapshot, selectedWorkId?: string): Promise<void> {
    const selected = resolveWorkSelection(snapshot, selectedWorkId ?? snapshot.selectedWorkId);
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
      this.invalidateRevision();
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
    await this.sendSnapshot({ ...next, selectedWorkId: resolveWorkSelection(next, next.selectedWorkId) });
  }

  public dispose(): void {
    this.panel?.dispose();
    this.panel = undefined;
    this.invalidateRevision();
  }

  public async previewAction(intent: PublicCommandIntent): Promise<void> {
    if (!this.panel) {
      throw new Error("控制中心尚未開啟，請先開啟控制中心再預覽操作。");
    }
    await this.stagePreview(intent);
  }

  private async sendSnapshot(snapshot: WorkspaceSnapshot, invalidate = true): Promise<void> {
    if (invalidate) {
      this.invalidateRevision();
    }
    this.lastSnapshot = snapshot;
    await this.sendMessage({
      type: "snapshot",
      snapshot,
      revision: this.revision,
      preferences: this.callbacks.getPreferences?.() ?? { displayMode: "concise" }
    });
  }

  private async handleMessage(message: unknown): Promise<void> {
    const parsed = parseWebviewMessage(message);
    if (!parsed) {
      this.callbacks.protocolError("拒絕未知或格式錯誤的 Webview 訊息。");
      await this.sendMessage({ type: "protocolError", message: "無法接受未知或格式錯誤的訊息。" });
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
          this.invalidateRevision();
          this.lastSnapshot = result.snapshot;
          await this.sendMessage({
            type: "bootstrapResult",
            report: result.report,
            snapshot: result.snapshot,
            revision: this.revision
          });
          return;
        }
        case "selectWork": {
          this.callbacks.selectWork(parsed.workId);
          if (this.lastSnapshot) {
            const selectedWorkId = resolveWorkSelection(this.lastSnapshot, parsed.workId);
            await this.sendSnapshot({ ...this.lastSnapshot, selectedWorkId });
          } else {
            this.invalidateRevision();
          }
          return;
        }
        case "setDisplayMode":
          await this.callbacks.setDisplayMode?.(parsed.mode);
          if (this.lastSnapshot) {
            await this.sendSnapshot(this.lastSnapshot, false);
          }
          return;
        case "openFile":
          await this.callbacks.openFile(parsed.path);
          return;
        case "copyAction":
          {
            const ticket = this.previewGate.take(this.panelId, parsed.intent, this.revision);
            if (!ticket) {
              throw new Error("請先完成同一操作的預覽；workspace 狀態可能已更新，請重新預覽。");
            }
            let bundle: PromptBundle;
            try {
              bundle = await this.callbacks.copy(ticket.bundle);
            } catch (error) {
              this.previewGate.restore(ticket);
              throw error;
            }
            await this.sendMessage({ type: "copyResult", ok: true, bundle });
            await this.callbacks.copySuccess?.();
          }
          return;
        case "previewAction":
          await this.stagePreview(parsed.intent);
          return;
      }
    } catch (error) {
      const failure = presentOperationError(error);
      await this.sendMessage({ type: "error", message: failure.message, detail: failure.detail });
    }
  }

  private async sendMessage(message: HostToWebviewMessage): Promise<void> {
    await this.panel?.webview.postMessage(message);
  }

  private async stagePreview(intent: PublicCommandIntent): Promise<void> {
    this.previewGate.invalidate();
    const bundle = await this.callbacks.preview(intent);
    this.previewGate.stage(this.panelId, intent, this.revision, bundle);
    await this.sendMessage({ type: "actionPreview", intent, bundle, revision: this.revision });
  }

  private invalidateRevision(): void {
    this.revision += 1;
    this.previewGate.invalidate();
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

function presentOperationError(error: unknown): { message: string; detail: string } {
  const detail = error instanceof Error ? error.message : String(error ?? "未知錯誤");
  if (/clipboard|剪貼簿/i.test(detail)) {
    return {
      message: "prompt 複製失敗；預覽仍保留，請檢查剪貼簿權限後再試一次。",
      detail
    };
  }
  if (/read-only diagnostic|critical contract|mutation public prompt/i.test(detail)) {
    return {
      message: "目前 workspace 有嚴重契約問題，已暫停 mutation prompt；請先在 Codex Chat 使用 status 確認，再回到這裡 Refresh。",
      detail
    };
  }
  if (/required|必要/i.test(detail)) {
    return {
      message: "請補齊公開操作的必要欄位，再重新預覽。",
      detail
    };
  }
  return {
    message: "DevWeave 操作未完成；請先查看下方技術詳情，確認 workspace 後再試一次。",
    detail
  };
}
