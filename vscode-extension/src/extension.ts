import * as vscode from "vscode";
import { BootstrapBundle, BootstrapBundleFile, BootstrapInstaller, BootstrapReport } from "./bootstrap";
import { ClipboardAdapter, VscodeClipboardAdapter } from "./clipboard";
import { DashboardPanel } from "./dashboard";
import { FileSystemPort } from "./filesystem";
import { DashboardPreferences, Diagnostic, DisplayMode, PromptBundle, PublicCommandIntent, WorkspaceSnapshot } from "./model";
import { DevWeavePromptComposer } from "./prompt";
import { WorkspaceSnapshotReader } from "./snapshot";
import { RefreshCoordinator } from "./refresh-coordinator";
import type { RefreshChangeSet } from "./refresh-coordinator";
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
    copy: (bundle) => controller.copyBundle(bundle),
    copySuccess: () => controller.notifyCopySuccess(),
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
  private snapshot: WorkspaceSnapshot = unavailableSnapshot("尚未選擇 workspace。");
  private selectedWorkId: string | null = null;
  private reader: WorkspaceSnapshotReader | undefined;
  private refreshCoordinator: RefreshCoordinator<WorkspaceSnapshot> | undefined;
  private bootstrapBundle: BootstrapBundle | undefined;
  private bootstrapBundlePromise: Promise<BootstrapBundle | undefined> | undefined;
  private readonly composer = new DevWeavePromptComposer();
  private readonly bootstrapInstaller = new BootstrapInstaller();
  private readonly preferencesKey = "devweave.controlCenter.preferences";
  private refreshTimer: ReturnType<typeof setTimeout> | undefined;
  private bootstrapTransaction = false;

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
        watcher.onDidChange((uri) => this.scheduleRefresh(uri), undefined, context.subscriptions);
        watcher.onDidCreate((uri) => this.scheduleRefresh(uri), undefined, context.subscriptions);
        watcher.onDidDelete((uri) => this.scheduleRefresh(uri), undefined, context.subscriptions);
        context.subscriptions.push(watcher);
      }
    }
  }

  public async refresh(changes: Partial<RefreshChangeSet> = { forceFull: true }): Promise<WorkspaceSnapshot> {
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
      bundle?.directories,
      bundle?.files
    );
    await this.refreshCoordinator?.request(changes);
    return this.snapshot;
  }

  public async openDashboard(workId?: string): Promise<void> {
    const root = await this.resolveRoot(true);
    if (!root) {
      await vscode.window.showInformationMessage(this.multipleRootMessage());
      return;
    }
    this.activeRoot = root;
    if (workId) {
      this.selectedWorkId = workId;
    }
    const snapshot = await this.refresh();
    const selectedSnapshot = workId ? await this.selectWork(workId) : snapshot;
    await this.dashboard?.show(selectedSnapshot, this.selectedWorkId ?? undefined);
  }

  public async selectWork(workId: string | null): Promise<WorkspaceSnapshot> {
    this.selectedWorkId = resolveWorkSelection(this.snapshot, workId);
    if (this.selectedWorkId && this.reader) {
      const detail = await this.reader.readWorkItemDetail(this.selectedWorkId);
      if (detail) {
        this.snapshot = {
          ...this.snapshot,
          workItems: this.snapshot.workItems.map((item) => item.id === detail.id ? detail : item),
          selectedWorkId: this.selectedWorkId
        };
      } else {
        this.snapshot = { ...this.snapshot, selectedWorkId: this.selectedWorkId };
      }
    } else {
      this.snapshot = { ...this.snapshot, selectedWorkId: this.selectedWorkId };
    }
    this.tree?.update(this.snapshot);
    return this.snapshot;
  }

  public handleWorkspaceFoldersChanged(): void {
    this.activeRoot = undefined;
    this.selectedWorkId = null;
    this.refreshCoordinator?.dispose();
    this.refreshCoordinator = undefined;
    this.reader = undefined;
    void this.refresh();
  }

  private ensureRefreshCoordinator(root: vscode.Uri, bootstrapDirectories?: readonly string[], bootstrapFiles?: BootstrapBundleFile[]): void {
    if (this.activeRoot?.toString() === root.toString() && this.refreshCoordinator && this.reader) {
      return;
    }
    this.refreshCoordinator?.dispose();
    this.activeRoot = root;
    const port: FileSystemPort = new VscodeFileSystemPort(root);
    this.reader = new WorkspaceSnapshotReader(port, {
      rootName: root.path.split("/").filter(Boolean).at(-1) ?? "Repository",
      rootPath: root.toString(),
      bootstrapDirectories,
      bootstrapFiles,
      initialReadMode: "summary"
    });
    this.refreshCoordinator = new RefreshCoordinator<WorkspaceSnapshot>({
      read: (changes) => this.reader?.readWorkspace(changes) ?? Promise.reject(new Error("Workspace snapshot reader is unavailable.")),
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
    this.activeRoot = root;
    const snapshot = await this.refresh();
    if (snapshot.mutationBlocked) {
      const report = bootstrapConflict(snapshot.projectPath, "目前 project.json 存在但 snapshot 有 critical diagnostic；不會自動修復或覆寫既有內容。");
      await vscode.window.showErrorMessage("DevWeave workspace 有衝突或嚴重問題，初始化未執行。", "開啟控制中心");
      return { report, snapshot };
    }
    const resources = new VscodeBootstrapResourceReader(this.context.extensionUri);
    const bundle = await this.loadBootstrapBundle();
    if (!bundle) {
      const report = bootstrapFailure("manifest.json", "Bootstrap bundle manifest 無法載入；workspace 未寫入。");
      return { report, snapshot };
    }
    const workspace = new VscodeBootstrapWorkspace(root);
    const preparation = await this.bootstrapInstaller.prepare(bundle, resources, workspace);
    const inspection = this.bootstrapInstaller.inspectPrepared(preparation);
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
      await vscode.window.showInformationMessage("目前 workspace 已完成 DevWeave 初始化。", "開啟控制中心");
      return { report, snapshot };
    }
    const isRepair = snapshot.projectExists;
    const confirmation = await vscode.window.showWarningMessage(
      isRepair
        ? `DevWeave control bundle 尚未完整（剩餘 ${inspection.missing.length + inspection.conflicts.length} 項）。這會只補齊無衝突缺檔，不覆寫既有不同內容。是否繼續？`
        : "這會在目前 workspace 建立 DevWeave control bundle、六組 skills、hook、project、baseline 與 Wiki starter。是否繼續？",
      { modal: true },
      "繼續初始化",
      "取消"
    );
    if (confirmation !== "繼續初始化") {
      const report = bootstrapFailure("workspace", "使用者取消初始化；repository 未寫入。");
      return { report, snapshot };
    }

    try {
      this.bootstrapTransaction = true;
      const report = await this.bootstrapInstaller.installPrepared(preparation, workspace);
      this.bootstrapTransaction = false;
      const refreshed = await this.refresh();
      this.output.appendLine(`[bootstrap] ${JSON.stringify(report)}`);
      if (report.complete) {
        await vscode.window.showInformationMessage("DevWeave 初始化完成；已重新整理 workspace 檔案快照。", "開啟控制中心");
      } else {
        await vscode.window.showErrorMessage("DevWeave 初始化未完成，請檢查衝突或錯誤路徑。", "開啟控制中心");
      }
      return { report, snapshot: refreshed };
    } catch (error) {
      this.bootstrapTransaction = false;
      const report = bootstrapFailure("bootstrap", error instanceof Error ? error.message : String(error));
      const refreshed = await this.refresh();
      this.output.appendLine(`[bootstrap] ${JSON.stringify(report)}`);
      await vscode.window.showErrorMessage("DevWeave bootstrap bundle 無法載入，workspace 未宣稱初始化成功。", "開啟控制中心");
      return { report, snapshot: refreshed };
    }
  }

  public async copyNextAction(): Promise<void> {
    const root = await this.resolveRoot(true);
    if (!root) {
      await vscode.window.showInformationMessage(this.multipleRootMessage());
      return;
    }
    this.activeRoot = root;

    const snapshot = await this.refresh();
    const activeWorks = snapshot.workItems.filter((work) => work.status === "active");
    const selectedActiveWork = this.selectedWorkId
      ? activeWorks.find((work) => work.id === this.selectedWorkId)
      : undefined;
    const work = activeWorks.length === 1 ? activeWorks[0] : selectedActiveWork;

    if (!work) {
      await this.dashboard?.show(snapshot, this.selectedWorkId ?? undefined);
      await vscode.window.showInformationMessage(
        activeWorks.length === 0
          ? "目前沒有 active work；請先建立或選取 work，再預覽下一步。"
          : "目前有多個 active work；請先在控制中心選取 work，再預覽下一步。"
      );
      return;
    }

    this.selectedWorkId = work.id;
    const selectedSnapshot = { ...snapshot, selectedWorkId: work.id };
    await this.dashboard?.show(selectedSnapshot, work.id);
    await this.dashboard?.previewAction({ type: "next", workId: work.id });
  }

  public async previewWikiBootstrap(): Promise<void> {
    const intent = { type: "wikiBootstrap" } as const;
    try {
      const root = await this.resolveRoot(true);
      if (!root) {
        await vscode.window.showInformationMessage(this.multipleRootMessage());
        return;
      }
      this.activeRoot = root;
      const snapshot = await this.refresh();
      await this.dashboard?.show(snapshot, this.selectedWorkId ?? undefined);
      await this.dashboard?.previewAction(intent);
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error ?? "未知錯誤");
      this.output.appendLine(`[wiki-bootstrap] ${detail}`);
      await vscode.window.showErrorMessage(
        "無法在控制中心產生 Wiki bootstrap prompt 預覽；請先確認 workspace，再重新整理。",
        "開啟控制中心"
      );
    }
  }

  public async openFile(relativePath: string): Promise<void> {
    if (!this.activeRoot || !isSafeWorkspacePath(relativePath) || !isAllowedDevWeavePath(relativePath)) {
      throw new Error("檔案路徑不安全，或尚未選擇 repository。");
    }
    const uri = vscode.Uri.joinPath(this.activeRoot, ...relativePath.replaceAll("\\", "/").split("/"));
    const document = await vscode.workspace.openTextDocument(uri);
    await vscode.window.showTextDocument(document, { preview: true });
  }

  public async copyBundle(bundle: PromptBundle): Promise<PromptBundle> {
    const snapshot = { ...this.snapshot, selectedWorkId: this.selectedWorkId };
    if (bundle.mutation && snapshot.mutationBlocked) {
      throw new Error("目前 workspace 有 critical contract 問題，只能查看；請先使用 status 確認後再重新整理。");
    }
    await this.clipboard.copy(bundle.chatText);
    return bundle;
  }

  public async notifyCopySuccess(): Promise<void> {
    await vscode.window.showInformationMessage("DevWeave prompt 已複製到剪貼簿；請在 Codex Chat 審閱並送出。", "開啟控制中心");
  }

  private pendingRefreshPaths = new Set<string>();
  private pendingRefreshForceFull = false;

  private scheduleRefresh(uri?: vscode.Uri): void {
    if (this.bootstrapTransaction) {
      return;
    }
    const relativePath = uri ? this.relativeWorkspacePath(uri) : undefined;
    if (relativePath) {
      this.pendingRefreshPaths.add(relativePath);
    } else {
      this.pendingRefreshForceFull = true;
    }
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
    }
    this.refreshTimer = setTimeout(() => {
      this.refreshTimer = undefined;
      const changes = {
        paths: [...this.pendingRefreshPaths].sort(),
        forceFull: this.pendingRefreshForceFull
      } satisfies RefreshChangeSet;
      this.pendingRefreshPaths.clear();
      this.pendingRefreshForceFull = false;
      void this.refresh(changes);
    }, 250);
  }

  private relativeWorkspacePath(uri: vscode.Uri): string | undefined {
    const root = this.activeRoot;
    if (!root || uri.scheme !== root.scheme) {
      return undefined;
    }
    const rootPath = root.path.replace(/\/$/, "");
    if (!uri.path.startsWith(`${rootPath}/`)) {
      return undefined;
    }
    return uri.path.slice(rootPath.length + 1).replaceAll("\\", "/");
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
    bootstrap: { complete: false, expected: [], missing: [], conflicts: [], pathKinds: {}, conflictReasons: {} },
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
    engineGateStatus: "unavailable",
    projectionReadiness: "attention",
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
