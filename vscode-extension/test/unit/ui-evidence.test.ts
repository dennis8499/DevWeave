import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, test } from "node:test";

import { UiEvidenceCollector, canonicalJson } from "../../src/evidence/ui-evidence";

const temporary = mkdtempSync(join(tmpdir(), "devweave-ui-evidence-"));
after(() => rmSync(temporary, { recursive: true, force: true }));

const provenance = {
  runId: "run-1",
  commit: "a".repeat(40),
  codexVersion: "codex-cli 1.2.3",
  schemaHash: "b".repeat(64)
};

test("UI evidence is bounded, redacted, provenance-bound, and screenshot-hashed", async () => {
  const screenshotPath = join(temporary, "control-center.png");
  const screenshot = Buffer.from("fixture-png");
  writeFileSync(screenshotPath, screenshot);
  const collector = new UiEvidenceCollector(provenance, {
    now: () => new Date("2026-08-25T00:00:00.000Z"),
    logLimitBytes: 1_024
  });
  collector.addAssertion("tabs", true, "five semantic tabs");
  collector.addLog("webview", "authorization=token-secret-value");
  const registered = await collector.registerScreenshot(screenshotPath);
  assert.deepEqual(registered, {
    name: "control-center.png",
    byteLength: screenshot.byteLength,
    sha256: createHash("sha256").update(screenshot).digest("hex")
  });
  const output = join(temporary, "report.json");
  const report = await collector.write(output);
  assert.equal(report.allPassed, true);
  assert.equal(report.capturedAt, "2026-08-25T00:00:00.000Z");
  assert.doesNotMatch(JSON.stringify(report), /token-secret-value/);
  assert.match(JSON.stringify(report), /<redacted>/);
  assert.equal(JSON.parse(readFileSync(output, "utf8")).provenance.commit, provenance.commit);
});

test("UI evidence rejects oversized screenshots, duplicate assertions, and invalid provenance", async () => {
  const oversized = join(temporary, "oversized.png");
  writeFileSync(oversized, Buffer.alloc(5));
  const collector = new UiEvidenceCollector(provenance, { screenshotLimitBytes: 4 });
  collector.addAssertion("unique", true);
  assert.throws(() => collector.addAssertion("unique", true), /Duplicate/);
  await assert.rejects(collector.registerScreenshot(oversized), /between 1 and 4 bytes/);
  assert.throws(() => new UiEvidenceCollector({ ...provenance, schemaHash: "bad" }), /SHA-256/);
});

test("canonical UI evidence JSON sorts object keys without reordering arrays", () => {
  assert.equal(canonicalJson({ z: 1, a: { y: 2, b: [3, { d: 4, c: 5 }] } }), '{"a":{"b":[3,{"c":5,"d":4}],"y":2},"z":1}');
});
