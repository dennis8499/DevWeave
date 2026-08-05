import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";

const extensionRoot = resolve(process.cwd());

test("Dashboard host invalidates preview tickets across snapshot and selection changes", () => {
  const source = readFileSync(resolve(extensionRoot, "src/dashboard.ts"), "utf8");
  assert.match(source, /private readonly previewGate = new PreviewGate\(\)/);
  assert.match(source, /case "copyAction"[\s\S]*previewGate\.take\(this\.panelId, parsed\.intent, this\.revision\)/);
  assert.match(source, /callbacks\.copy\(ticket\.bundle\)/);
  assert.match(source, /previewGate\.restore\(ticket\)/);
  assert.match(source, /callbacks\.copy\(ticket\.bundle\)[\s\S]*catch \(error\)[\s\S]*previewGate\.restore\(ticket\)[\s\S]*await this\.sendMessage\(\{ type: "copyResult"/);
  assert.match(source, /await this\.sendMessage\(\{ type: "copyResult"[\s\S]*callbacks\.copySuccess\?\.\(\)/);
  assert.match(source, /presentOperationError\(error\)/);
  assert.match(source, /message: failure\.message, detail: failure\.detail/);
  assert.match(source, /case "selectWork"[\s\S]*await this\.sendSnapshot\(\{ \.\.\.this\.lastSnapshot, selectedWorkId \}\)/);
  assert.match(source, /sendSnapshot\(snapshot: WorkspaceSnapshot, invalidate = true\)/);
  assert.match(source, /revision: this\.revision/);
});

test("Dashboard preview protocol preserves the exact intent and revision", () => {
  const source = readFileSync(resolve(extensionRoot, "src/dashboard.ts"), "utf8");
  assert.match(source, /type: "actionPreview", intent, bundle, revision: this\.revision/);
  assert.doesNotMatch(source, /case "copyAction"[\s\S]*callbacks\.copy\(parsed\.intent\)/);
});
