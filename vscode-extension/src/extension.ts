import * as vscode from "vscode";
import { BootstrapBundle, BootstrapBundleFile, BootstrapInstaller, BootstrapReport } from "./bootstrap";
import { ClipboardAdapter, VscodeClipboardAdapter } from "./clipboard";
import { DashboardPanel } from "./dashboard";
import { FileSystemPort } from "./filesystem";
import { DashboardPreferences, Diagnostic, DisplayMode, PromptBundle, PublicCommandIntent, WorkspaceSnapshot } from "./model";
import { DevWeavePromptComposer } from "./prompt";
import { WorkspaceSnapshotReader } from "./snapshot";
import { RefreshCoordinator } from "./refresh-coordinator";
import { WorkItemsTreeProvider } from "./tree";
import { readBootstrapBundle, VscodeBootstrapResourceReader, VscodeBootstrapWorkspace } from "./vscode-bootstrap";
import { VscodeFileSystemPort } from "./vscode-filesystem";
import { resolveWorkSelection } from "./work-selection";

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
    getPreferences: () => controller.getPreferences(),
    setDisplayMode: (mode) => controller.setDisplayMode(mode),
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
    vscode.commands.registerCommand("devweave.wikiBootstrap", () => controller.previewWikiBootstrap()),
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
  private refreshCoordinator: RefreshCoordinator<WorkspaceSnapshot> | undefined;
  private bootstrapBundle: BootstrapBundle | undefined;
  private bootstrapBundlePromise: Promise<BootstrapBundle | undefined> | undefined;
  private readonly composer = new DevWeavePromptComposer();
  private readonly bootstrapInstaller = new BootstrapInstaller();
  private readonly preferencesKey = "devweave.controlCenter.preferences";
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
    for (const pattern of [".devweave/project.json", ".devweave/work-items/**", ".devweave/baseline/**", "wiki/**", ".codex/hooks.json", "AGENTS.md", "skills-lock.json", ".agents/skills/**"]) {
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
      this.tree?.update(this.snapshot);
      await this.dashboard?.refresh(this.snapshot);
      return this.snapshot;
    }
    const bundle = await this.loadBootstrapBundle();
    this.ensureRefreshCoordinator(
      root,
      bundle ? [...bundle.directories, ...bundle.files.map((file) => file.destination)] : undefined,
      bundle?.files
    );
    await this.refreshCoordinator?.request();
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
    this.selectedWorkId = resolveWorkSelection(this.snapshot, workId);
    this.snapshot = { ...this.snapshot, selectedWorkId: this.selectedWorkId };
    this.tree?.update(this.snapshot);
  }

  public handleWorkspaceFoldersChanged(): void {
    this.activeRoot = undefined;
    this.selectedWorkId = null;
    this.refreshCoordinator?.dispose();
    this.refreshCoordinator = undefined;
    this.reader = undefined;
    void this.refresh();
  }

  private ensureRefreshCoordinator(root: vscode.Uri, bootstrapPaths?: readonly string[], bootstrapFiles?: BootstrapBundleFile[]): void {
    if (this.activeRoot?.toString() === root.toString() && this.refreshCoordinator && this.reader) {
      return;
    }
    this.refreshCoordinator?.dispose();
    this.activeRoot = root;
    const port: FileSystemPort = new VscodeFileSystemPort(root);
    this.reader = new WorkspaceSnapshotReader(port, {
      rootName: root.path.split("/").filter(Boolean).at(-1) ?? "Repository",
      rootPath: root.toString(),
      bootstrapPaths,
      bootstrapFiles
    });
    this.refreshCoordinator = new RefreshCoordinator<WorkspaceSnapshot>({
      read: () => this.reader?.readWorkspace() ?? Promise.reject(new Error("Workspace snapshot reader is unavailable.")),
      publish: (next) => this.publishSnapshot(next),
      onError: (error) => this.output.appendLine(`[refresh] ${error instanceof Error ? error.message : String(error)}`)
    });
  }

  private publishSnapshot(next: WorkspaceSnapshot): void {
    this.snapshot = { ...next, selectedWorkId: resolveWorkSelection(next, this.selectedWorkId) };
    this.selectedWorkId = this.snapshot.selectedWorkId;
    this.tree?.update(this.snapshot);
    void this.dashboard?.refresh(this.snapshot);
  }

  private async loadBootstrapBundle(): Promise<BootstrapBundle | undefined> {
    if (this.bootstrapBundle) return this.bootstrapBundle;
    if (!this.bootstrapBundlePromise) {
      this.bootstrapBundlePromise = (async () => {
        try {
          const resources = new VscodeBootstrapResourceReader(this.context.extensionUri);
          const bundle = await readBootstrapBundle(resources);
          if (!isBootstrapBundle(bundle)) throw new Error("Bootstrap manifest is malformed.");
          this.bootstrapBundle = bundle;
          return bundle;
        } catch (error) {
          this.output.appendLine(`[bootstrap] manifest unavailable: ${error instanceof Error ? error.message : String(error)}`);
          return undefined;
        }
      })();
    }
    return this.bootstrapBundlePromise;
  }

  public async preview(intent: PublicCommandIntent): Promise<PromptBundle> {
    const snapshot = { ...this.snapshot, selectedWorkId: this.selectedWorkId };
    return this.composer.compose(intent, snapshot);
  }

  public getPreferences(): DashboardPreferences {
    const stored = this.context.workspaceState.get<Partial<DashboardPreferences>>(this.preferencesKey);
    return { displayMode: stored?.displayMode === "advanced" ? "advanced" : "concise" };
  }

  public async setDisplayMode(mode: DisplayMode): Promise<void> {
    await this.context.workspaceState.update(this.preferencesKey, { displayMode: mode });
  }

  public async initialize(): Promise<{ report: BootstrapReport; snapshot: WorkspaceSnapshot }> {
    const root = await this.resolveRoot(true);
    if (!root) {
      const report = bootstrapFailure("workspace", this.multipleRootMessage());
      return { report, snapshot: this.snapshot };
    }
    const snapshot = await this.refresh();
    if (snapshot.mutationBlocked) {
      const report = bootstrapConflict(snapshot.projectPath, "目前 project.json 存在但 snapshot 有 critical diagnostic；不會自動修復或覆寫既有內容。");
      await vscode.window.showErrorMessage("DevWeave workspace 有 conflict/diagnostic，初始化未執行。", "Open Dashboard");
      return { report, snapshot };
    }
    const resources = new VscodeBootstrapResourceReader(this.context.extensionUri);
    const bundle = await this.loadBootstrapBundle();
    if (!bundle) {
      const report = bootstrapFailure("manifest.json", "Bootstrap bundle manifest 無法載入；workspace 未寫入。");
      return { report, snapshot };
    }
    const workspace = new VscodeBootstrapWorkspace(root);
    const inspection = await this.bootstrapInstaller.inspect(bundle, resources, workspace);
    if (inspection.complete) {
      const report: BootstrapReport = {
        ok: true,
        complete: true,
        status: "already_initialized",
        created: [],
        adopted: inspection.adopted,
        skipped: inspection.skipped,
        missing: [],
        conflicts: [],
        errors: [],
        rolledBack: []
      };
      await vscode.window.showInformationMessage("目前 workspace 已完成 DevWeave 初始化。", "Open Dashboard");
      return { report, snapshot };
    }
    const isRepair = snapshot.projectExists;
    const confirmation = await vscode.window.showWarningMessage(
      isRepair
        ? `DevWeave control bundle 尚未完整（剩餘 ${inspection.missing.length + inspection.conflicts.length} 項）。這會只補齊無衝突缺檔，不覆寫既有不同內容。是否繼續？`
        : "這會在目前 workspace 建立 DevWeave control bundle、六組 skills、hook、project、baseline 與 Wiki starter。是否繼續？",
      { modal: true },
      "Initialize DevWeave",
      "Cancel"
    );
    if (confirmation !== "Initialize DevWeave") {
      const report = bootstrapFailure("workspace", "使用者取消初始化；repository 未寫入。");
      return { report, snapshot };
    }

    try {
      const report = await this.bootstrapInstaller.install(bundle, resources, workspace);
      const refreshed = await this.refresh();
      this.output.appendLine(`[bootstrap] ${JSON.stringify(report)}`);
      if (report.complete) {
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

  public async copy(intent: PublicCommandIntent): Promise<PromptBundle> {
    const bundle = await this.preview(intent);
    const snapshot = { ...this.snapshot, selectedWorkId: this.selectedWorkId };
    if (bundle.mutation && snapshot.mutationBlocked) {
      throw new Error("DevWeave snapshot is read-only because critical contract diagnostics are present. Use the status command form first.");
    }
    await this.copyBundle(bundle);
    return bundle;
  }

  public async copyNextAction(): Promise<void> {
    const work = this.currentWork();
    await this.copy({ type: "next", ...(work ? { workId: work.id } : {}) });
  }

  public async previewWikiBootstrap(): Promise<void> {
    const intent = { type: "wikiBootstrap" } as const;
    try {
      const bundle = await this.preview(intent);
      const warningText = bundle.warnings.length > 0
        ? `\n\n注意：${bundle.warnings.join(" ")}`
        : "";
      const confirmation = await vscode.window.showWarningMessage(
        `預覽 Codex Chat prompt：\n\n${bundle.chatText}${warningText}\n\nExtension 不會執行 CLI 或寫入 Wiki。`,
        { modal: true },
        "Copy prompt",
        "Cancel"
      );
      if (confirmation === "Copy prompt") {
        await this.copyBundle(bundle);
      }
    } catch (error) {
      await vscode.window.showErrorMessage(
        error instanceof Error ? error.message : "無法產生 Wiki bootstrap prompt。",
        "Open Dashboard"
      );
    }
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
    const active = this.snapshot.workItems.filter((work) => work.status === "active");
    return active.length === 1 ? active[0] : undefined;
  }

  private async copyBundle(bundle: PromptBundle): Promise<void> {
    await this.clipboard.copy(bundle.chatText);
    await vscode.window.showInformationMessage("DevWeave prompt 已複製到 clipboard；請在 Codex Chat 審閱並送出。", "Open Dashboard");
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
    if (!promptForChoice) {
      return undefined;
    }
    const choices = await Promise.all(folders.map(async (folder) => {
      const state = await this.readRootState(folder.uri);
      return {
        label: folder.name,
        description: `${state.label} · ${folder.uri.fsPath}`,
        detail: state.detail,
        uri: folder.uri
      };
    }));
    const picked = await vscode.window.showQuickPick(choices, {
      placeHolder: "選擇要開啟的 DevWeave repository（顯示 managed 狀態）"
    });
    return picked?.uri;
  }

  private async readRootState(uri: vscode.Uri): Promise<{ label: string; detail: string }> {
    const projectUri = vscode.Uri.joinPath(uri, ".devweave", "project.json");
    try {
      const bytes = await vscode.workspace.fs.readFile(projectUri);
      const project: unknown = JSON.parse(new TextDecoder().decode(bytes));
      const managed = isRecord(project) && typeof project.managed === "boolean" ? project.managed : null;
      return managed === true
        ? { label: "已管理", detail: "DevWeave managed workspace；可讀取 workflow snapshot。" }
        : managed === false
          ? { label: "未啟用 managed", detail: "已有 DevWeave 設定，但需要明確啟用。" }
          : { label: "設定不完整", detail: "project.json 存在，但 managed 欄位無法確認。" };
    } catch {
      return { label: "未初始化", detail: "找不到 .devweave/project.json；可選此 repository 進行初始化。" };
    }
  }

  private multipleRootMessage(): string {
    const count = vscode.workspace.workspaceFolders?.length ?? 0;
    return count > 1 ? "請先在 DevWeave Control Center 選擇一個 repository。" : "目前沒有可讀取的 VS Code workspace。";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isBootstrapBundle(value: unknown): value is BootstrapBundle {
  return isRecord(value)
    && value.schemaVersion === 1
    && typeof value.bundleVersion === "string"
    && Array.isArray(value.directories)
    && Array.isArray(value.files)
    && value.files.every((file) => isRecord(file) && typeof file.destination === "string" && typeof file.source === "string");
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
    bootstrap: { complete: false, expected: [], missing: [], conflicts: [] },
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
      coveredChangedPaths: [],
      uncoveredChangedPaths: [],
      bootstrap: {
        complete: false,
        recommended: true,
        reasons: ["overview_not_ready", "architecture_missing", "module_missing"],
        overview: null,
        architecturePages: [],
        modulePages: []
      },
      review: {
        required: false,
        current: false,
        disposition: null,
        rationale: "",
        affectedPages: [],
        coveredChangedPaths: [],
        uncoveredChangedPaths: [],
        changeFingerprint: null,
        recordedAt: null,
        invalidatedAt: null
      },
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
    || normalized === "AGENTS.md"
    || normalized === "skills-lock.json"
    || normalized.startsWith(".agents/skills/");
}

function bootstrapFailure(path: string, reason: string): BootstrapReport {
  return {
    ok: false,
    complete: false,
    status: "failed",
    created: [],
    adopted: [],
    skipped: [],
    missing: [],
    conflicts: [],
    errors: [{ path, reason }],
    rolledBack: []
  };
}

function bootstrapConflict(path: string, reason: string): BootstrapReport {
  return {
    ok: false,
    complete: false,
    status: "conflict",
    created: [],
    adopted: [],
    skipped: [],
    missing: [],
    conflicts: [{ path, reason }],
    errors: [],
    rolledBack: []
  };
}
