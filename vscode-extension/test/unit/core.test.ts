import assert from "node:assert/strict";
import test from "node:test";
import { FileSystemPort, DirectoryEntry } from "../../src/filesystem";
import { ActionIntent, WorkspaceSnapshot } from "../../src/model";
import { DevWeavePromptComposer } from "../../src/prompt";
import { parseActionIntent, parseWebviewMessage } from "../../src/protocol";
import { WorkspaceSnapshotReader } from "../../src/snapshot";

class MemoryFileSystem implements FileSystemPort {
  private readonly files = new Map<string, string>();

  public constructor(entries: Record<string, string>) {
    for (const [path, text] of Object.entries(entries)) {
      this.files.set(this.normalize(path), text);
    }
  }

  public async exists(relativePath: string): Promise<boolean> {
    const path = this.normalize(relativePath);
    return path === "." || this.files.has(path) || [...this.files.keys()].some((file) => file.startsWith(path + "/"));
  }

  public async readText(relativePath: string, maxBytes = 1_000_000): Promise<{ text: string; truncated: boolean }> {
    const value = this.files.get(this.normalize(relativePath));
    if (value === undefined) {
      throw new Error("Missing file: " + relativePath);
    }
    const truncated = Buffer.byteLength(value, "utf8") > maxBytes;
    return { text: truncated ? value.slice(0, maxBytes) : value, truncated };
  }

  public async readDirectory(relativePath: string): Promise<DirectoryEntry[]> {
    const parent = this.normalize(relativePath);
    const prefix = parent === "." ? "" : parent + "/";
    const entries = new Map<string, DirectoryEntry>();
    for (const file of this.files.keys()) {
      if (!file.startsWith(prefix)) {
        continue;
      }
      const remainder = file.slice(prefix.length);
      if (!remainder) {
        continue;
      }
      const [name, ...rest] = remainder.split("/");
      entries.set(name, { name, kind: rest.length > 0 ? "directory" : "file" });
    }
    return [...entries.values()].sort((a, b) => a.name.localeCompare(b.name));
  }

  private normalize(value: string): string {
    const normalized = value.replaceAll("\\", "/").replace(/^\.\//, "").replace(/\/$/, "");
    return normalized || ".";
  }
}

function managedEntries(): Record<string, string> {
  return {
    ".devweave/project.json": JSON.stringify({
      managed: true,
      schema_version: 1,
      commands: [{
        id: "unit-tests",
        argv: ["python", "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd: ".",
        required_for: ["high", "low", "standard"],
        timeout_seconds: 240
      }],
      verification_profiles: { high: ["unit-tests"], standard: ["unit-tests"], low: ["unit-tests"] }
    }),
    ".codex/hooks.json": "{}",
    ".agents/skills/devweave/SKILL.md": "# DevWeave",
    ".devweave/baseline/architecture.json": "{}",
    ".devweave/work-items/demo/state.json": JSON.stringify({
      schema_version: 1,
      id: "demo",
      title: "Demo work",
      kind: "feature",
      status: "active",
      phase: "implementation",
      risk: { level: "high" },
      scope: { paths: ["vscode-extension/**"], rationale: "test" },
      gates: { scope: { status: "approved" }, build: { status: "approved" }, acceptance: { status: "pending" } },
      tasks: { "TASK-001": { status: "completed", evidence: ["evidence-1"] } },
      updated_at: "2026-08-03T01:00:00Z"
    }),
    ".devweave/work-items/demo/brief.md": "# Demo",
    ".devweave/work-items/demo/evidence/evidence-1.json": JSON.stringify({
      id: "evidence-1",
      kind: "test",
      status: "passed",
      summary: "passed",
      stale: true,
      binds_current_source: true
    }),
    "wiki/index.md": "---\ntitle: Wiki index\ntype: architecture\nstatus: active\nsources: []\n---\n# Index",
    "wiki/overview.md": "---\ntitle: Overview\ntype: synthesis\nstatus: placeholder\nsources: []\n---\n# Placeholder"
  };
}

function snapshotFixture(): WorkspaceSnapshot {
  return {
    capturedAt: "2026-08-03T01:00:00Z",
    rootName: "fixture",
    rootPath: "file:///fixture",
    projectPath: ".devweave/project.json",
    projectExists: true,
    managed: true,
    schemaVersion: 1,
    project: {},
    commands: [],
    verificationProfiles: {},
    baselineFiles: [],
    hookPresent: true,
    skillPresent: true,
    workItems: [],
    knowledge: { root: "wiki", health: "healthy", pages: [], placeholderPages: [], stalePages: [], critical: [], warnings: [], affectedPages: [], pendingRefresh: [], planned: null },
    diagnostics: [],
    mutationBlocked: false,
    source: "filesystem",
    authoritative: false,
    engineObservedAt: null,
    selectedWorkId: null
  };
}

test("snapshot reader projects array commands, placeholder Wiki, work state, and stale evidence", async () => {
  const reader = new WorkspaceSnapshotReader(new MemoryFileSystem(managedEntries()), {
    rootName: "fixture",
    rootPath: "file:///fixture",
    now: () => "2026-08-03T01:00:00Z"
  });
  const snapshot = await reader.readWorkspace();

  assert.equal(snapshot.projectExists, true);
  assert.equal(snapshot.managed, true);
  assert.equal(snapshot.commands[0]?.id, "unit-tests");
  assert.deepEqual(snapshot.commands[0]?.argv.slice(0, 3), ["python", "-B", "-m"]);
  assert.deepEqual(snapshot.workItems[0]?.staleEvidence, ["evidence-1"]);
  assert.deepEqual(snapshot.knowledge.placeholderPages, ["wiki/overview.md"]);
  assert.equal(snapshot.knowledge.health, "warning");
  assert.equal(snapshot.diagnostics.some((item) => item.code === "project_invalid"), false);
});

test("snapshot reader reports an uninitialized workspace without invoking an engine", async () => {
  const reader = new WorkspaceSnapshotReader(new MemoryFileSystem({ "wiki/index.md": "placeholder" }), {
    rootName: "empty",
    rootPath: "file:///empty",
    now: () => "2026-08-03T01:00:00Z"
  });
  const snapshot = await reader.readWorkspace();

  assert.equal(snapshot.projectExists, false);
  assert.equal(snapshot.managed, null);
  assert.ok(snapshot.diagnostics.some((item) => item.code === "project_missing"));
  assert.deepEqual(snapshot.workItems, []);
});

test("snapshot reader keeps managed false explicit and preserves multiple active/closed work items", async () => {
  const entries = managedEntries();
  entries[".devweave/project.json"] = JSON.stringify({ managed: false, schema_version: 1, commands: [] });
  entries[".devweave/work-items/closed/state.json"] = JSON.stringify({
    schema_version: 1,
    id: "closed",
    title: "Closed work",
    kind: "feature",
    status: "closed",
    phase: "closed",
    risk: { level: "low" },
    gates: {},
    tasks: {},
    updated_at: "2026-08-03T02:00:00Z"
  });
  const reader = new WorkspaceSnapshotReader(new MemoryFileSystem(entries), {
    rootName: "managed-false",
    rootPath: "file:///managed-false",
    now: () => "2026-08-03T02:00:00Z"
  });
  const snapshot = await reader.readWorkspace();

  assert.equal(snapshot.managed, false);
  assert.ok(snapshot.diagnostics.some((item) => item.code === "managed_disabled"));
  assert.equal(snapshot.workItems.length, 2);
  assert.ok(snapshot.workItems.some((item) => item.status === "closed"));
  assert.ok(snapshot.diagnostics.some((item) => item.code === "legacy_work"));
});

test("snapshot reader fails closed for malformed and unsupported project/state", async () => {
  const malformed = managedEntries();
  malformed[".devweave/project.json"] = "{";
  const malformedSnapshot = await new WorkspaceSnapshotReader(new MemoryFileSystem(malformed), {
    rootName: "malformed",
    rootPath: "file:///malformed"
  }).readWorkspace();
  assert.equal(malformedSnapshot.mutationBlocked, true);
  assert.ok(malformedSnapshot.diagnostics.some((item) => item.code === "json_parse"));

  const unsupported = managedEntries();
  unsupported[".devweave/project.json"] = JSON.stringify({ managed: true, schema_version: 99, commands: [] });
  unsupported[".devweave/work-items/demo/state.json"] = JSON.stringify({ schema_version: 99, id: "demo", status: "active", phase: "implementation" });
  const unsupportedSnapshot = await new WorkspaceSnapshotReader(new MemoryFileSystem(unsupported), {
    rootName: "unsupported",
    rootPath: "file:///unsupported"
  }).readWorkspace();
  assert.equal(unsupportedSnapshot.mutationBlocked, true);
  assert.ok(unsupportedSnapshot.diagnostics.some((item) => item.code === "unsupported_schema"));
  assert.ok(unsupportedSnapshot.diagnostics.some((item) => item.code === "work_unsupported_schema"));
  assert.equal(unsupportedSnapshot.workItems[0]?.readOnly, true);
});

test("snapshot reader marks stale Wiki metadata and missing hook without rebuilding fingerprints", async () => {
  const entries = managedEntries();
  delete entries[".codex/hooks.json"];
  entries["wiki/stale.md"] = "---\ntitle: Stale\ntype: modules\nstatus: active\nsource_fingerprint: old\ncomputed_source_fingerprint: new\nsources: []\n---\n# Stale";
  const snapshot = await new WorkspaceSnapshotReader(new MemoryFileSystem(entries), {
    rootName: "stale",
    rootPath: "file:///stale"
  }).readWorkspace();

  assert.ok(snapshot.diagnostics.some((item) => item.code === "hook_missing"));
  assert.deepEqual(snapshot.knowledge.stalePages, ["wiki/stale.md"]);
  assert.equal(snapshot.knowledge.pages.find((page) => page.path === "wiki/stale.md")?.computedSourceFingerprint, "new");
});

test("prompt composition is deterministic, repo-relative, and shell-safe", () => {
  const composer = new DevWeavePromptComposer();
  const snapshot = snapshotFixture();
  const intent: ActionIntent = {
    type: "commandSet",
    id: "safe-command",
    cwd: ".",
    argv: ["python", "-B", "-m", "unittest", "discover"],
    timeout: 120,
    requiredFor: ["high", "standard"]
  };
  const first = composer.compose(intent, snapshot);
  const second = composer.compose(intent, snapshot);

  assert.deepEqual(first, second);
  assert.match(first.machineCommand ?? "", /--required-for "high" "standard"/);
  assert.match(first.machineCommand ?? "", /-- "python"/);
  assert.equal(first.mutation, true);
  assert.deepEqual(first.targetPaths, [".devweave/project.json"]);
  assert.equal(first.chatText.includes("C:\\"), false);
  assert.equal(first.chatText.includes("|"), false);
  assert.equal(first.chatText.includes("secret"), false);
});

test("prompt composer redacts absolute paths and credential-like values", () => {
  const composer = new DevWeavePromptComposer();
  const bundle = composer.compose({
    type: "scope",
    workId: "demo",
    paths: ["C:\\Users\\owner\\repo", "src"],
    rationale: "Review C:\\Users\\owner\\repo; ghp_1234567890123456"
  }, snapshotFixture());

  assert.equal(bundle.chatText.includes("C:\\Users"), false);
  assert.equal(bundle.chatText.includes("ghp_1234567890123456"), false);
  assert.deepEqual(bundle.targetPaths, ["[invalid-repo-relative-path]", "src"]);
  assert.ok(bundle.warnings.some((warning) => warning.includes("absolute")));
  assert.ok(bundle.warnings.some((warning) => warning.includes("credential")));
});

test("mutation prompt is disabled when the snapshot has a critical diagnostic", () => {
  const composer = new DevWeavePromptComposer();
  const snapshot = { ...snapshotFixture(), mutationBlocked: true, diagnostics: [{ severity: "critical" as const, code: "json_parse", message: "invalid" }] };
  const bundle = composer.compose({ type: "taskStart", workId: "demo", taskId: "TASK-001" }, snapshot);

  assert.equal(bundle.mutation, true);
  assert.equal(bundle.machineCommand, undefined);
  assert.match(bundle.chatText, /read-only diagnostic state/);
  assert.ok(bundle.warnings.some((warning) => warning.includes("mutation prompt")));
});

test("every ActionIntent produces a preview bundle", () => {
  const composer = new DevWeavePromptComposer();
  const snapshot = snapshotFixture();
  const intents: ActionIntent[] = [
    { type: "init", goal: "bootstrap" },
    { type: "doctor" },
    { type: "project" },
    { type: "commandList" },
    { type: "commandSet", id: "x", cwd: ".", argv: ["echo", "ok"], timeout: 10, requiredFor: [] },
    { type: "commandRemove", id: "x" },
    { type: "start", kind: "feature", title: "Feature", risk: "standard", rationale: "Need it" },
    { type: "status", all: true },
    { type: "instructions", workId: "demo" },
    { type: "validate", workId: "demo", gate: "build" },
    { type: "bind", workId: "demo" },
    { type: "risk", workId: "demo", level: "high", rationale: "Impact" },
    { type: "scope", workId: "demo", paths: ["vscode-extension/**"], rationale: "Boundary" },
    { type: "baseline", workId: "demo", targets: ["architecture"], rationale: "Record" },
    { type: "knowledgeStatus", workId: "demo" },
    { type: "knowledgeContext", workId: "demo", pages: ["wiki/index.md"], gaps: ["placeholder"] },
    { type: "knowledgePlan", workId: "demo", upserts: ["wiki/overview.md"], deletes: [], rationale: "Refresh" },
    { type: "knowledgeSeal", workId: "demo", pages: ["wiki/overview.md"] },
    { type: "taskStart", workId: "demo", taskId: "TASK-001" },
    { type: "taskComplete", workId: "demo", taskId: "TASK-001", evidence: ["evidence-1"] },
    { type: "taskBlock", workId: "demo", taskId: "TASK-001", note: "Blocked" },
    { type: "evidenceAdd", workId: "demo", kind: "test", status: "passed", summary: "Passed", covers: ["AC-001"], tasks: ["TASK-001"] },
    { type: "verify", workId: "demo", command: "unit-tests", kind: "test", covers: ["AC-001"], tasks: ["TASK-001"], expect: "zero" },
    { type: "waiverAdd", workId: "demo", kind: "risk", target: "AC-001", reason: "Accepted", gate: "build" },
    { type: "approve", workId: "demo", gate: "build" },
    { type: "revise", workId: "demo", from: "design", reason: "Change" },
    { type: "close", workId: "demo" }
  ];

  for (const intent of intents) {
    const bundle = composer.compose(intent, snapshot);
    assert.ok(bundle.chatText.length > 0, intent.type);
    assert.ok(bundle.machineCommand?.startsWith("python -B .agents/skills/devweave/scripts/devweave.py --repo ."), intent.type);
    assert.equal(bundle.chatText.includes(".devweave/work-items/"), false, intent.type);
  }
});

test("Webview protocol accepts typed actions and rejects malformed messages", () => {
  const action: ActionIntent = { type: "approve", workId: "demo", gate: "build" };
  assert.deepEqual(parseActionIntent(action), action);
  assert.deepEqual(parseWebviewMessage({ type: "copyAction", intent: action }), { type: "copyAction", intent: action });
  assert.deepEqual(parseWebviewMessage({ type: "selectWork", workId: null }), { type: "selectWork", workId: null });
  assert.deepEqual(parseWebviewMessage({ type: "refresh" }), { type: "refresh" });
  assert.equal(parseWebviewMessage({ type: "refresh", unexpected: true }), null);
  assert.equal(parseWebviewMessage({ type: "copyAction", intent: { type: "approve" } }), null);
  assert.equal(parseWebviewMessage({ type: "executeCommand", command: "python" }), null);
  assert.equal(parseActionIntent({ type: "taskStart", workId: "demo" }), null);
});
