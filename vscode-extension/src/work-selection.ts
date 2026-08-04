import type { WorkspaceSnapshot } from "./model";

/**
 * Resolve an implicit dashboard selection without turning closed history into
 * the current work. An explicitly selected closed item remains browseable.
 */
export function resolveWorkSelection(snapshot: WorkspaceSnapshot, selectedWorkId: string | null | undefined): string | null {
  if (selectedWorkId && snapshot.workItems.some((item) => item.id === selectedWorkId)) {
    return selectedWorkId;
  }
  const active = snapshot.workItems.filter((item) => item.status === "active");
  return active.length === 1 ? active[0].id : null;
}

export function groupWorkItems(snapshot: WorkspaceSnapshot): { active: WorkspaceSnapshot["workItems"]; closed: WorkspaceSnapshot["workItems"] } {
  return {
    active: snapshot.workItems.filter((item) => item.status === "active"),
    closed: snapshot.workItems.filter((item) => item.status === "closed")
  };
}
