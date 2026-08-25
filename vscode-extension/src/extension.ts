import { randomBytes } from "node:crypto";

import * as vscode from "vscode";

import { CodexAppServerSession } from "./app-server/session";
import { HostBridgeClient } from "./controller/host-bridge-client";
import { WorkspaceController, type ControllerState } from "./controller/workspace-controller";
import type { PendingDecision, ReviewFinding, RiskLevel } from "./v2/contracts";
import { projectUiState } from "./ui/projection";
import { parseUiIntent, type UiIntent } from "./ui/protocol";

let activeRuntime: ExtensionRuntime | undefined;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  const workspace = vscode.workspace.workspaceFolders?.[0];
  if (!workspace) return;
  const runtime = new ExtensionRuntime(context, workspace.uri);
  activeRuntime = runtime;
  context.subscriptions.push(runtime);
  await runtime.activate();
}

export async function deactivate(): Promise<void> {
  await activeRuntime?.shutdown();
  activeRuntime = undefined;
}

class ExtensionRuntime implements vscode.Disposable {
  private readonly host = new HostBridgeClient();
  private readonly appServer = new CodexAppServerSession();
  private readonly controller: WorkspaceController;
  private readonly tree = new RunTreeProvider();
  private dashboard: ControlCenterPanel | undefined;
  private hostConnected = false;
  private disposed = false;

  public constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly workspace: vscode.Uri
  ) {
    this.controller = new WorkspaceController(workspace.fsPath, this.host, this.appServer);
    this.controller.subscribe((state) => {
      this.tree.update(state);
      this.dashboard?.update(state);
    });
  }

  public async activate(): Promise<void> {
    this.context.subscriptions.push(
      vscode.window.createTreeView("devweave.runs", { treeDataProvider: this.tree }),
      vscode.commands.registerCommand("devweave.openControlCenter", () => this.openDashboard()),
      vscode.commands.registerCommand("devweave.startRun", () => this.openDashboard()),
      vscode.commands.registerCommand("devweave.resumeRun", () => this.resumePrompt()),
      vscode.commands.registerCommand("devweave.steer", () => this.steerPrompt()),
      vscode.commands.registerCommand("devweave.interrupt", () => this.guard(() => this.controller.interrupt())),
      vscode.commands.registerCommand("devweave.cancel", () => this.cancelPrompt())
    );
    this.tree.update(this.controller.state);
  }

  public dispose(): void {
    void this.shutdown();
  }

  public async shutdown(): Promise<void> {
    if (this.disposed) return;
    this.disposed = true;
    this.dashboard?.dispose();
    await Promise.allSettled([this.appServer.close(), this.host.close()]);
  }

  private openDashboard(): void {
    if (!this.dashboard) {
      this.dashboard = new ControlCenterPanel(this.context.extensionUri, this.controller, (intent) => this.handleIntent(intent));
      this.dashboard.onDispose(() => { this.dashboard = undefined; });
    }
    this.dashboard.reveal();
    this.dashboard.update(this.controller.state);
  }

  private async handleIntent(intent: UiIntent): Promise<void> {
    await this.guard(async () => {
      if (intent.type === "start") {
        await this.ensureHost();
        const draft = await this.createDraft(intent.goal, intent.scope, intent.risk);
        const codexPath = this.codexPath();
        await this.controller.startRun({ draft, slug: slug(intent.goal), ...(codexPath ? { codex_path: codexPath } : {}) });
      } else if (intent.type === "resume") {
        await this.ensureHost();
        await this.controller.resumeRun(intent.runId, this.codexPath(), intent.threadId);
      } else if (intent.type === "turn") {
        await this.controller.startTurn(intent.text);
      } else if (intent.type === "steer") {
        await this.controller.steer(intent.text);
      } else if (intent.type === "interrupt") {
        await this.controller.interrupt();
      } else if (intent.type === "cancel") {
        await this.controller.cancel();
      } else if (intent.type === "approval") {
        await this.controller.resolveApproval(intent.requestId, intent.decision);
      } else if (intent.type === "decision") {
        const decision = pendingDecision(this.controller.state.run, intent.decisionId);
        await this.controller.decide(decision, intent.optionId, intent.other);
      } else if (intent.type === "gate") {
        await this.controller.decideGate(intent.gateId, intent.approve, this.controller.state.review ?? undefined);
      } else if (intent.type === "review") {
        await this.runReview();
      } else if (intent.type === "refresh") {
        await this.controller.refreshRun(this.codexPath());
      }
    });
  }

  private async ensureHost(): Promise<void> {
    if (this.hostConnected) return;
    const python = vscode.workspace.getConfiguration("devweave", this.workspace).get<string>("pythonPath", "python");
    const script = vscode.Uri.joinPath(
      this.workspace,
      ".agents", "skills", "devweave", "scripts", "devweave_v2_host.py"
    ).fsPath;
    await this.host.connect(python, script, this.workspace.fsPath);
    this.hostConnected = true;
  }

  private codexPath(): string | undefined {
    const configured = vscode.workspace.getConfiguration("devweave", this.workspace).get<string>("codexPath", "").trim();
    return configured || undefined;
  }

  private async createDraft(goal: string, scope: string, risk: RiskLevel): Promise<Record<string, unknown>> {
    const normalizedScope = scope.replaceAll("\\", "/").trim();
    if (!normalizedScope || normalizedScope.startsWith("/") || normalizedScope.split("/").includes("..")) {
      throw new Error("Scope must be a normalized repository-relative path or pattern.");
    }
    const projectUri = vscode.Uri.joinPath(this.workspace, ".devweave", "project.json");
    const project = JSON.parse(new TextDecoder().decode(await vscode.workspace.fs.readFile(projectUri))) as Record<string, unknown>;
    if (project.schema_version !== 2 || typeof project.verification_plan !== "object" || project.verification_plan === null) {
      throw new Error("DevWeave schema-v2 project configuration is required before starting a run.");
    }
    const runId = `${utcStamp()}-${slug(goal)}`.slice(0, 120);
    return {
      schema_version: 2,
      run_id: runId,
      revision: 1,
      goal: goal.trim(),
      scope: [normalizedScope],
      non_goals: ["No push, pull request, merge, reset, or automatic branch switch."],
      requirements: ["REQ-DRAFT-001"],
      acceptance_criteria: ["AC-DRAFT-001"],
      decisions: [{ decision_id: "DEC-DRAFT-001", summary: "Agent must refine this seed plan before its planning Gate." }],
      tasks: [{
        task_id: "TASK-001",
        title: "Refine and implement the governed vertical slice",
        requirement_ids: ["REQ-DRAFT-001"],
        acceptance_ids: ["AC-DRAFT-001"],
        declared_paths: [normalizedScope],
        dependencies: []
      }],
      verification_plan: project.verification_plan,
      risk,
      risk_rationale: `User selected ${risk} risk; engine escalation remains authoritative.`
    };
  }

  private async runReview(): Promise<void> {
    const outcome = await this.controller.reviewForAcceptance(async (round, findings) => {
      const summaries = findings.map((item) => `${item.finding_id}: ${item.summary}`).join("\n");
      const turnId = await this.controller.startTurn(
        `Resolve review round ${round} findings, run the frozen verification plan, and request completion again.\n${summaries}`
      );
      if (!turnId || !this.appServer.waitForTurnCompleted) throw new Error("Fix turn could not be observed.");
      await this.appServer.waitForTurnCompleted(turnId);
      await this.controller.refreshRun(this.codexPath());
      const verification = record(record(this.controller.state.run).verification);
      if (verification.status !== "passed") throw new Error("Fix round did not produce current successful verification.");
    });
    if (outcome.status === "blocked") {
      throw new Error("Detached review remains blocked after its bounded rounds.");
    }
  }

  private async resumePrompt(): Promise<void> {
    const runId = await vscode.window.showInputBox({ title: "Resume DevWeave run", prompt: "Run ID", ignoreFocusOut: true });
    if (!runId) return;
    await this.guard(async () => {
      await this.ensureHost();
      await this.controller.resumeRun(runId, this.codexPath());
      this.openDashboard();
    });
  }

  private async steerPrompt(): Promise<void> {
    const text = await vscode.window.showInputBox({ title: "Steer active Codex turn", prompt: "Additional instruction", ignoreFocusOut: true });
    if (text) await this.guard(() => this.controller.steer(text));
  }

  private async cancelPrompt(): Promise<void> {
    const answer = await vscode.window.showWarningMessage("Cancel the active DevWeave run?", { modal: true }, "Cancel run");
    if (answer === "Cancel run") await this.guard(() => this.controller.cancel());
  }

  private async guard(action: () => Promise<unknown>): Promise<void> {
    try {
      await action();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      await vscode.window.showErrorMessage(`DevWeave: ${message}`);
    }
  }
}

class ControlCenterPanel implements vscode.Disposable {
  private readonly panel: vscode.WebviewPanel;
  private readonly disposables: vscode.Disposable[] = [];
  private disposeListener: (() => void) | undefined;

  public constructor(
    extensionUri: vscode.Uri,
    private readonly controller: WorkspaceController,
    onIntent: (intent: UiIntent) => Promise<void>
  ) {
    this.panel = vscode.window.createWebviewPanel(
      "devweave.controlCenter",
      "DevWeave Control Center",
      vscode.ViewColumn.Active,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.joinPath(extensionUri, "dist")]
      }
    );
    this.panel.webview.html = webviewHtml(this.panel.webview, extensionUri);
    this.disposables.push(
      this.panel.onDidDispose(() => this.disposeListener?.()),
      this.panel.webview.onDidReceiveMessage(async (value: unknown) => {
        const intent = parseUiIntent(value);
        if (!intent) {
          await vscode.window.showErrorMessage("DevWeave rejected an invalid Control Center message.");
          return;
        }
        await onIntent(intent);
      })
    );
  }

  public reveal(): void { this.panel.reveal(vscode.ViewColumn.Active); }

  public update(state: ControllerState): void {
    void this.panel.webview.postMessage({ type: "state", state: projectUiState(state) });
  }

  public onDispose(listener: () => void): void { this.disposeListener = listener; }

  public dispose(): void {
    for (const disposable of this.disposables.splice(0)) disposable.dispose();
    this.panel.dispose();
  }
}

class RunTreeProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
  private readonly changed = new vscode.EventEmitter<void>();
  private state: ControllerState | undefined;
  public readonly onDidChangeTreeData = this.changed.event;

  public update(state: ControllerState): void {
    this.state = state;
    this.changed.fire();
  }

  public getTreeItem(element: vscode.TreeItem): vscode.TreeItem { return element; }

  public getChildren(): vscode.TreeItem[] {
    if (!this.state?.run) return [treeItem("No active run", "Open Control Center to start")];
    const run = this.state.run;
    return [
      treeItem(String(run.run_id ?? "Unknown run"), `Run · ${String(run.status ?? this.state.status)}`),
      treeItem(this.state.threadId || "No thread", `Thread · ${this.state.appServer.connection}`),
      treeItem(String(record(run.verification).status ?? "pending"), "Verification"),
      treeItem(String(record(run.review).status ?? "pending"), "Review")
    ];
  }
}

function treeItem(label: string, description: string): vscode.TreeItem {
  const item = new vscode.TreeItem(label);
  item.description = description;
  item.command = { command: "devweave.openControlCenter", title: "Open Control Center" };
  return item;
}

function webviewHtml(webview: vscode.Webview, extensionUri: vscode.Uri): string {
  const nonce = randomBytes(18).toString("base64");
  const script = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, "dist", "webview", "main.js"));
  const styles = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, "dist", "webview", "styles.css"));
  return `<!doctype html><html lang="en"><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${webview.cspSource} data:; style-src ${webview.cspSource}; script-src 'nonce-${nonce}';">
    <link rel="stylesheet" href="${styles}"><title>DevWeave Control Center</title></head>
    <body><div id="app" aria-busy="false"><p>Connecting to DevWeave…</p></div><script nonce="${nonce}" src="${script}"></script></body></html>`;
}

function pendingDecision(run: Record<string, unknown> | null, decisionId: string): PendingDecision {
  const value = record(record(run).pending_decision);
  if (value.decision_id !== decisionId) throw new Error("Pending decision is stale or unavailable.");
  return value as unknown as PendingDecision;
}

function slug(value: string): string {
  return value.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40) || "run";
}

function utcStamp(): string {
  return new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 14);
}

function record(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
