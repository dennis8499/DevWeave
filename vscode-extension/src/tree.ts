import * as vscode from "vscode";
import { WorkItemProjection, WorkspaceSnapshot } from "./model";
import { presentPhase, presentRisk, presentStatus } from "./presentation";
import { groupWorkItems } from "./work-selection";

export type TreeNode =
  | { kind: "repository"; label: string }
  | { kind: "group"; group: "active" | "closed" }
  | { kind: "work"; work: WorkItemProjection };

export class WorkItemsTreeProvider implements vscode.TreeDataProvider<TreeNode> {
  private readonly changed = new vscode.EventEmitter<TreeNode | undefined | null | void>();
  public readonly onDidChangeTreeData = this.changed.event;
  private snapshot: WorkspaceSnapshot | null = null;

  public update(snapshot: WorkspaceSnapshot): void {
    this.snapshot = snapshot;
    this.changed.fire();
  }

  public getTreeItem(element: TreeNode): vscode.TreeItem {
    if (element.kind === "repository") {
      const item = new vscode.TreeItem(element.label, vscode.TreeItemCollapsibleState.Expanded);
      item.iconPath = new vscode.ThemeIcon("repo");
      item.contextValue = "devweave.repository";
      item.command = {
        command: "devweave.openDashboard",
        title: "Open DevWeave Control Center"
      };
      return item;
    }

    if (element.kind === "group") {
      const groups = this.snapshot ? groupWorkItems(this.snapshot) : { active: [], closed: [] };
      const items = groups[element.group];
      const item = new vscode.TreeItem(
        element.group === "active" ? "進行中的工作" : "已結束的歷史",
        element.group === "active" ? vscode.TreeItemCollapsibleState.Expanded : vscode.TreeItemCollapsibleState.Collapsed
      );
      item.description = `${items.length} 個`;
      item.contextValue = `devweave.${element.group}WorkGroup`;
      item.iconPath = new vscode.ThemeIcon(element.group === "active" ? "pulse" : "history");
      return item;
    }

    const work = element.work;
    const item = new vscode.TreeItem(work.title, vscode.TreeItemCollapsibleState.None);
    item.description = `${presentPhase(work.phase)} · ${presentStatus(work.status)} · ${presentRisk(work.risk)}`;
    item.tooltip = `${work.id}\n${presentPhase(work.phase)}\n${presentStatus(work.status)}`;
    item.iconPath = new vscode.ThemeIcon(iconForWork(work));
    item.contextValue = work.status === "closed" ? "devweave.closedWork" : "devweave.work";
    item.command = {
      command: "devweave.openDashboard",
      title: "Open DevWeave Work Item",
      arguments: [work.id]
    };
    return item;
  }

  public getChildren(element?: TreeNode): TreeNode[] {
    if (!this.snapshot) {
      return [];
    }
    if (!element) {
      const repository = this.snapshot.rootName ?? "需要選擇 repository";
      return [{ kind: "repository", label: repository }];
    }
    if (element.kind === "repository") {
      return [
        { kind: "group", group: "active" },
        { kind: "group", group: "closed" }
      ];
    }
    if (element.kind === "group") {
      const groups = groupWorkItems(this.snapshot);
      return groups[element.group]
        .map((work) => ({ kind: "work" as const, work }));
    }
    if (element.kind === "work") {
      return [];
    }
    return [];
  }

  public dispose(): void {
    this.changed.dispose();
  }
}

function iconForWork(work: WorkItemProjection): string {
  if (work.blocker) {
    return "error";
  }
  if (work.status === "closed") {
    return "pass-filled";
  }
  if (work.gates.acceptance.status === "approved") {
    return "check-all";
  }
  if (work.gates.build.status === "approved") {
    return "tools";
  }
  if (work.gates.scope.status === "approved") {
    return "list-ordered";
  }
  return "circle-outline";
}
