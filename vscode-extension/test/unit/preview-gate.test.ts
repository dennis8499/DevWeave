import assert from "node:assert/strict";
import test from "node:test";
import { PreviewGate } from "../../src/preview-gate";
import type { PromptBundle, PublicCommandIntent } from "../../src/model";

const intent: PublicCommandIntent = { type: "feature", request: "新增可預覽的功能" };
const bundle: PromptBundle = {
  chatText: "$devweave feature 新增可預覽的功能",
  command: "feature",
  warnings: [],
  mutation: true
};

test("PreviewGate stages and consumes only a matching ticket once", () => {
  const gate = new PreviewGate();
  const staged = gate.stage("panel-1", intent, 7, bundle);

  assert.equal(staged.panelId, "panel-1");
  assert.equal(staged.revision, 7);
  assert.deepEqual(gate.take("panel-1", intent, 7), staged);
  assert.equal(gate.take("panel-1", intent, 7), null);
});

test("PreviewGate rejects mismatched panel, intent, or revision without consuming", () => {
  const gate = new PreviewGate();
  gate.stage("panel-1", intent, 7, bundle);

  assert.equal(gate.take("panel-2", intent, 7), null);
  assert.equal(gate.take("panel-1", { type: "status" }, 7), null);
  assert.equal(gate.take("panel-1", intent, 8), null);
  assert.ok(gate.take("panel-1", intent, 7));
});

test("PreviewGate compares typed intent fields without delimiter collisions", () => {
  const gate = new PreviewGate();
  const staged: PublicCommandIntent = { type: "revise", workId: "a", change: "b\u0000c" };
  const collision: PublicCommandIntent = { type: "revise", workId: "a\u0000b", change: "c" };
  gate.stage("panel-1", staged, 7, bundle);

  assert.equal(gate.take("panel-1", collision, 7), null);
  assert.ok(gate.take("panel-1", staged, 7));
});

test("PreviewGate invalidation makes a ticket stale and prevents restore", () => {
  const gate = new PreviewGate();
  const staged = gate.stage("panel-1", intent, 7, bundle);
  const consumed = gate.take("panel-1", intent, 7);
  gate.invalidate();

  assert.equal(gate.take("panel-1", intent, 7), null);
  assert.deepEqual(consumed, staged);
  assert.equal(gate.restore(consumed!), false);
});

test("PreviewGate restores only the consumed current ticket for clipboard retry", () => {
  const gate = new PreviewGate();
  const staged = gate.stage("panel-1", intent, 7, bundle);
  const consumed = gate.take("panel-1", intent, 7);

  assert.deepEqual(consumed, staged);
  assert.equal(gate.restore(consumed!), true);
  assert.deepEqual(gate.take("panel-1", intent, 7), staged);
  assert.equal(gate.restore(consumed!), false);
});
