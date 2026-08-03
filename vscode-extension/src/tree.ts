import * as vscode from "vscode";
import { WorkItemProjection, WorkspaceSnapshot } from "./model";

export type TreeNode =
  | { kind: "repository"; label: string }
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

    const work = element.work;
    const item = new vscode.TreeItem(work.title, vscode.TreeItemCollapsibleState.None);
    item.description = `${work.phase} · ${work.risk}`;
    item.tooltip = `${work.id}\n${work.phase}\n${work.status}`;
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
    if (element) {
      return [];
    }
    const repository = this.snapshot.rootName ?? "Repository selection required";
    const workItems = this.snapshot.workItems.map((work) => ({ kind: "work" as const, work }));
    return [{ kind: "repository", label: repository }, ...workItems];
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
