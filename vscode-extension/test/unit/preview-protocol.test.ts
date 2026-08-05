import assert from "node:assert/strict";
import test from "node:test";
import type { BootstrapReport } from "../../src/bootstrap";
import type { HostToWebviewMessage } from "../../src/protocol";
import type { PromptBundle, WorkspaceSnapshot } from "../../src/model";

const bundle: PromptBundle = {
  chatText: "$devweave status",
  command: "status",
  warnings: [],
  mutation: false
};

const snapshot = {} as WorkspaceSnapshot;
const report = {} as BootstrapReport;

test("host preview messages carry intent and the snapshot revision", () => {
  const preview: HostToWebviewMessage = {
    type: "actionPreview",
    intent: { type: "status" },
    bundle,
    revision: 12
  };
  const snapshotMessage: HostToWebviewMessage = {
    type: "snapshot",
    snapshot,
    revision: 12
  };
  const bootstrapMessage: HostToWebviewMessage = {
    type: "bootstrapResult",
    report,
    snapshot,
    revision: 13
  };

  assert.equal(preview.revision, snapshotMessage.revision);
  assert.equal(bootstrapMessage.revision, 13);
  assert.deepEqual(preview.intent, { type: "status" });
});
