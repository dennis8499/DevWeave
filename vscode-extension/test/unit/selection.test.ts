import assert from "node:assert/strict";
import test from "node:test";
import type { WorkItemProjection, WorkspaceSnapshot } from "../../src/model";
import { groupWorkItems, resolveWorkSelection } from "../../src/work-selection";

function item(id: string, status: "active" | "closed"): WorkItemProjection {
  return { id, title: id, status } as WorkItemProjection;
}

function snapshot(workItems: WorkItemProjection[]): WorkspaceSnapshot {
  return { workItems } as WorkspaceSnapshot;
}

test("selection never promotes closed history to the implicit current work", () => {
  assert.equal(resolveWorkSelection(snapshot([item("closed-1", "closed")]), null), null);
  assert.equal(resolveWorkSelection(snapshot([item("active-1", "active"), item("closed-1", "closed")]), null), "active-1");
  assert.equal(resolveWorkSelection(snapshot([item("active-1", "active"), item("closed-1", "closed")]), "closed-1"), "closed-1");
});

test("multiple active works require an explicit choice", () => {
  assert.equal(resolveWorkSelection(snapshot([item("active-1", "active"), item("active-2", "active")]), null), null);
  assert.equal(resolveWorkSelection(snapshot([item("active-1", "active"), item("active-2", "active")]), "missing"), null);
  assert.equal(resolveWorkSelection(snapshot([item("active-1", "active"), item("active-2", "active")]), "active-2"), "active-2");
  console.log("[walkthrough] multi-active implicit-selection=blocked explicit-selection=active-2");
});

test("work grouping exposes active work and closed history as separate collections", () => {
  const groups = groupWorkItems(snapshot([item("active-1", "active"), item("closed-1", "closed")]));
  assert.deepEqual(groups.active.map((work) => work.id), ["active-1"]);
  assert.deepEqual(groups.closed.map((work) => work.id), ["closed-1"]);
});
