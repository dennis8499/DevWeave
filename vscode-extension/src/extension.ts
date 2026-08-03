import * as vscode from "vscode";
import { BootstrapBundle, BootstrapInstaller, BootstrapReport } from "./bootstrap";
import { ClipboardAdapter, VscodeClipboardAdapter } from "./clipboard";
import { DashboardPanel } from "./dashboard";
import { FileSystemPort } from "./filesystem";
import { ActionIntent, Diagnostic, PromptBundle, WorkspaceSnapshot } from "./model";
import { DevWeavePromptComposer } from "./prompt";
import { WorkspaceSnapshotReader } from "./snapshot";
import { WorkItemsTreeProvider } from "./tree";
import { readBootstrapBundle, VscodeBootstrapResourceReader, VscodeBootstrapWorkspace } from "./vscode-bootstrap";
import { VscodeFileSystemPort } from "./vscode-filesystem";

export function activate(context: vscode.ExtensionContext): void {
  const output = vscode.window.createOutputChannel("DevWeave Control Center");
  const controller = new ExtensionController(context, output);
  const tree = new WorkItemsTreeProvider();
  const dashboard = new DashboardPanel(context, {
    refresh: () => controller.refresh(),
    initialize: () => controller.initialize(),
    preview: (intent) => controller.preview(intent),
    copy: (intent) => controller.copy(intent),
    openFile: (path) => controller.openFile(path),
    selectWork: (workId) => controller.selectWork(workId),
    protocolError: (message) => output.appendLine(`[protocol] ${message}`)
  });
  controller.attach(tree, dashboard);

  context.subscriptions.push(
    output,
    tree,
    dashboard,
    vscode.window.registerTreeDataProvider("devweave.workItems", tree),
    vscode.commands.registerCommand("devweave.openDashboard", (workId?: string) => controller.openDashboard(workId)),
    vscode.commands.registerCommand("devweave.initialize", () => controller.initialize()),
    vscode.commands.registerCommand("devweave.refresh", () => controller.refresh()),
    vscode.commands.registerCommand("devweave.copyNextAction", () => controller.copyNextAction()),
    vscode.workspace.onDidChangeWorkspaceFolders(() => controller.handleWorkspaceFoldersChanged())
  );
  controller.startWatchers(context);
  void controller.refresh();
}

export function deactivate(): void {
  // All resources are owned by ExtensionContext subscriptions.
}

class ExtensionController {
  private tree: WorkItemsTreeProvider | undefined;
  private dashboard: DashboardPanel | undefined;
  private activeRoot: vscode.Uri | undefined;
  private snapshot: WorkspaceSnapshot = unavailableSnapshot("No workspace selected.");
  private selectedWorkId: string | null = null;
  private reader: WorkspaceSnapshotReader | undefined;
  private readonly composer = new DevWeavePromptComposer();
  private readonly bootstrapInstaller = new BootstrapInstaller();
  private refreshTimer: ReturnType<typeof setTimeout> | undefined;

  public constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly output: vscode.OutputChannel,
    private readonly clipboard: ClipboardAdapter = new VscodeClipboardAdapter()
  ) {}

  public attach(tree: WorkItemsTreeProvider, dashboard: DashboardPanel): void {
    this.tree = tree;
    this.dashboard = dashboard;
  }

  public startWatchers(context: vscode.ExtensionContext): void {
    const folders = vscode.workspace.workspaceFolders ?? [];
    if (folders.length === 0) {
      return;
    }
    for (const pattern of [".devweave/project.json", ".devweave/work-items/**", ".devweave/baseline/**", "wiki/**", ".codex/hooks.json", ".agents/skills/devweave/**"]) {
      for (const folder of folders) {
        const watcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(folder.uri, pattern));
        watcher.onDidChange(() => this.scheduleRefresh(), undefined, context.subscriptions);
        watcher.onDidCreate(() => this.scheduleRefresh(), undefined, context.subscriptions);
        watcher.onDidDelete(() => this.scheduleRefresh(), undefined, context.subscriptions);
        context.subscriptions.push(watcher);
      }
    }
  }

  public async refresh(): Promise<WorkspaceSnapshot> {
    const root = await this.resolveRoot(false);
    if (!root) {
      this.snapshot = unavailableSnapshot(this.multipleRootMessage());
    } else {
      this.activeRoot = root;
      const port: FileSystemPort = new VscodeFileSystemPort(root);
      this.reader = new WorkspaceSnapshotReader(port, {
        rootName: root.path.split("/").filter(Boolean).at(-1) ?? "Repository",
        rootPath: root.toString()
      });
      this.snapshot = await this.reader.readWorkspace();
      this.snapshot = { ...this.snapshot, selectedWorkId: this.selectedWorkId };
    }
    this.tree?.update(this.snapshot);
    await this.dashboard?.refresh(this.snapshot);
    return this.snapshot;
  }

  public async openDashboard(workId?: string): Promise<void> {
    const root = await this.resolveRoot(true);
    if (!root) {
      await vscode.window.showInformationMessage(this.multipleRootMessage());
      return;
    }
    if (workId) {
      this.selectedWorkId = workId;
    }
    const snapshot = await this.refresh();
    await this.dashboard?.show(snapshot, this.selectedWorkId ?? undefined);
  }

  public selectWork(workId: string | null): void {
    this.selectedWorkId = workId;
    this.snapshot = { ...this.snapshot, selectedWorkId: workId };
    this.tree?.update(this.snapshot);
  }

  public handleWorkspaceFoldersChanged(): void {
    this.activeRoot = undefined;
    this.selectedWorkId = null;
    void this.refresh();
  }

  public async preview(intent: ActionIntent): Promise<PromptBundle> {
    const snapshot = { ...this.snapshot, selectedWorkId: this.selectedWorkId };
    return this.composer.compose(intent, snapshot);
  }

  public async initialize(): Promise<{ report: BootstrapReport; snapshot: WorkspaceSnapshot }> {
    const root = await this.resolveRoot(true);
    if (!root) {
      const report = bootstrapFailure("workspace", this.multipleRootMessage());
      return { report, snapshot: this.snapshot };
    }
    const snapshot = await this.refresh();
    if (snapshot.projectExists) {
      if (snapshot.mutationBlocked) {
        const report = bootstrapConflict(snapshot.projectPath, "目前 project.json 存在但 snapshot 有 critical diagnostic；不會自動修復或覆寫既有內容。");
        await vscode.window.showErrorMessage("DevWeave workspace 有 conflict/diagnostic，初始化未執行。", "Open Dashboard");
        return { report, snapshot };
      }
      const report: BootstrapReport = {
        ok: true,
        status: "already_initialized",
        created: [],
        adopted: [],
        skipped: [],
        conflicts: [],
        errors: [],
        rolledBack: []
      };
      await vscode.window.showInformationMessage("目前 workspace 已完成 DevWeave 初始化。", "Open Dashboard");
      return { report, snapshot };
    }
    const confirmation = await vscode.window.showWarningMessage(
      "這會在目前 workspace 建立 DevWeave engine、skill、hook、project、baseline 與 Wiki starter。是否繼續？",
      { modal: true },
      "Initialize DevWeave",
      "Cancel"
    );
    if (confirmation !== "Initialize DevWeave") {
      const report = bootstrapFailure("workspace", "使用者取消初始化；repository 未寫入。");
      return { report, snapshot };
    }

    try {
      const resources = new VscodeBootstrapResourceReader(this.context.extensionUri);
      const bundle = await readBootstrapBundle(resources) as BootstrapBundle;
      const report = await this.bootstrapInstaller.install(bundle, resources, new VscodeBootstrapWorkspace(root));
      const refreshed = await this.refresh();
      this.output.appendLine(`[bootstrap] ${JSON.stringify(report)}`);
      if (report.ok) {
        await vscode.window.showInformationMessage("DevWeave 初始化完成；已重新整理 workspace snapshot。", "Open Dashboard");
      } else {
        await vscode.window.showErrorMessage("DevWeave 初始化未完成，請檢查 conflict/error 路徑。", "Open Dashboard");
      }
      return { report, snapshot: refreshed };
    } catch (error) {
      const report = bootstrapFailure("bootstrap", error instanceof Error ? error.message : String(error));
      const refreshed = await this.refresh();
      this.output.appendLine(`[bootstrap] ${JSON.stringify(report)}`);
      await vscode.window.showErrorMessage("DevWeave bootstrap bundle 無法載入，workspace 未宣稱初始化成功。", "Open Dashboard");
      return { report, snapshot: refreshed };
    }
  }

  public async copy(intent: ActionIntent): Promise<PromptBundle> {
    const bundle = await this.preview(intent);
    const snapshot = { ...this.snapshot, selectedWorkId: this.selectedWorkId };
    if (bundle.mutation && snapshot.mutationBlocked) {
      throw new Error("DevWeave snapshot is read-only because critical contract diagnostics are present. Copy doctor/status first.");
    }
    await this.clipboard.copy(bundle.chatText);
    await vscode.window.showInformationMessage("DevWeave prompt 已複製到 clipboard；請在 Codex Chat 審閱並送出。", "Open Dashboard");
    return bundle;
  }

  public async copyNextAction(): Promise<void> {
    const work = this.currentWork();
    if (!work) {
      await this.copy({ type: "status", all: true });
      return;
    }
    await this.copy({ type: "instructions", workId: work.id });
  }

  public async openFile(relativePath: string): Promise<void> {
    if (!this.activeRoot || !isSafeWorkspacePath(relativePath) || !isAllowedDevWeavePath(relativePath)) {
      throw new Error("File path is not safe or no repository is selected.");
    }
    const uri = vscode.Uri.joinPath(this.activeRoot, ...relativePath.replaceAll("\\", "/").split("/"));
    const document = await vscode.workspace.openTextDocument(uri);
    await vscode.window.showTextDocument(document, { preview: true });
  }

  private currentWork() {
    if (this.selectedWorkId) {
      return this.snapshot.workItems.find((work) => work.id === this.selectedWorkId);
    }
    return this.snapshot.workItems.length === 1 ? this.snapshot.workItems[0] : undefined;
  }

  private scheduleRefresh(): void {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
    }
    this.refreshTimer = setTimeout(() => {
      this.refreshTimer = undefined;
      void this.refresh();
    }, 250);
  }

  private async resolveRoot(promptForChoice: boolean): Promise<vscode.Uri | undefined> {
    if (this.activeRoot) {
      return this.activeRoot;
    }
    const folders = vscode.workspace.workspaceFolders ?? [];
    if (folders.length === 0) {
      return undefined;
    }
    if (folders.length === 1) {
      return folders[0].uri;
    }
    const managed = [];
    for (const folder of folders) {
      if (await vscode.workspace.fs.stat(vscode.Uri.joinPath(folder.uri, ".devweave", "project.json")).then(() => true, () => false)) {
        managed.push(folder);
      }
    }
    if (managed.length === 1) {
      return managed[0].uri;
    }
    if (!promptForChoice) {
      return undefined;
    }
    const picked = await vscode.window.showQuickPick(
      folders.map((folder) => ({ label: folder.name, description: folder.uri.toString(), uri: folder.uri })),
      { placeHolder: "選擇要開啟的 DevWeave repository" }
    );
    return picked?.uri;
  }

  private multipleRootMessage(): string {
    const count = vscode.workspace.workspaceFolders?.length ?? 0;
    return count > 1 ? "請先在 DevWeave Control Center 選擇一個 repository。" : "目前沒有可讀取的 VS Code workspace。";
  }
}

function unavailableSnapshot(message: string): WorkspaceSnapshot {
  const diagnostic: Diagnostic = { severity: "warning", code: "workspace_unavailable", message };
  return {
    capturedAt: new Date().toISOString(),
    rootName: null,
    rootPath: null,
    projectPath: ".devweave/project.json",
    projectExists: false,
    managed: null,
    schemaVersion: null,
    project: null,
    commands: [],
    verificationProfiles: {},
    baselineFiles: [],
    hookPresent: false,
    skillPresent: false,
    workItems: [],
    knowledge: {
      root: "wiki",
      health: "unknown",
      pages: [],
      placeholderPages: [],
      stalePages: [],
      critical: [],
      warnings: [diagnostic],
      affectedPages: [],
      pendingRefresh: [],
      planned: null
    },
    diagnostics: [diagnostic],
    mutationBlocked: false,
    source: "filesystem",
    authoritative: false,
    engineObservedAt: null,
    selectedWorkId: null
  };
}

function isSafeWorkspacePath(value: string): boolean {
  const normalized = value.replaceAll("\\", "/");
  return Boolean(normalized) && !normalized.startsWith("/") && !/^[A-Za-z]:/.test(normalized) && !normalized.split("/").includes("..");
}

function isAllowedDevWeavePath(value: string): boolean {
  const normalized = value.replaceAll("\\", "/");
  return normalized === ".devweave/project.json"
    || normalized.startsWith(".devweave/work-items/")
    || normalized.startsWith(".devweave/baseline/")
    || normalized.startsWith("wiki/")
    || normalized === ".codex/hooks.json"
    || normalized.startsWith(".agents/skills/devweave/");
}

function bootstrapFailure(path: string, reason: string): BootstrapReport {
  return {
    ok: false,
    status: "failed",
    created: [],
    adopted: [],
    skipped: [],
    conflicts: [],
    errors: [{ path, reason }],
    rolledBack: []
  };
}

function bootstrapConflict(path: string, reason: string): BootstrapReport {
  return {
    ok: false,
    status: "conflict",
    created: [],
    adopted: [],
    skipped: [],
    conflicts: [{ path, reason }],
    errors: [],
    rolledBack: []
  };
}
